"""Generate one concise clarification for the first missing field."""

from restaurant_voice_ai.conversation.enums import ResponseType
from restaurant_voice_ai.conversation.state import ConversationState

QUESTIONS = {
    "customer_name": "What name should I use for the reservation?",
    "customer_phone": "What phone number should I use?",
    "reservation_date": "What date would you like?",
    "reservation_time": "What time would you like?",
    "party_size": "How many guests will there be?",
    "reservation_id": "What is your reservation or confirmation code?",
    "requested_change": "What would you like to change: the date, time, or party size?",
}


def request_clarification(state: ConversationState) -> ConversationState:
    field = state["missing_fields"][0]
    return {"response_type": ResponseType.CLARIFICATION.value, "response_text": QUESTIONS[field]}
