"""Pure graph routing functions and stable node names."""

from typing import Literal, cast

from restaurant_voice_ai.conversation.enums import Intent
from restaurant_voice_ai.conversation.state import ConversationState

INITIALIZE = "initialize"
CLASSIFY_INTENT = "classify_intent"
EXTRACT_ENTITIES = "extract_entities"
VALIDATE_REQUEST = "validate_request"
RETRIEVE_KNOWLEDGE = "retrieve_knowledge"
CHECK_AVAILABILITY = "check_availability"
CREATE_RESERVATION = "create_reservation"
CANCEL_RESERVATION = "cancel_reservation"
MODIFY_RESERVATION = "modify_reservation"
REQUEST_CLARIFICATION = "request_clarification"
COMPOSE_RESPONSE = "compose_response"
HANDLE_GREETING = "handle_greeting"
HANDLE_UNSUPPORTED = "handle_unsupported"
HANDLE_ERROR = "handle_error"

ValidationRoute = Literal[
    "request_clarification",
    "handle_greeting",
    "retrieve_knowledge",
    "check_availability",
    "create_reservation",
    "cancel_reservation",
    "modify_reservation",
    "handle_unsupported",
    "handle_error",
]


def route_after_validation(state: ConversationState) -> ValidationRoute:
    if state.get("error_code"):
        return cast(ValidationRoute, HANDLE_ERROR)
    if state.get("missing_fields"):
        return cast(ValidationRoute, REQUEST_CLARIFICATION)
    routes: dict[str, str] = {
        Intent.GREETING.value: HANDLE_GREETING,
        Intent.KNOWLEDGE_QUERY.value: RETRIEVE_KNOWLEDGE,
        Intent.CHECK_AVAILABILITY.value: CHECK_AVAILABILITY,
        Intent.CREATE_RESERVATION.value: CREATE_RESERVATION,
        Intent.CANCEL_RESERVATION.value: CANCEL_RESERVATION,
        Intent.MODIFY_RESERVATION.value: MODIFY_RESERVATION,
        Intent.UNSUPPORTED.value: HANDLE_UNSUPPORTED,
        Intent.UNKNOWN.value: HANDLE_UNSUPPORTED,
    }
    return cast(
        ValidationRoute,
        routes.get(state.get("intent", Intent.UNKNOWN.value), HANDLE_UNSUPPORTED),
    )


def route_after_operation(
    state: ConversationState,
) -> Literal["compose_response", "handle_error"]:
    route = HANDLE_ERROR if state.get("error_code") else COMPOSE_RESPONSE
    return cast(Literal["compose_response", "handle_error"], route)
