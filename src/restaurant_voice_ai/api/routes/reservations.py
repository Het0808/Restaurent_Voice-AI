"""Reservation and availability API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.core.config import Settings, get_settings
from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.db.schemas.reservation import (
    ReservationCancelRequest,
    ReservationCreate,
    ReservationListResponse,
    ReservationResponse,
    ReservationUpdate,
)
from restaurant_voice_ai.db.schemas.table import (
    AvailabilityCheckRequest,
    AvailabilityResponse,
    AvailableTableResponse,
)
from restaurant_voice_ai.db.services.reservation_service import ReservationService

router = APIRouter(prefix="/reservations", tags=["Reservations"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def service(session: AsyncSession, settings: Settings) -> ReservationService:
    return ReservationService(session, settings)


@router.post("/availability", response_model=AvailabilityResponse)
async def check_availability(
    data: AvailabilityCheckRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> AvailabilityResponse:
    tables = await service(session, settings).check_availability(
        data.party_size, data.reservation_start, data.reservation_end
    )
    items = [AvailableTableResponse.model_validate(table, from_attributes=True) for table in tables]
    return AvailabilityResponse(available=bool(items), tables=items)


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    data: ReservationCreate,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ReservationResponse:
    reservation = await service(session, settings).create(data)
    return ReservationResponse.model_validate(reservation)


@router.get("", response_model=ReservationListResponse)
async def list_reservations(
    session: SessionDependency, settings: SettingsDependency
) -> ReservationListResponse:
    reservations = await service(session, settings).list_all()
    items = [ReservationResponse.model_validate(item) for item in reservations]
    return ReservationListResponse(items=items, count=len(items))


@router.get("/code/{confirmation_code}", response_model=ReservationResponse)
async def get_reservation_by_code(
    confirmation_code: str,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ReservationResponse:
    reservation = await service(session, settings).get_by_code(confirmation_code)
    return ReservationResponse.model_validate(reservation)


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: uuid.UUID,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ReservationResponse:
    reservation = await service(session, settings).get(reservation_id)
    return ReservationResponse.model_validate(reservation)


@router.patch("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: uuid.UUID,
    data: ReservationUpdate,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ReservationResponse:
    reservation = await service(session, settings).update(reservation_id, data)
    return ReservationResponse.model_validate(reservation)


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    data: ReservationCancelRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ReservationResponse:
    reservation = await service(session, settings).cancel(reservation_id, data.confirmation_code)
    return ReservationResponse.model_validate(reservation)
