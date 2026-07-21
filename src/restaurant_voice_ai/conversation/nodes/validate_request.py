"""Validate required fields without performing business operations."""

from restaurant_voice_ai.conversation.enums import Intent, NextAction
from restaurant_voice_ai.conversation.state import ConversationState

REQUIRED_FIELDS: dict[Intent, tuple[str, ...]] = {
    Intent.CHECK_AVAILABILITY: ("reservation_date", "reservation_time", "party_size"),
    Intent.CREATE_RESERVATION: (
        "customer_name",
        "customer_phone",
        "reservation_date",
        "reservation_time",
        "party_size",
    ),
    Intent.CANCEL_RESERVATION: ("reservation_id",),
    Intent.MODIFY_RESERVATION: ("reservation_id", "requested_change"),
}
NEXT_ACTIONS = {
    "customer_name": NextAction.ASK_CUSTOMER_NAME,
    "customer_phone": NextAction.ASK_CUSTOMER_PHONE,
    "reservation_date": NextAction.ASK_RESERVATION_DATE,
    "reservation_time": NextAction.ASK_RESERVATION_TIME,
    "party_size": NextAction.ASK_PARTY_SIZE,
    "reservation_id": NextAction.ASK_RESERVATION_ID,
    "requested_change": NextAction.ASK_REQUESTED_CHANGE,
}


def validate_request(state: ConversationState) -> ConversationState:
    intent = Intent(state["intent"])
    entities = state.get("entities", {})
    missing: list[str] = []
    for field in REQUIRED_FIELDS.get(intent, ()):
        if field == "requested_change":
            present = any(
                entities.get(key) is not None
                for key in ("requested_date", "requested_time", "requested_party_size")
            )
        else:
            present = entities.get(field) is not None
        if not present:
            missing.append(field)
    next_action = NEXT_ACTIONS[missing[0]].value if missing else NextAction.NONE.value
    return {"missing_fields": missing, "next_action": next_action}
