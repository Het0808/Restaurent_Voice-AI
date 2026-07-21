"""Idempotent persistence operations for telephony call sessions."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.db.models.call_session import CallSession


class CallSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, call_sid: str) -> CallSession | None:
        result = await self.session.scalar(
            select(CallSession).where(CallSession.external_call_id == call_sid)
        )
        return result

    async def get_or_create(
        self,
        call_sid: str,
        caller: str | None,
        destination: str | None,
        direction: str | None,
        status: str = "in-progress",
    ) -> CallSession:
        existing = await self.get(call_sid)
        if existing is not None:
            return existing
        call = CallSession(
            external_call_id=call_sid,
            customer_phone=caller,
            destination_phone=destination,
            direction=direction,
            status=status,
            started_at=datetime.now(UTC),
        )
        self.session.add(call)
        await self.session.commit()
        await self.session.refresh(call)
        return call

    async def update_status(
        self,
        call_sid: str,
        status: str,
        *,
        duration: int | None = None,
        error: str | None = None,
    ) -> CallSession | None:
        call = await self.get(call_sid)
        if call is None:
            return None
        call.status = status
        call.duration_seconds = duration if duration is not None else call.duration_seconds
        call.error_details = error[:1000] if error else call.error_details
        if status in {"completed", "busy", "failed", "no-answer", "canceled"}:
            call.ended_at = call.ended_at or datetime.now(UTC)
        await self.session.commit()
        return call

    async def mark_escalated(self, call_sid: str, reason: str) -> None:
        call = await self.get(call_sid)
        if call is not None:
            call.escalated = True
            call.escalation_reason = reason[:160]
            await self.session.commit()
