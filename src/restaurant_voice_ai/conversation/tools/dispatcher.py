"""Application-controlled dispatcher for narrow service operations."""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from restaurant_voice_ai.conversation.enums import ConfirmationStatus
from restaurant_voice_ai.conversation.models import (
    ConversationEntities,
    KnowledgeGateway,
    ReservationGateway,
)
from restaurant_voice_ai.conversation.tools.definitions import MUTATION_TOOLS, TOOL_SCHEMAS
from restaurant_voice_ai.conversation.tools.results import ToolResult
from restaurant_voice_ai.core.exceptions import ApplicationError


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    conversation_id: str
    confirmation_status: ConfirmationStatus
    tool_iteration_count: int
    max_tool_iterations: int


class ConversationToolDispatcher:
    def __init__(
        self,
        knowledge: KnowledgeGateway,
        reservations: ReservationGateway,
        max_party_size: int,
    ) -> None:
        self.knowledge = knowledge
        self.reservations = reservations
        self.max_party_size = max_party_size

    async def execute(
        self, tool_name: str, arguments: dict[str, Any], context: ToolExecutionContext
    ) -> ToolResult:
        schema = TOOL_SCHEMAS.get(tool_name)
        if schema is None:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                status="rejected",
                error_code="UNSUPPORTED_TOOL",
                message="That operation is not supported.",
            )
        if context.tool_iteration_count >= context.max_tool_iterations:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                status="rejected",
                error_code="TOOL_LIMIT_REACHED",
                message="I couldn't complete that request. Please try again.",
            )
        if (
            tool_name in MUTATION_TOOLS
            and context.confirmation_status is not ConfirmationStatus.CONFIRMED
        ):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                status="rejected",
                error_code="CONFIRMATION_REQUIRED",
                message="Please confirm this change first.",
            )
        try:
            parsed = schema.model_validate(arguments)
            parsed_data = parsed.model_dump(mode="json", exclude_none=True)
            party_size = parsed_data.get("party_size") or parsed_data.get("requested_party_size")
            if party_size is not None and int(party_size) > self.max_party_size:
                raise ValueError("Party size exceeds the restaurant maximum")
            data = await self._dispatch(tool_name, parsed_data)
            return ToolResult(tool_name=tool_name, success=True, status="success", data=data)
        except (ValidationError, ValueError) as error:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                status="validation_error",
                error_code="INVALID_TOOL_ARGUMENTS",
                message=str(error).splitlines()[0],
            )
        except ApplicationError as error:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                status="domain_error",
                error_code=error.code,
                message=error.message,
            )
        except Exception:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                status="temporarily_unavailable",
                error_code="TOOL_EXECUTION_ERROR",
                message="The operation could not be completed right now.",
            )

    async def _dispatch(self, tool_name: str, data: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "search_restaurant_knowledge":
            return await self.knowledge.retrieve(str(data["query"]))
        entities = ConversationEntities.model_validate(data)
        if tool_name == "check_table_availability":
            return await self.reservations.check_availability(entities)
        if tool_name == "create_reservation":
            return await self.reservations.create(entities, "en")
        if tool_name == "modify_reservation":
            return await self.reservations.modify(entities)
        if tool_name == "cancel_reservation":
            return await self.reservations.cancel(str(data["reservation_id"]))
        raise ValueError("Unsupported tool")
