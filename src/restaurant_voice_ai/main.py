"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from restaurant_voice_ai.api.router import api_router
from restaurant_voice_ai.core.config import Settings, get_settings
from restaurant_voice_ai.core.exceptions import register_exception_handlers
from restaurant_voice_ai.core.logging import configure_logging, get_logger
from restaurant_voice_ai.db.session import dispose_engine
from restaurant_voice_ai.schemas.common import HealthResponse, RootResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    logger = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
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
            yield
        finally:
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

    if app_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

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
            },
        )
        return response

    register_exception_handlers(application)
    application.include_router(api_router, prefix=app_settings.api_v1_prefix)

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
