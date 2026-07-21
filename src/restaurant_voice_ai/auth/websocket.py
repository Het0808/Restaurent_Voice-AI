"""WebSocket API-key authentication."""

from fastapi import WebSocket

from restaurant_voice_ai.auth.api_keys import authenticate_api_key
from restaurant_voice_ai.auth.models import AuthIdentity, Permission, Role
from restaurant_voice_ai.auth.permissions import has_permission
from restaurant_voice_ai.core.config import Settings


def authenticate_websocket(websocket: WebSocket, permission: Permission) -> AuthIdentity | None:
    settings: Settings = websocket.app.state.settings
    if not settings.api_auth_enabled:
        return AuthIdentity(role=Role.INTERNAL, fingerprint="auth-disabled")
    supplied = websocket.headers.get(settings.api_key_header_name)
    if (
        supplied is None
        and settings.websocket_query_api_key_enabled
        and settings.app_env != "production"
    ):
        supplied = websocket.query_params.get("api_key")
    identity = authenticate_api_key(supplied, settings.api_keys, settings.admin_api_keys)
    if identity is None or not has_permission(identity.role, permission):
        return None
    return identity
