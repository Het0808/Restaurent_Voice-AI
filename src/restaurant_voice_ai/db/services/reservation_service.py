"""Transactional reservation and availability business logic."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.core.exceptions import (
    BusinessValidationError,
    DatabaseOperationError,
    InvalidReservationStateError,
    ReservationConflictError,
    ResourceNotFoundError,
)
from restaurant_voice_ai.db.models.reservation import Reservation, ReservationStatus
from restaurant_voice_ai.db.models.restaurant_table import RestaurantTable
from restaurant_voice_ai.db.repositories.reservation_repository import ReservationRepository
from restaurant_voice_ai.db.repositories.table_repository import TableRepository
from restaurant_voice_ai.db.schemas.reservation import ReservationCreate, ReservationUpdate

logger = logging.getLogger(__name__)


class ReservationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.reservations = ReservationRepository(session)
        self.tables = TableRepository(session)

    def validate_party_size(self, party_size: int) -> None:
        if party_size > self.settings.max_party_size:
            raise BusinessValidationError(
                f"party_size must not exceed {self.settings.max_party_size}"
            )

    @staticmethod
    def ensure_aware(value: datetime) -> datetime:
        """Normalize SQLite test timestamps; PostgreSQL returns aware timestamps."""
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value

    @staticmethod
    def validate_time_range(reservation_start: datetime, reservation_end: datetime) -> None:
        if reservation_start.tzinfo is None or reservation_end.tzinfo is None:
            raise BusinessValidationError("Reservation times must be timezone-aware")
        if reservation_end <= reservation_start:
            raise BusinessValidationError("reservation_end must be after reservation_start")

    async def _available_tables(
        self,
        party_size: int,
        reservation_start: datetime,
        reservation_end: datetime,
        *,
        lock: bool = False,
        exclude_reservation_id: uuid.UUID | None = None,
    ) -> list[RestaurantTable]:
        self.validate_party_size(party_size)
        self.validate_time_range(reservation_start, reservation_end)
        candidates = await self.tables.find_candidates(party_size, lock=lock)
        available: list[RestaurantTable] = []
        for table in candidates:
            if not await self.reservations.has_overlap(
                table.id,
                reservation_start,
                reservation_end,
                exclude_reservation_id=exclude_reservation_id,
            ):
                available.append(table)
        return available

    async def check_availability(
        self, party_size: int, reservation_start: datetime, reservation_end: datetime
    ) -> list[RestaurantTable]:
        return await self._available_tables(party_size, reservation_start, reservation_end)

    async def create(self, data: ReservationCreate) -> Reservation:
        self.validate_party_size(data.party_size)
        reservation_end = data.reservation_end or (
            data.reservation_start
            + timedelta(minutes=self.settings.default_reservation_duration_minutes)
        )
        self.validate_time_range(data.reservation_start, reservation_end)
        try:
            async with self.session.begin():
                available = await self._available_tables(
                    data.party_size,
                    data.reservation_start,
                    reservation_end,
                    lock=True,
                )
                if not available:
                    raise ReservationConflictError()
                table = available[0]
                reservation = Reservation(
                    confirmation_code=self._confirmation_code(),
                    customer_name=data.customer_name,
                    customer_phone=data.customer_phone,
                    customer_email=data.customer_email,
                    party_size=data.party_size,
                    reservation_start=data.reservation_start,
                    reservation_end=reservation_end,
                    status=ReservationStatus.CONFIRMED,
                    special_requests=data.special_requests,
                    language=data.language,
                    restaurant_table_id=table.id,
                    restaurant_table=table,
                )
                await self.reservations.create(reservation)
            # Confirmation is returned only after the transaction commit above succeeds.
            saved = await self.reservations.get_by_id(reservation.id)
            if saved is None:
                raise DatabaseOperationError()
            return saved
        except (ReservationConflictError, BusinessValidationError):
            raise
        except SQLAlchemyError as exc:
            logger.exception("Database failure while creating reservation")
            raise DatabaseOperationError() from exc

    async def get(self, reservation_id: uuid.UUID) -> Reservation:
        reservation = await self.reservations.get_by_id(reservation_id)
        if reservation is None:
            raise ResourceNotFoundError("Reservation not found")
        return reservation

    async def get_by_code(self, confirmation_code: str) -> Reservation:
        reservation = await self.reservations.get_by_confirmation_code(confirmation_code)
        if reservation is None:
            raise ResourceNotFoundError("Reservation not found")
        return reservation

    async def list_all(self) -> list[Reservation]:
        return await self.reservations.list_all()

    async def update(self, reservation_id: uuid.UUID, data: ReservationUpdate) -> Reservation:
        try:
            async with self.session.begin():
                reservation = await self.reservations.get_by_id(reservation_id, lock=True)
                if reservation is None:
                    raise ResourceNotFoundError("Reservation not found")
                if reservation.status == ReservationStatus.CANCELLED:
                    raise InvalidReservationStateError("Cancelled reservations cannot be modified")

                changes = data.model_dump(exclude_unset=True)
                schedule_changed = bool(
                    {"party_size", "reservation_start", "reservation_end"} & changes.keys()
                )
                if schedule_changed:
                    current_start = self.ensure_aware(reservation.reservation_start)
                    current_end = self.ensure_aware(reservation.reservation_end)
                    original_duration = current_end - current_start
                    start = data.reservation_start or current_start
                    end = data.reservation_end
                    if end is None:
                        end = start + original_duration
                    party_size = data.party_size or reservation.party_size
                    self.validate_party_size(party_size)
                    self.validate_time_range(start, end)
                    if start <= datetime.now(UTC):
                        raise BusinessValidationError("reservation_start must be in the future")

                    available = await self._available_tables(
                        party_size,
                        start,
                        end,
                        lock=True,
                        exclude_reservation_id=reservation.id,
                    )
                    current = next(
                        (
                            table
                            for table in available
                            if table.id == reservation.restaurant_table_id
                        ),
                        None,
                    )
                    selected = current or (available[0] if available else None)
                    if selected is None:
                        raise ReservationConflictError()
                    changes["restaurant_table_id"] = selected.id
                    reservation.restaurant_table = selected
                    changes["reservation_start"] = start
                    changes["reservation_end"] = end

                for field, value in changes.items():
                    setattr(reservation, field, value)
                await self.reservations.update(reservation)
            saved = await self.reservations.get_by_id(reservation_id)
            if saved is None:
                raise DatabaseOperationError()
            return saved
        except (
            ResourceNotFoundError,
            InvalidReservationStateError,
            ReservationConflictError,
            BusinessValidationError,
        ):
            raise
        except SQLAlchemyError as exc:
            logger.exception("Database failure while updating reservation")
            raise DatabaseOperationError() from exc

    async def cancel(
        self, reservation_id: uuid.UUID, confirmation_code: str | None = None
    ) -> Reservation:
        try:
            async with self.session.begin():
                if confirmation_code is not None:
                    reservation = await self.reservations.get_by_confirmation_code(
                        confirmation_code
                    )
                    if reservation is not None and reservation.id != reservation_id:
                        raise ResourceNotFoundError("Reservation not found")
                else:
                    reservation = await self.reservations.get_by_id(reservation_id, lock=True)
                if reservation is None:
                    raise ResourceNotFoundError("Reservation not found")
                if reservation.status != ReservationStatus.CANCELLED:
                    await self.reservations.cancel(reservation, datetime.now(UTC))
            saved = await self.reservations.get_by_id(reservation_id)
            if saved is None:
                raise DatabaseOperationError()
            return saved
        except ResourceNotFoundError:
            raise
        except SQLAlchemyError as exc:
            logger.exception("Database failure while cancelling reservation")
            raise DatabaseOperationError() from exc

    @staticmethod
    def _confirmation_code() -> str:
        return f"RSV-{uuid.uuid4().hex[:8].upper()}"
