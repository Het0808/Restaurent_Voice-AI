"""Reservation ORM model."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant_voice_ai.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from restaurant_voice_ai.db.models.restaurant_table import RestaurantTable


class ReservationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Reservation(TimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("party_size > 0", name="ck_reservations_party_size_positive"),
        CheckConstraint(
            "reservation_end > reservation_start", name="ck_reservations_valid_time_range"
        ),
        Index(
            "ix_reservations_table_times",
            "restaurant_table_id",
            "reservation_start",
            "reservation_end",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    confirmation_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(160))
    customer_phone: Mapped[str] = mapped_column(String(32), index=True)
    customer_email: Mapped[str | None] = mapped_column(String(254))
    party_size: Mapped[int] = mapped_column(Integer)
    reservation_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reservation_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(
            ReservationStatus,
            name="reservation_status",
            values_callable=lambda values: [item.value for item in values],
        ),
        default=ReservationStatus.CONFIRMED,
        index=True,
    )
    special_requests: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(8))
    restaurant_table_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("restaurant_tables.id", ondelete="RESTRICT"), nullable=False
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    restaurant_table: Mapped["RestaurantTable"] = relationship(back_populates="reservations")
