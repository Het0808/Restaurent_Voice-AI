"""Authentication identities and permissions."""

from enum import StrEnum

from pydantic import BaseModel


class Role(StrEnum):
    PUBLIC = "public"
    CLIENT = "client"
    ADMIN = "admin"
    INTERNAL = "internal"


class Permission(StrEnum):
    SEND_TEXT_MESSAGE = "send_text_message"
    OPEN_VOICE_SESSION = "open_voice_session"
    RESET_CONVERSATION = "reset_conversation"
    VIEW_DEBUG_STATE = "view_debug_state"
    VIEW_METRICS = "view_metrics"
    VIEW_ADMIN_HEALTH = "view_admin_health"
    READ_CONVERSATION_AUDIT = "read_conversation_audit"


class AuthIdentity(BaseModel):
    role: Role
    fingerprint: str
