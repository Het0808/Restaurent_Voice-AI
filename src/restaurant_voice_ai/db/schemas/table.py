"""Restaurant table and availability schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TableCreate(BaseModel):
    table_number: int = Field(gt=0)
    capacity: int = Field(ge=1)
    area: str | None = Field(default=None, max_length=80)
    is_active: bool = True


class TableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    table_number: int
    capacity: int
    area: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TableListResponse(BaseModel):
    items: list[TableResponse]
    count: int


class AvailabilityCheckRequest(BaseModel):
    party_size: int = Field(ge=1, le=100)
    reservation_start: datetime
    reservation_end: datetime

    @model_validator(mode="after")
    def validate_times(self) -> "AvailabilityCheckRequest":
        if self.reservation_start.tzinfo is None or self.reservation_end.tzinfo is None:
            raise ValueError("Reservation times must be timezone-aware")
        if self.reservation_end <= self.reservation_start:
            raise ValueError("reservation_end must be after reservation_start")
        return self


class AvailableTableResponse(BaseModel):
    id: uuid.UUID
    table_number: int
    capacity: int
    area: str | None


class AvailabilityResponse(BaseModel):
    available: bool
    tables: list[AvailableTableResponse]
