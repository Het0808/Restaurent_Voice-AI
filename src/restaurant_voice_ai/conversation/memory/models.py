"""Serializable conversation memory models."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from restaurant_voice_ai.conversation.enums import ConfirmationStatus, ConversationStatus


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant", "tool", "system"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tool_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingOperation(BaseModel):
    operation_id: str
    operation_type: Literal["create_reservation", "modify_reservation", "cancel_reservation"]
    validated_arguments: dict[str, Any]
    missing_fields: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confirmation_required: bool = True
    confirmation_status: ConfirmationStatus = ConfirmationStatus.AWAITING_CONFIRMATION
    summary: str | None = None


class ConversationSnapshot(BaseModel):
    conversation_id: str
    turn_number: int = 0
    message_history: list[ConversationMessage] = Field(default_factory=list)
    intent: str = "unknown"
    accumulated_entities: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    pending_operation: PendingOperation | None = None
    last_tool_result: dict[str, Any] | None = None
    conversation_status: ConversationStatus = ConversationStatus.ACTIVE
    model_provider: str = "rules"
    fallback_used: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
