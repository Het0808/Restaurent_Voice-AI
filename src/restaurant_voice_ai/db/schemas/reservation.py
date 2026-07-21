"""Reservation request and response schemas."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from restaurant_voice_ai.db.models.reservation import ReservationStatus
from restaurant_voice_ai.db.schemas.table import TableResponse

LanguageCode = Literal["en", "hi", "gu"]


class ReservationCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=160)
    customer_phone: str = Field(min_length=1, max_length=32)
    customer_email: str | None = Field(default=None, max_length=254)
    party_size: int = Field(ge=1, le=100)
    reservation_start: datetime
    reservation_end: datetime | None = None
    special_requests: str | None = Field(default=None, max_length=1000)
    language: LanguageCode | None = None

    @field_validator("customer_name", "customer_phone")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @model_validator(mode="after")
    def validate_times(self) -> "ReservationCreate":
        if self.reservation_start.tzinfo is None:
            raise ValueError("reservation_start must be timezone-aware")
        if self.reservation_start <= datetime.now(UTC):
            raise ValueError("reservation_start must be in the future")
        if self.reservation_end is not None:
            if self.reservation_end.tzinfo is None:
                raise ValueError("reservation_end must be timezone-aware")
            if self.reservation_end <= self.reservation_start:
                raise ValueError("reservation_end must be after reservation_start")
        return self


class ReservationUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=1, max_length=160)
    customer_phone: str | None = Field(default=None, min_length=1, max_length=32)
    customer_email: str | None = Field(default=None, max_length=254)
    party_size: int | None = Field(default=None, ge=1, le=100)
    reservation_start: datetime | None = None
    reservation_end: datetime | None = None
    special_requests: str | None = Field(default=None, max_length=1000)
    language: LanguageCode | None = None

    @field_validator("customer_name", "customer_phone")
    @classmethod
    def reject_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Value must not be blank")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_update(self) -> "ReservationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        for value in (self.reservation_start, self.reservation_end):
            if value is not None and value.tzinfo is None:
                raise ValueError("Reservation times must be timezone-aware")
        if (
            self.reservation_start is not None
            and self.reservation_end is not None
            and self.reservation_end <= self.reservation_start
        ):
            raise ValueError("reservation_end must be after reservation_start")
        return self


class ReservationCancelRequest(BaseModel):
    confirmation_code: str | None = Field(default=None, min_length=1, max_length=20)


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    confirmation_code: str
    customer_name: str
    customer_phone: str
    customer_email: str | None
    party_size: int
    reservation_start: datetime
    reservation_end: datetime
    status: ReservationStatus
    special_requests: str | None
    language: str | None
    restaurant_table_id: uuid.UUID
    restaurant_table: TableResponse
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None


class ReservationListResponse(BaseModel):
    items: list[ReservationResponse]
    count: int
