"""FastAPI application entry point."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from restaurant_voice_ai.api.router import api_router
from restaurant_voice_ai.api.routes.operations import router as operations_router
from restaurant_voice_ai.core.config import Settings, get_settings
from restaurant_voice_ai.core.exceptions import register_exception_handlers
from restaurant_voice_ai.core.logging import configure_logging, get_logger
from restaurant_voice_ai.db.session import dispose_engine
from restaurant_voice_ai.observability.middleware import OperationsMiddleware
from restaurant_voice_ai.persistence.redis.client import RedisClientManager
from restaurant_voice_ai.rate_limit.base import RateLimiter
from restaurant_voice_ai.rate_limit.in_memory import InMemoryRateLimiter
from restaurant_voice_ai.rate_limit.redis import RedisRateLimiter
from restaurant_voice_ai.schemas.common import HealthResponse, RootResponse
from restaurant_voice_ai.voice.dependencies import get_session_manager


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level, app_settings.log_format)
    logger = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        app_settings.validate_runtime_configuration()
        application.state.ready = False
        redis_manager: RedisClientManager | None = None
        if app_settings.app_env == "production":
            startup_engine = create_async_engine(app_settings.database_url)
            try:
                async with asyncio.timeout(app_settings.startup_database_timeout_seconds):
                    async with startup_engine.connect() as connection:
                        await connection.execute(text("SELECT 1"))
            finally:
                await startup_engine.dispose()
        if app_settings.redis_enabled:
            redis_manager = getattr(application.state, "redis_manager", None)
            if redis_manager is None:
                redis_manager = RedisClientManager(app_settings)
            application.state.redis_manager = redis_manager
            redis_required = any(
                backend == "redis"
                for backend in (
                    app_settings.conversation_memory_backend,
                    app_settings.idempotency_backend,
                    app_settings.rate_limit_backend,
                )
            )
            if redis_required:
                await redis_manager.ping()
        logger.info(
            "Application startup",
            extra={
                "environment": app_settings.app_env,
                "version": app_settings.app_version,
                "embedding_provider": app_settings.embedding_provider,
                "embedding_model": app_settings.embedding_model_name,
                "chroma_persist_directory": app_settings.chroma_persist_directory,
                "chroma_collection_name": app_settings.chroma_collection_name,
            },
        )
        try:
            application.state.ready = True
            yield
        finally:
            application.state.ready = False
            await get_session_manager(
                app_settings.voice_max_sessions,
                app_settings.voice_session_idle_timeout_seconds,
                app_settings.voice_max_session_seconds,
            ).shutdown()
            if redis_manager is not None:
                await redis_manager.close()
            await dispose_engine()
            logger.info("Application shutdown")

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        # Keep public error responses safe even when application debug logging is enabled.
        debug=False,
        lifespan=lifespan,
    )
    application.state.settings = app_settings

    application.add_middleware(TrustedHostMiddleware, allowed_hosts=app_settings.trusted_hosts)

    if app_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if app_settings.rate_limit_backend == "redis":
        rate_redis = RedisClientManager(app_settings)
        application.state.redis_manager = rate_redis
        limiter: RateLimiter = RedisRateLimiter(rate_redis)
    else:
        limiter = InMemoryRateLimiter()
    application.state.rate_limiter = limiter
    application.add_middleware(OperationsMiddleware, settings=app_settings, limiter=limiter)

    @application.middleware("http")
    async def log_requests(request: Request, call_next: RequestResponseEndpoint) -> Response:
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000
            logger.exception(
                "Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 2),
                    "request_id": getattr(request.state, "request_id", "-"),
                },
            )
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "request_id": getattr(request.state, "request_id", "-"),
            },
        )
        return response

    register_exception_handlers(application)
    application.include_router(api_router, prefix=app_settings.api_v1_prefix)
    application.include_router(operations_router)
    demo_directory = Path(__file__).resolve().parents[2] / "examples" / "voice_demo"
    if demo_directory.is_dir():
        application.mount(
            "/voice-demo", StaticFiles(directory=demo_directory, html=True), name="voice-demo"
        )

    @application.get("/", response_model=RootResponse, tags=["Service"])
    async def root() -> RootResponse:
        return RootResponse(
            message=f"{app_settings.app_name} API",
            docs="/docs",
            health="/health",
        )

    # Unversioned operational health endpoint.
    from restaurant_voice_ai.api.routes.health import health

    application.add_api_route(
        "/health",
        health,
        methods=["GET"],
        response_model=HealthResponse,
        tags=["Health"],
    )

    return application


app = create_app()
