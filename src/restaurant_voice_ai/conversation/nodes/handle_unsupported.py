"""Safe response for unsupported and unknown requests."""

from restaurant_voice_ai.conversation.enums import NextAction, ResponseType
from restaurant_voice_ai.conversation.state import ConversationState


def handle_unsupported(_: ConversationState) -> ConversationState:
    return {
        "response_type": ResponseType.UNSUPPORTED.value,
        "response_text": "I can help with restaurant questions and table reservations.",
        "next_action": NextAction.HANDOFF_RECOMMENDED.value,
    }
