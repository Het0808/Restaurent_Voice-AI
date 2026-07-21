"""Metrics and production health endpoints."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.auth.dependencies import require_permission
from restaurant_voice_ai.auth.models import AuthIdentity, Permission
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.observability.metrics import metrics
from restaurant_voice_ai.persistence.redis.factory import get_redis_manager

router = APIRouter(tags=["Operations"])


@router.get("/health/live")
async def liveness(request: Request) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    return {
        "status": "alive",
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def readiness(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthIdentity, Depends(require_permission(Permission.VIEW_ADMIN_HEALTH))],
) -> Response:
    settings: Settings = request.app.state.settings
    components: dict[str, object] = {}
    ready = True
    try:
        await session.execute(text("SELECT 1"))
        components["database"] = {"ready": True}
    except SQLAlchemyError:
        components["database"] = {"ready": False}
        ready = False
    redis_required = settings.redis_enabled and any(
        item == "redis"
        for item in (
            settings.conversation_memory_backend,
            settings.idempotency_backend,
            settings.rate_limit_backend,
        )
    )
    if redis_required:
        try:
            components["redis"] = {"ready": await get_redis_manager(request).ping()}
        except Exception:
            components["redis"] = {"ready": False}
            ready = False
    else:
        components["redis"] = {"ready": True, "required": False}
    components["conversation"] = {"ready": True}
    components["voice"] = {
        "ready": settings.voice_enabled,
        "stt_provider": settings.voice_stt_provider,
        "tts_provider": settings.voice_tts_provider,
    }
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "ready": ready,
            "components": components,
            "version": settings.app_version,
            "environment": settings.app_env,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@router.get("/metrics")
async def prometheus_metrics(
    request: Request,
    _: Annotated[AuthIdentity, Depends(require_permission(Permission.VIEW_METRICS))],
) -> Response:
    settings: Settings = request.app.state.settings
    if not settings.metrics_enabled:
        return Response(status_code=404)
    return Response(generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST)
