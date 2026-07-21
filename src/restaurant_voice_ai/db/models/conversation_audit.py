"""Safe PostgreSQL/SQLAlchemy conversation audit models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from restaurant_voice_ai.db.base import Base, TimestampMixin


class ConversationSessionAudit(TimestampMixin, Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    channel: Mapped[str] = mapped_column(String(16), default="text")
    language: Mapped[str] = mapped_column(String(16), default="en")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="active")
    total_turns: Mapped[int] = mapped_column(Integer, default=0)
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ConversationTurnAudit(Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        UniqueConstraint("conversation_id", "turn_number", name="uq_conversation_turn_number"),
        Index("ix_conversation_turns_conversation_id", "conversation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[str] = mapped_column(String(64))
    turn_number: Mapped[int] = mapped_column(Integer)
    user_message_masked: Mapped[str] = mapped_column(Text)
    assistant_message: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(48))
    response_type: Mapped[str] = mapped_column(String(48))
    tool_name: Mapped[str | None] = mapped_column(String(64))
    tool_success: Mapped[bool | None] = mapped_column(Boolean)
    confirmation_status: Mapped[str | None] = mapped_column(String(48))
    model_provider: Mapped[str | None] = mapped_column(String(48))
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ToolAuditEvent(Base):
    __tablename__ = "tool_audit_events"
    __table_args__ = (Index("ix_tool_audit_conversation_id", "conversation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[str] = mapped_column(String(64))
    turn_number: Mapped[int] = mapped_column(Integer)
    tool_name: Mapped[str] = mapped_column(String(64))
    operation_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    idempotency_key_hash: Mapped[str | None] = mapped_column(String(64))
    reservation_id: Mapped[str | None] = mapped_column(String(64))
    safe_arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
