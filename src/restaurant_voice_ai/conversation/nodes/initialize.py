"""Initialize safe per-request state."""

import uuid

from restaurant_voice_ai.conversation.enums import Intent, NextAction
from restaurant_voice_ai.conversation.state import ConversationState


def initialize(state: ConversationState) -> ConversationState:
    return {
        "message": state["message"].strip(),
        "conversation_id": uuid.uuid4().hex,
        "language": state.get("language", "en"),
        "debug": state.get("debug", False),
        "intent": Intent.UNKNOWN.value,
        "entities": {},
        "missing_fields": [],
        "next_action": NextAction.NONE.value,
        "citations": [],
        "retrieval_results": [],
        "retrieved_context": "",
        "evidence_found": False,
        "availability": None,
        "reservation": None,
        "retrieval": None,
        "error_code": None,
        "error_message": None,
        "trace": [],
    }
