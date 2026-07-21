"""Availability operation node."""

from typing import Any

from restaurant_voice_ai.conversation.models import ConversationDependencies, ConversationEntities
from restaurant_voice_ai.conversation.state import ConversationState
from restaurant_voice_ai.core.exceptions import ApplicationError


def build_node(dependencies: ConversationDependencies) -> Any:
    async def check_availability(state: ConversationState) -> ConversationState:
        try:
            result = await dependencies.reservations.check_availability(
                ConversationEntities.model_validate(state["entities"])
            )
            return {"availability": result}
        except ApplicationError as error:
            return {"error_code": error.code, "error_message": error.message}
        except Exception:
            return {
                "error_code": "AVAILABILITY_ERROR",
                "error_message": "I couldn't check availability right now.",
            }

    return check_availability
