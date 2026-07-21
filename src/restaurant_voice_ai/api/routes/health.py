"""Service health endpoints."""

from fastapi import APIRouter, Request

from restaurant_voice_ai.core.config import Settings
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
