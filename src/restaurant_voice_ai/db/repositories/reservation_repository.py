"""Reservation persistence and overlap queries."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from restaurant_voice_ai.db.models.reservation import Reservation, ReservationStatus

BLOCKING_STATUSES = (ReservationStatus.PENDING, ReservationStatus.CONFIRMED)


class ReservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, reservation: Reservation) -> Reservation:
        self.session.add(reservation)
        await self.session.flush()
        return reservation

    async def get_by_id(
        self, reservation_id: uuid.UUID, *, lock: bool = False
    ) -> Reservation | None:
        statement = (
            select(Reservation)
            .options(selectinload(Reservation.restaurant_table))
            .where(Reservation.id == reservation_id)
        )
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_confirmation_code(self, confirmation_code: str) -> Reservation | None:
        result = await self.session.execute(
            select(Reservation)
            .options(selectinload(Reservation.restaurant_table))
            .where(Reservation.confirmation_code == confirmation_code.upper())
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Reservation]:
        result = await self.session.scalars(
            select(Reservation)
            .options(selectinload(Reservation.restaurant_table))
            .order_by(Reservation.reservation_start)
        )
        return list(result)

    async def has_overlap(
        self,
        table_id: uuid.UUID,
        reservation_start: datetime,
        reservation_end: datetime,
        *,
        exclude_reservation_id: uuid.UUID | None = None,
    ) -> bool:
        statement = select(Reservation.id).where(
            Reservation.restaurant_table_id == table_id,
            Reservation.status.in_(BLOCKING_STATUSES),
            Reservation.reservation_start < reservation_end,
            Reservation.reservation_end > reservation_start,
        )
        if exclude_reservation_id is not None:
            statement = statement.where(Reservation.id != exclude_reservation_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none() is not None

    async def update(self, reservation: Reservation) -> Reservation:
        await self.session.flush()
        return reservation

    async def cancel(self, reservation: Reservation, cancelled_at: datetime) -> Reservation:
        reservation.status = ReservationStatus.CANCELLED
        reservation.cancelled_at = cancelled_at
        await self.session.flush()
        return reservation
