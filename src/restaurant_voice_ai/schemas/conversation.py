"""Public conversation endpoint schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from restaurant_voice_ai.conversation.enums import Intent, NextAction, ResponseType


class ConversationMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: Literal["en", "hi", "gu"] = "en"
    debug: bool = False


class ConversationCitation(BaseModel):
    source: str
    source_filename: str
    chunk_id: str
    section: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationMessageResponse(BaseModel):
    intent: Intent
    response_type: ResponseType
    response_text: str
    next_action: NextAction = NextAction.NONE
    entities: dict[str, Any] = Field(default_factory=dict)
    citations: list[ConversationCitation] = Field(default_factory=list)
    availability: dict[str, Any] | None = None
    reservation: dict[str, Any] | None = None
    trace: list[dict[str, Any]] | None = None
