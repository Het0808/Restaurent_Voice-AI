"""Static, allowlisted tool declarations for Gemini and application routing."""

from typing import Any

from pydantic import BaseModel

from restaurant_voice_ai.conversation.tools.schemas import (
    CancelReservation,
    CheckTableAvailability,
    CreateReservation,
    ModifyReservation,
    SearchRestaurantKnowledge,
)

type PydanticModelType = type[BaseModel]

TOOL_SCHEMAS: dict[str, PydanticModelType] = {
    "search_restaurant_knowledge": SearchRestaurantKnowledge,
    "check_table_availability": CheckTableAvailability,
    "create_reservation": CreateReservation,
    "modify_reservation": ModifyReservation,
    "cancel_reservation": CancelReservation,
}
MUTATION_TOOLS = frozenset({"create_reservation", "modify_reservation", "cancel_reservation"})


def tool_declarations() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": f"Validated restaurant operation: {name}",
            "parameters": schema.model_json_schema(),
        }
        for name, schema in TOOL_SCHEMAS.items()
    ]
