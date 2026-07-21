"""Reservation cancellation operation node."""

from typing import Any

from restaurant_voice_ai.conversation.models import ConversationDependencies
from restaurant_voice_ai.conversation.state import ConversationState
from restaurant_voice_ai.core.exceptions import ApplicationError


def build_node(dependencies: ConversationDependencies) -> Any:
    async def cancel_reservation(state: ConversationState) -> ConversationState:
        try:
            result = await dependencies.reservations.cancel(
                str(state["entities"]["reservation_id"])
            )
            return {"reservation": result}
        except ApplicationError as error:
            return {"error_code": error.code, "error_message": error.message}
        except Exception:
            return {
                "error_code": "RESERVATION_CANCEL_ERROR",
                "error_message": "I couldn't cancel the reservation.",
            }

    return cancel_reservation
