"""Minimal future-facing call session persistence model."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from restaurant_voice_ai.db.base import Base, TimestampMixin


class CallSessionStatus(StrEnum):
    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BUSY = "busy"
    FAILED = "failed"
    NO_ANSWER = "no-answer"
    CANCELED = "canceled"


class CallSession(TimestampMixin, Base):
    __tablename__ = "call_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    external_call_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    customer_phone: Mapped[str | None] = mapped_column(String(32))
    destination_phone: Mapped[str | None] = mapped_column(String(32))
    direction: Mapped[str | None] = mapped_column(String(32))
    detected_language: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(24), default=CallSessionStatus.QUEUED.value)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[str | None] = mapped_column(String(160))
    reservation_outcome: Mapped[str | None] = mapped_column(String(64))
    error_details: Mapped[str | None] = mapped_column(Text)
