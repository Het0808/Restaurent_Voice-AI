"""Convert internal failures into safe caller-facing text."""

from restaurant_voice_ai.conversation.enums import NextAction, ResponseType
from restaurant_voice_ai.conversation.state import ConversationState


def handle_error(state: ConversationState) -> ConversationState:
    return {
        "response_type": ResponseType.ERROR.value,
        "response_text": state.get("error_message")
        or "I couldn't complete that request. Please try again.",
        "next_action": NextAction.RETRY.value,
    }
