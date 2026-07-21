"""Service health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


def build_health_response(settings: Settings) -> HealthResponse:
    """Create the shared health response from application settings."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )


async def health(request: Request) -> HealthResponse:
    """Report process health without checking future external dependencies."""
    settings: Settings = request.app.state.settings
    return build_health_response(settings)


router.add_api_route("/health", health, methods=["GET"], response_model=HealthResponse)


@router.get("/health/database", response_model=HealthResponse)
async def database_health(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HealthResponse | JSONResponse:
    """Report database readiness without changing basic process health."""
    settings: Settings = request.app.state.settings
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": settings.app_name,
                "version": settings.app_version,
                "environment": settings.app_env,
            },
        )
    return build_health_response(settings)
