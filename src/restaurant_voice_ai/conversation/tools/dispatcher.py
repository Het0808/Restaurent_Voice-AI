"""Application-controlled dispatcher for narrow service operations."""

import hashlib
import json
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
from restaurant_voice_ai.persistence.redis.idempotency import (
    IdempotencyStatus,
    IdempotencyStore,
)


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
        idempotency: IdempotencyStore | None = None,
    ) -> None:
        self.knowledge = knowledge
        self.reservations = reservations
        self.max_party_size = max_party_size
        self.idempotency = idempotency

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
        idempotency_key: str | None = None
        try:
            parsed = schema.model_validate(arguments)
            parsed_data = parsed.model_dump(mode="json", exclude_none=True)
            party_size = parsed_data.get("party_size") or parsed_data.get("requested_party_size")
            if party_size is not None and int(party_size) > self.max_party_size:
                raise ValueError("Party size exceeds the restaurant maximum")
            if tool_name in MUTATION_TOOLS and self.idempotency is not None:
                canonical = json.dumps(parsed_data, sort_keys=True, separators=(",", ":"))
                idempotency_key = hashlib.sha256(
                    f"{context.conversation_id}:{tool_name}:{canonical}".encode()
                ).hexdigest()
                existing = await self.idempotency.get(idempotency_key)
                if existing and existing.status is IdempotencyStatus.COMPLETED:
                    return ToolResult(
                        tool_name=tool_name,
                        success=True,
                        status="replayed",
                        data=existing.result,
                    )
                if not await self.idempotency.reserve(idempotency_key, 86400):
                    return ToolResult(
                        tool_name=tool_name,
                        success=False,
                        status="rejected",
                        error_code="DUPLICATE_OPERATION_IN_PROGRESS",
                        message="That operation is already being processed.",
                    )
            data = await self._dispatch(tool_name, parsed_data)
            if idempotency_key is not None and self.idempotency is not None:
                await self.idempotency.complete(idempotency_key, data, 86400)
            return ToolResult(tool_name=tool_name, success=True, status="success", data=data)
        except (ValidationError, ValueError) as error:
            await self._mark_idempotency_failed(idempotency_key)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                status="validation_error",
                error_code="INVALID_TOOL_ARGUMENTS",
                message=str(error).splitlines()[0],
            )
        except ApplicationError as error:
            await self._mark_idempotency_failed(idempotency_key)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                status="domain_error",
                error_code=error.code,
                message=error.message,
            )
        except Exception:
            await self._mark_idempotency_failed(idempotency_key)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                status="temporarily_unavailable",
                error_code="TOOL_EXECUTION_ERROR",
                message="The operation could not be completed right now.",
            )

    async def _mark_idempotency_failed(self, key: str | None) -> None:
        if key is not None and self.idempotency is not None:
            await self.idempotency.fail(key, 300)

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
