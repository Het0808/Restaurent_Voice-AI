"""Best-effort safe conversation audit service."""

import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.db.models.conversation_audit import (
    ConversationSessionAudit,
    ConversationTurnAudit,
    ToolAuditEvent,
)
from restaurant_voice_ai.observability.redaction import mask_phone_numbers
from restaurant_voice_ai.schemas.conversation import ConversationMessageResponse

logger = logging.getLogger(__name__)


class ConversationAudit(Protocol):
    async def record_turn(
        self,
        user_message: str,
        response: ConversationMessageResponse,
        metadata: dict[str, Any],
        latency_ms: float,
    ) -> None: ...


class SqlConversationAudit:
    """Synchronously commits audit after a turn; failures remain noncritical."""

    def __init__(self, session: AsyncSession, store_transcripts: bool = True) -> None:
        self.session = session
        self.store_transcripts = store_transcripts

    async def record_turn(
        self,
        user_message: str,
        response: ConversationMessageResponse,
        metadata: dict[str, Any],
        latency_ms: float,
    ) -> None:
        try:
            existing = await self.session.scalar(
                select(ConversationSessionAudit).where(
                    ConversationSessionAudit.conversation_id == response.conversation_id
                )
            )
            now = datetime.now(UTC)
            if existing is None:
                existing = ConversationSessionAudit(
                    conversation_id=response.conversation_id,
                    channel=str(metadata.get("channel", "text")),
                    language=str(metadata.get("language", "en")),
                    started_at=now,
                    status="active",
                    total_turns=response.turn_number,
                    safe_metadata={"channel": str(metadata.get("channel", "text"))},
                )
                self.session.add(existing)
            else:
                existing.total_turns = max(existing.total_turns, response.turn_number)
            pending = response.pending_operation or {}
            mutation_intents = {
                "create_reservation",
                "modify_reservation",
                "cancel_reservation",
            }
            inferred_tool = (
                response.intent.value if response.intent.value in mutation_intents else None
            )
            citations = [
                {
                    "source": item.source_filename,
                    "chunk_id": item.chunk_id,
                    "section": item.section,
                }
                for item in response.citations
            ]
            self.session.add(
                ConversationTurnAudit(
                    conversation_id=response.conversation_id,
                    turn_number=response.turn_number,
                    user_message_masked=(
                        mask_phone_numbers(user_message) if self.store_transcripts else "[disabled]"
                    ),
                    assistant_message=response.response_text,
                    intent=response.intent.value,
                    response_type=response.response_type.value,
                    tool_name=pending.get("operation_type") or inferred_tool,
                    tool_success=(
                        bool(response.reservation) if inferred_tool is not None else None
                    ),
                    confirmation_status=(
                        pending.get("confirmation_status")
                        or ("completed" if response.reservation else None)
                    ),
                    model_provider=response.model_provider,
                    fallback_used=response.fallback_used,
                    latency_ms=latency_ms,
                    citations=citations,
                    error_code=None,
                    created_at=now,
                )
            )
            if response.intent.value in mutation_intents:
                safe_arguments = {
                    key: (mask_phone_numbers(str(value)) if key == "customer_phone" else value)
                    for key, value in response.entities.items()
                    if key not in {"customer_name"}
                }
                reservation_id = None
                if response.reservation:
                    reservation_id = str(
                        response.reservation.get("id")
                        or response.reservation.get("confirmation_code")
                        or ""
                    )
                self.session.add(
                    ToolAuditEvent(
                        conversation_id=response.conversation_id,
                        turn_number=response.turn_number,
                        tool_name=response.intent.value,
                        operation_type=response.intent.value,
                        status="success" if response.reservation else "pending",
                        idempotency_key_hash=None,
                        reservation_id=reservation_id or None,
                        safe_arguments=safe_arguments,
                        error_code=None,
                        created_at=now,
                    )
                )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.exception("Conversation audit persistence failed")
