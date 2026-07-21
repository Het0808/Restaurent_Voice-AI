"""Validated model input and output contracts."""

from typing import Any

from pydantic import BaseModel, Field

from restaurant_voice_ai.conversation.enums import Intent


class InterpretationResult(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0, le=1)
    entities: dict[str, Any] = Field(default_factory=dict)
    requested_operation: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    requires_clarification: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    language: str = "en"
    reason_category: str = "supported_request"


class ResponseGenerationInput(BaseModel):
    language: str
    response_type: str
    verified_facts: dict[str, Any] = Field(default_factory=dict)
    pending_summary: str | None = None
    retrieved_context: str = ""
    deterministic_fallback: str
