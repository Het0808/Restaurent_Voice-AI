"""Reservation modification operation node."""

from typing import Any

from restaurant_voice_ai.conversation.models import ConversationDependencies, ConversationEntities
from restaurant_voice_ai.conversation.state import ConversationState
from restaurant_voice_ai.core.exceptions import ApplicationError


def build_node(dependencies: ConversationDependencies) -> Any:
    async def modify_reservation(state: ConversationState) -> ConversationState:
        try:
            result = await dependencies.reservations.modify(
                ConversationEntities.model_validate(state["entities"])
            )
            return {"reservation": result}
        except ApplicationError as error:
            return {"error_code": error.code, "error_message": error.message}
        except Exception:
            return {
                "error_code": "RESERVATION_MODIFY_ERROR",
                "error_message": "I couldn't modify the reservation.",
            }

    return modify_reservation
