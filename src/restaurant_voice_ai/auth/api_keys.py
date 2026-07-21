"""Constant-time API-key validation without retaining raw keys."""

import hashlib
import hmac

from pydantic import SecretStr

from restaurant_voice_ai.auth.models import AuthIdentity, Role


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def authenticate_api_key(
    supplied: str | None,
    client_keys: list[SecretStr],
    admin_keys: list[SecretStr],
) -> AuthIdentity | None:
    if not supplied:
        return None
    matched_role: Role | None = None
    for role, configured in ((Role.ADMIN, admin_keys), (Role.CLIENT, client_keys)):
        for candidate in configured:
            if hmac.compare_digest(supplied, candidate.get_secret_value()):
                matched_role = role
    return (
        AuthIdentity(role=matched_role, fingerprint=fingerprint(supplied)) if matched_role else None
    )
