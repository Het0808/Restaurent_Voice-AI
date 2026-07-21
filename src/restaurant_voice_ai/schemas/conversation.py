"""Public conversation endpoint schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from restaurant_voice_ai.conversation.enums import Intent, NextAction, ResponseType


class ConversationMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, min_length=8, max_length=64)
    language: Literal["en", "hi", "gu"] = "en"
    metadata: dict[str, Any] = Field(default_factory=dict)
    debug: bool = False


class ConversationCitation(BaseModel):
    source: str
    source_filename: str
    chunk_id: str
    section: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationMessageResponse(BaseModel):
    conversation_id: str
    turn_number: int
    intent: Intent
    response_type: ResponseType
    response_text: str
    next_action: NextAction = NextAction.NONE
    missing_fields: list[str] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    citations: list[ConversationCitation] = Field(default_factory=list)
    availability: dict[str, Any] | None = None
    reservation: dict[str, Any] | None = None
    confirmation_required: bool = False
    pending_operation: dict[str, Any] | None = None
    model_provider: str = "rules"
    fallback_used: bool = False
    debug_trace: list[dict[str, Any]] | None = None
    trace: list[dict[str, Any]] | None = None


class ConversationResetResponse(BaseModel):
    conversation_id: str
    reset: bool = True
    message: str = "Conversation memory cleared."
