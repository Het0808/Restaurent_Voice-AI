"""FastAPI authentication dependencies."""

from collections.abc import Callable
from typing import Annotated

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from restaurant_voice_ai.auth.api_keys import authenticate_api_key
from restaurant_voice_ai.auth.models import AuthIdentity, Permission, Role
from restaurant_voice_ai.auth.permissions import has_permission
from restaurant_voice_ai.core.config import Settings

api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False, scheme_name="ApiKeyAuth")


def require_permission(permission: Permission) -> Callable[[Request], AuthIdentity]:
    def dependency(
        request: Request,
        documented_key: Annotated[str | None, Security(api_key_scheme)] = None,
    ) -> AuthIdentity:
        settings: Settings = request.app.state.settings
        if not settings.api_auth_enabled:
            return AuthIdentity(role=Role.INTERNAL, fingerprint="auth-disabled")
        supplied = request.headers.get(settings.api_key_header_name) or documented_key
        identity = authenticate_api_key(supplied, settings.api_keys, settings.admin_api_keys)
        if identity is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "authentication_required",
                    "message": "A valid API key is required.",
                },
            )
        if not has_permission(identity.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "permission_denied", "message": "Permission denied."},
            )
        request.state.auth_identity = identity.fingerprint
        return identity

    return dependency
