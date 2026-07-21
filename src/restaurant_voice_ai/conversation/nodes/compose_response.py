"""Compose concise deterministic responses from operation results."""

from restaurant_voice_ai.conversation.enums import Intent, NextAction, ResponseType
from restaurant_voice_ai.conversation.state import ConversationState


def compose_response(state: ConversationState) -> ConversationState:
    intent = Intent(state["intent"])
    if intent is Intent.KNOWLEDGE_QUERY:
        if not state.get("evidence_found"):
            text = "I couldn't find that in the restaurant information I have."
        else:
            text = state.get("retrieved_context", "").split("\n", 1)[-1].split("\n\n", 1)[0]
            if "allerg" in state["message"].casefold():
                text += " Please confirm severe allergies directly with restaurant staff."
        return {
            "response_type": ResponseType.ANSWER.value,
            "response_text": text,
            "next_action": NextAction.NONE.value,
        }
    if intent is Intent.CHECK_AVAILABILITY:
        available = bool((state.get("availability") or {}).get("available"))
        text = (
            "Yes, a table is available for that time."
            if available
            else "Sorry, no table is available for that time."
        )
        return {
            "response_type": ResponseType.ANSWER.value,
            "response_text": text,
            "next_action": NextAction.CONFIRM_RESERVATION.value
            if available
            else NextAction.NONE.value,
        }
    reservation = state.get("reservation") or {}
    code = reservation.get("confirmation_code", "")
    actions = {
        Intent.CREATE_RESERVATION: (
            f"Your reservation is confirmed. Your confirmation code is {code}."
        ),
        Intent.CANCEL_RESERVATION: f"Reservation {code} has been cancelled.",
        Intent.MODIFY_RESERVATION: f"Reservation {code} has been updated.",
    }
    return {
        "response_type": ResponseType.CONFIRMATION.value,
        "response_text": actions[intent],
        "next_action": NextAction.NONE.value,
    }
