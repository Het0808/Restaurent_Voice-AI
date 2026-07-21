"""JSON-serializable state passed between graph nodes."""

from typing import Any, TypedDict


class ConversationState(TypedDict, total=False):
    message: str
    language: str
    debug: bool
    intent: str
    intent_confidence: float
    entities: dict[str, Any]
    missing_fields: list[str]
    next_action: str
    response_type: str
    response_text: str
    conversation_id: str
    citations: list[dict[str, Any]]
    retrieval_results: list[dict[str, Any]]
    retrieved_context: str
    evidence_found: bool
    availability: dict[str, Any] | None
    reservation: dict[str, Any] | None
    retrieval: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    trace: list[dict[str, Any]]
