"""Restaurant table ORM model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant_voice_ai.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from restaurant_voice_ai.db.models.reservation import Reservation


class RestaurantTable(TimestampMixin, Base):
    __tablename__ = "restaurant_tables"
    __table_args__ = (
        CheckConstraint("table_number > 0", name="ck_restaurant_tables_number_positive"),
        CheckConstraint("capacity >= 1", name="ck_restaurant_tables_capacity_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    table_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    area: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="restaurant_table")
