"""Deterministic greeting response."""

from restaurant_voice_ai.conversation.enums import NextAction, ResponseType
from restaurant_voice_ai.conversation.state import ConversationState


def handle_greeting(_: ConversationState) -> ConversationState:
    return {
        "response_type": ResponseType.ANSWER.value,
        "response_text": "Hello! How can I help with your visit today?",
        "next_action": NextAction.NONE.value,
    }
