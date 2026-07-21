"""Multi-turn conversation service with application-controlled mutations."""

import re
import uuid
from datetime import date
from time import perf_counter
from typing import Any

from restaurant_voice_ai.conversation.confirmation import (
    ConfirmationDecision,
    detect_confirmation,
)
from restaurant_voice_ai.conversation.enums import (
    ConfirmationStatus,
    Intent,
    NextAction,
    ResponseType,
)
from restaurant_voice_ai.conversation.graph import create_conversation_graph
from restaurant_voice_ai.conversation.llm.fallback import DeterministicConversationModel
from restaurant_voice_ai.conversation.llm.google_client import GoogleConversationModel
from restaurant_voice_ai.conversation.llm.schemas import ResponseGenerationInput
from restaurant_voice_ai.conversation.memory.in_memory import InMemoryConversationMemory
from restaurant_voice_ai.conversation.memory.models import (
    ConversationMessage,
    ConversationSnapshot,
    PendingOperation,
)
from restaurant_voice_ai.conversation.models import ConversationDependencies
from restaurant_voice_ai.conversation.state import ConversationState
from restaurant_voice_ai.conversation.tools.dispatcher import (
    ConversationToolDispatcher,
    ToolExecutionContext,
)
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.observability.metrics import metrics
from restaurant_voice_ai.schemas.conversation import ConversationMessageResponse

MUTATION_INTENTS = {
    Intent.CREATE_RESERVATION: "create_reservation",
    Intent.MODIFY_RESERVATION: "modify_reservation",
    Intent.CANCEL_RESERVATION: "cancel_reservation",
}
REQUIRED_FIELDS = {
    "create_reservation": (
        "customer_name",
        "customer_phone",
        "reservation_date",
        "reservation_time",
        "party_size",
    ),
    "modify_reservation": ("reservation_id", "requested_change"),
    "cancel_reservation": ("reservation_id",),
}


class ConversationService:
    def __init__(self, dependencies: ConversationDependencies) -> None:
        self.dependencies = dependencies
        self.legacy_mode = dependencies.settings is None
        self.settings = dependencies.settings or Settings(
            _env_file=None,
            app_env="test",
            cors_origins=[],
            conversation_mode="rules",
            conversation_intent_provider="rules",
            conversation_entity_provider="rules",
            conversation_response_provider="rules",
        )
        self.memory = dependencies.memory or InMemoryConversationMemory(
            self.settings.conversation_memory_ttl_seconds,
            self.settings.conversation_max_history_messages,
        )
        self.fallback_model = DeterministicConversationModel(
            dependencies.classifier, dependencies.extractor
        )
        self.model = dependencies.conversation_model
        if self.model is None and self.settings.conversation_mode != "rules":
            self.model = GoogleConversationModel(
                self.settings.google_api_key, self.settings.google_chat_model
            )
        self.dispatcher = dependencies.dispatcher or ConversationToolDispatcher(
            dependencies.knowledge,
            dependencies.reservations,
            self.settings.max_party_size,
            dependencies.idempotency,
        )
        self.graph = create_conversation_graph(self._process_turn_node)

    async def process_message(
        self,
        message: str,
        language: str = "en",
        *,
        conversation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        debug: bool = False,
    ) -> ConversationMessageResponse:
        started_at = perf_counter()
        identifier = conversation_id or str(uuid.uuid4())
        async with self.memory.conversation_lock(identifier):
            snapshot = await self.memory.load(identifier)
            if snapshot is None:
                snapshot = ConversationSnapshot(conversation_id=identifier)
            result = await self.graph.ainvoke(
                {
                    "message": message,
                    "language": language,
                    "debug": debug,
                    "conversation_id": identifier,
                    "metadata": metadata or {},
                    "snapshot": snapshot.model_dump(mode="json"),
                },
                config={"recursion_limit": 12},
            )
            saved = ConversationSnapshot.model_validate(
                result.get("snapshot", snapshot.model_dump(mode="json"))
            )
            await self.memory.save(saved)
        response_data = dict(result.get("response", {}))
        response_data.setdefault("conversation_id", result.get("conversation_id", identifier))
        response_data.setdefault(
            "turn_number", result.get("turn_number", max(saved.turn_number, 1))
        )
        response = ConversationMessageResponse.model_validate(response_data)
        metrics.conversation_turns.labels(
            response.intent.value,
            response.model_provider,
            str(response.fallback_used).lower(),
        ).inc()
        if self.dependencies.audit is not None:
            await self.dependencies.audit.record_turn(
                message,
                response,
                metadata or {"channel": "text", "language": language},
                (perf_counter() - started_at) * 1000,
            )
        return response

    async def reset(self, conversation_id: str) -> None:
        async with self.memory.conversation_lock(conversation_id):
            await self.memory.delete(conversation_id)

    async def inspect(self, conversation_id: str) -> ConversationSnapshot | None:
        return await self.memory.load(conversation_id)

    async def _process_turn_node(self, state: ConversationState) -> dict[str, Any]:
        snapshot = ConversationSnapshot.model_validate(state["snapshot"])
        message = str(state["message"]).strip()
        language = str(state.get("language", "en"))
        snapshot.turn_number += 1
        snapshot.metadata.update(state.get("metadata", {}))
        snapshot.message_history.append(ConversationMessage(role="user", content=message))
        trace = [
            {"node": name, "status": "completed"}
            for name in (
                "initialize",
                "load_conversation_memory",
                "merge_context",
                "detect_confirmation_or_correction",
                "interpret_message",
                "plan_action",
            )
        ]

        response = await self._handle(snapshot, message, language, trace)
        snapshot.message_history.append(
            ConversationMessage(role="assistant", content=response.response_text)
        )
        response.debug_trace = trace if state.get("debug") else None
        response.trace = response.debug_trace
        return {
            "conversation_id": snapshot.conversation_id,
            "turn_number": snapshot.turn_number,
            "snapshot": snapshot.model_dump(mode="json"),
            "response": response.model_dump(mode="json"),
        }

    async def _handle(
        self,
        snapshot: ConversationSnapshot,
        message: str,
        language: str,
        trace: list[dict[str, Any]],
    ) -> ConversationMessageResponse:
        pending = snapshot.pending_operation
        if (
            pending is not None
            and pending.confirmation_status is ConfirmationStatus.AWAITING_CONFIRMATION
        ):
            decision = detect_confirmation(message)
            if decision is ConfirmationDecision.AFFIRMATIVE and not pending.missing_fields:
                return await self._execute_pending(snapshot, language, trace)
            if decision is ConfirmationDecision.NEGATIVE:
                pending.confirmation_status = ConfirmationStatus.REJECTED
                snapshot.pending_operation = None
                snapshot.accumulated_entities = {}
                snapshot.missing_fields = []
                return self._response(
                    snapshot,
                    Intent(pending.operation_type),
                    ResponseType.ANSWER,
                    "Okay, I won't make that change.",
                )
            if decision is ConfirmationDecision.CORRECTION:
                await self._merge_correction(pending, message, language)
                pending.confirmation_status = ConfirmationStatus.AWAITING_CONFIRMATION
                pending.summary = self._summary(pending.operation_type, pending.validated_arguments)
                return self._confirmation_response(snapshot, pending)

        if pending is not None and pending.missing_fields:
            await self._merge_follow_up(pending, message, language)
            pending.missing_fields = self._missing(
                pending.operation_type, pending.validated_arguments
            )
            snapshot.missing_fields = pending.missing_fields
            snapshot.accumulated_entities = dict(pending.validated_arguments)
            if pending.missing_fields:
                return self._clarification_response(snapshot, pending)
            pending.summary = self._summary(pending.operation_type, pending.validated_arguments)
            pending.confirmation_status = ConfirmationStatus.AWAITING_CONFIRMATION
            return self._confirmation_response(snapshot, pending)

        interpretation, provider, fallback_used = await self._interpret(
            message, language, snapshot.message_history
        )
        snapshot.intent = interpretation.intent.value
        snapshot.model_provider = provider
        snapshot.fallback_used = fallback_used
        entities = dict(interpretation.entities)
        snapshot.accumulated_entities = entities

        if interpretation.intent in MUTATION_INTENTS:
            operation = MUTATION_INTENTS[interpretation.intent]
            missing = self._missing(operation, entities)
            pending = PendingOperation(
                operation_id=uuid.uuid4().hex,
                operation_type=operation,
                validated_arguments=entities,
                missing_fields=missing,
                confirmation_required=self.settings.conversation_require_mutation_confirmation,
                confirmation_status=ConfirmationStatus.AWAITING_CONFIRMATION,
            )
            snapshot.pending_operation = pending
            snapshot.missing_fields = missing
            if missing:
                return self._clarification_response(snapshot, pending)
            pending.summary = self._summary(operation, entities)
            if self.legacy_mode:
                return await self._execute_pending(snapshot, language, trace)
            return self._confirmation_response(snapshot, pending)

        return await self._execute_read(snapshot, interpretation.intent, message, language, trace)

    async def _interpret(
        self, message: str, language: str, history: list[ConversationMessage]
    ) -> tuple[Any, str, bool]:
        if self.settings.conversation_mode != "rules" and self.model is not None:
            try:
                interpreted = await self.model.interpret(message, language, history)
                return interpreted, self.model.provider_name, False
            except Exception:
                pass
        interpreted = await self.fallback_model.interpret(message, language, history)
        return interpreted, "rules", self.settings.conversation_mode != "rules"

    async def _merge_follow_up(
        self, pending: PendingOperation, message: str, language: str
    ) -> None:
        field = pending.missing_fields[0]
        if field == "customer_name" and not re.search(r"\d", message):
            pending.validated_arguments[field] = message.strip()
            return
        if field == "customer_phone":
            digits = re.sub(r"\D", "", message)
            if 7 <= len(digits) <= 15:
                pending.validated_arguments[field] = digits
            return
        if field == "reservation_id":
            value = message.strip().upper()
            if re.fullmatch(r"[A-Z0-9-]{6,40}", value):
                pending.validated_arguments[field] = value
            return
        intent = Intent(pending.operation_type)
        extracted = await self.dependencies.extractor.extract(message, intent, language)
        pending.validated_arguments.update(extracted.model_dump(exclude_none=True))

    async def _merge_correction(
        self, pending: PendingOperation, message: str, language: str
    ) -> None:
        intent = Intent(pending.operation_type)
        extracted = await self.dependencies.extractor.extract(message, intent, language)
        changes = extracted.model_dump(exclude_none=True)
        name = re.search(r"(?:name is|the name is)\s+([^,]+?)(?:\s+not\s+|$)", message, re.I)
        if name:
            changes["customer_name"] = name.group(1).strip()
        phone = re.search(r"(?:phone|number).*?(\+?[\d ()-]{7,20})", message, re.I)
        if phone:
            changes["customer_phone"] = re.sub(r"\D", "", phone.group(1))
        pending.validated_arguments.update(changes)

    async def _execute_read(
        self,
        snapshot: ConversationSnapshot,
        intent: Intent,
        message: str,
        language: str,
        trace: list[dict[str, Any]],
    ) -> ConversationMessageResponse:
        if intent is Intent.GREETING:
            return self._response(
                snapshot, intent, ResponseType.ANSWER, "Hello! How can I help today?"
            )
        if intent not in {Intent.KNOWLEDGE_QUERY, Intent.CHECK_AVAILABILITY}:
            return self._response(
                snapshot,
                intent,
                ResponseType.UNSUPPORTED,
                "I can help with restaurant questions and table reservations.",
                next_action=NextAction.HANDOFF_RECOMMENDED,
            )
        tool_name = (
            "search_restaurant_knowledge"
            if intent is Intent.KNOWLEDGE_QUERY
            else "check_table_availability"
        )
        arguments = (
            {"query": message, "top_k": 5}
            if intent is Intent.KNOWLEDGE_QUERY
            else snapshot.accumulated_entities
        )
        result = await self.dispatcher.execute(
            tool_name,
            arguments,
            ToolExecutionContext(
                snapshot.conversation_id,
                ConfirmationStatus.NOT_REQUIRED,
                0,
                self.settings.conversation_max_tool_iterations,
            ),
        )
        trace.append({"node": "execute_tool", "tool": tool_name, "success": result.success})
        snapshot.last_tool_result = result.model_dump(mode="json")
        if not result.success:
            if intent is Intent.KNOWLEDGE_QUERY:
                return self._response(
                    snapshot,
                    intent,
                    ResponseType.ANSWER,
                    "I couldn't find that in the restaurant information I have.",
                )
            return self._response(
                snapshot,
                intent,
                ResponseType.ERROR,
                result.message or "I couldn't complete that request.",
                next_action=NextAction.RETRY,
            )
        if intent is Intent.KNOWLEDGE_QUERY:
            data = result.data
            context = str(data.get("retrieved_context", ""))
            if not data.get("evidence_found"):
                text = "I couldn't find that in the restaurant information I have."
            else:
                text = context.split("\n", 1)[-1].split("\n\n", 1)[0]
            response = self._response(snapshot, intent, ResponseType.ANSWER, text)
            response.citations = data.get("citations", [])
            return await self._naturalize(response, language, context)
        available = bool(result.data.get("available"))
        text = (
            "Yes, a table is available for that time."
            if available
            else "Sorry, no table is available for that time."
        )
        response = self._response(snapshot, intent, ResponseType.ANSWER, text)
        response.availability = result.data
        return await self._naturalize(response, language, "")

    async def _execute_pending(
        self,
        snapshot: ConversationSnapshot,
        language: str,
        trace: list[dict[str, Any]],
    ) -> ConversationMessageResponse:
        pending = snapshot.pending_operation
        if pending is None:
            return self._response(
                snapshot, Intent.UNKNOWN, ResponseType.ERROR, "There is nothing to confirm."
            )
        pending.confirmation_status = ConfirmationStatus.EXECUTING
        result = await self.dispatcher.execute(
            pending.operation_type,
            pending.validated_arguments,
            ToolExecutionContext(
                snapshot.conversation_id,
                ConfirmationStatus.CONFIRMED,
                0,
                self.settings.conversation_max_tool_iterations,
            ),
        )
        trace.append(
            {
                "node": "execute_confirmed_tool",
                "tool": pending.operation_type,
                "success": result.success,
            }
        )
        snapshot.last_tool_result = result.model_dump(mode="json")
        intent = Intent(pending.operation_type)
        if not result.success:
            pending.confirmation_status = ConfirmationStatus.AWAITING_CONFIRMATION
            return self._response(
                snapshot,
                intent,
                ResponseType.ERROR,
                result.message or "I couldn't complete that request.",
                next_action=NextAction.RETRY,
            )
        pending.confirmation_status = ConfirmationStatus.COMPLETED
        snapshot.pending_operation = None
        snapshot.missing_fields = []
        data = result.data
        code = str(data.get("confirmation_code") or data.get("id") or "")
        action = {
            Intent.CREATE_RESERVATION: (
                f"Your reservation is confirmed. Your confirmation code is {code}."
            ),
            Intent.MODIFY_RESERVATION: f"Reservation {code} has been updated.",
            Intent.CANCEL_RESERVATION: f"Reservation {code} has been cancelled.",
        }[intent]
        response = self._response(snapshot, intent, ResponseType.CONFIRMATION, action)
        response.reservation = data
        return await self._naturalize(response, language, "")

    async def _naturalize(
        self, response: ConversationMessageResponse, language: str, context: str
    ) -> ConversationMessageResponse:
        if (
            self.settings.conversation_mode == "rules"
            or self.settings.conversation_response_provider == "rules"
            or self.model is None
        ):
            return response
        try:
            generated = await self.model.generate_response(
                ResponseGenerationInput(
                    language=language,
                    response_type=response.response_type.value,
                    verified_facts=response.reservation or response.availability or {},
                    retrieved_context=context[:3000],
                    deterministic_fallback=response.response_text,
                )
            )
            if self._safe_generated(generated, response):
                response.response_text = generated
                response.model_provider = self.model.provider_name
                return response
        except Exception:
            pass
        response.fallback_used = True
        return response

    @staticmethod
    def _safe_generated(text: str, response: ConversationMessageResponse) -> bool:
        if not text or len(text) > 600:
            return False
        lowered = text.casefold()
        if any(term in lowered for term in ("api_key", "traceback", "select *", "insert into")):
            return False
        if response.response_type is ResponseType.CONFIRMATION and not response.reservation:
            return False
        return True

    @staticmethod
    def _missing(operation: str, arguments: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        for field in REQUIRED_FIELDS[operation]:
            if field == "requested_change":
                present = any(
                    arguments.get(key) is not None
                    for key in ("requested_date", "requested_time", "requested_party_size")
                )
            else:
                present = arguments.get(field) is not None
            if not present:
                missing.append(field)
        return missing

    @staticmethod
    def _summary(operation: str, arguments: dict[str, Any]) -> str:
        if operation == "create_reservation":
            parsed = date.fromisoformat(str(arguments["reservation_date"]))
            date_text = f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
            hour, minute = map(int, str(arguments["reservation_time"]).split(":"))
            suffix = "AM" if hour < 12 else "PM"
            display_hour = hour % 12 or 12
            return (
                f"book a table for {arguments['party_size']} on {date_text} at "
                f"{display_hour}:{minute:02d} {suffix} under {arguments['customer_name']}"
            )
        if operation == "cancel_reservation":
            return f"cancel reservation {arguments['reservation_id']}"
        changes = []
        if arguments.get("requested_date"):
            changes.append(f"date to {arguments['requested_date']}")
        if arguments.get("requested_time"):
            changes.append(f"time to {arguments['requested_time']}")
        if arguments.get("requested_party_size"):
            changes.append(f"party size to {arguments['requested_party_size']}")
        return f"update reservation {arguments['reservation_id']}: " + ", ".join(changes)

    def _clarification_response(
        self, snapshot: ConversationSnapshot, pending: PendingOperation
    ) -> ConversationMessageResponse:
        field = pending.missing_fields[0]
        questions = {
            "customer_name": "What name should I use for the reservation?",
            "customer_phone": "What phone number should I use?",
            "reservation_date": "What date would you like?",
            "reservation_time": "What time would you like?",
            "party_size": "How many guests will there be?",
            "reservation_id": "What is your reservation or confirmation code?",
            "requested_change": "What would you like to change: the date, time, or party size?",
        }
        next_actions = {
            "customer_name": NextAction.ASK_CUSTOMER_NAME,
            "customer_phone": NextAction.ASK_CUSTOMER_PHONE,
            "reservation_date": NextAction.ASK_RESERVATION_DATE,
            "reservation_time": NextAction.ASK_RESERVATION_TIME,
            "party_size": NextAction.ASK_PARTY_SIZE,
            "reservation_id": NextAction.ASK_RESERVATION_ID,
            "requested_change": NextAction.ASK_REQUESTED_CHANGE,
        }
        return self._response(
            snapshot,
            Intent(pending.operation_type),
            ResponseType.CLARIFICATION,
            questions[field],
            next_action=next_actions[field],
        )

    def _confirmation_response(
        self, snapshot: ConversationSnapshot, pending: PendingOperation
    ) -> ConversationMessageResponse:
        return self._response(
            snapshot,
            Intent(pending.operation_type),
            ResponseType.CLARIFICATION,
            f"Please confirm: {pending.summary}. Shall I proceed?",
            next_action=NextAction.AWAIT_CONFIRMATION,
        )

    def _response(
        self,
        snapshot: ConversationSnapshot,
        intent: Intent,
        response_type: ResponseType,
        text: str,
        *,
        next_action: NextAction = NextAction.NONE,
    ) -> ConversationMessageResponse:
        pending = snapshot.pending_operation
        pending_public = None
        if pending is not None:
            pending_public = {
                "operation_id": pending.operation_id,
                "operation_type": pending.operation_type,
                "missing_fields": pending.missing_fields,
                "confirmation_status": pending.confirmation_status.value,
                "summary": pending.summary,
            }
        return ConversationMessageResponse(
            conversation_id=snapshot.conversation_id,
            turn_number=snapshot.turn_number,
            intent=intent,
            response_type=response_type,
            response_text=text,
            next_action=next_action,
            missing_fields=list(snapshot.missing_fields),
            entities=dict(snapshot.accumulated_entities),
            confirmation_required=bool(pending),
            pending_operation=pending_public,
            model_provider=snapshot.model_provider,
            fallback_used=snapshot.fallback_used,
        )
