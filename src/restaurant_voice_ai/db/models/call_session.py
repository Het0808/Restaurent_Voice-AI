"""Minimal future-facing call session persistence model."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from restaurant_voice_ai.db.base import Base, TimestampMixin


class CallSessionStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class CallSession(TimestampMixin, Base):
    __tablename__ = "call_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    external_call_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    customer_phone: Mapped[str | None] = mapped_column(String(32))
    detected_language: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[CallSessionStatus] = mapped_column(
        Enum(
            CallSessionStatus,
            name="call_session_status",
            values_callable=lambda values: [item.value for item in values],
        ),
        default=CallSessionStatus.STARTED,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
