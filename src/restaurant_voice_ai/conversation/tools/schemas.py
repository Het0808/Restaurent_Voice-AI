"""Strict schemas for supported conversation tools."""

import re
from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchRestaurantKnowledge(StrictToolArguments):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class CheckTableAvailability(StrictToolArguments):
    reservation_date: date
    reservation_time: time
    party_size: int = Field(ge=1, le=100)


class CreateReservation(StrictToolArguments):
    customer_name: str = Field(min_length=1, max_length=160)
    customer_phone: str = Field(min_length=7, max_length=20)
    reservation_date: date
    reservation_time: time
    party_size: int = Field(ge=1, le=100)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = (
            "+" + re.sub(r"\D", "", value) if value.startswith("+") else re.sub(r"\D", "", value)
        )
        if not 7 <= len(normalized.lstrip("+")) <= 15:
            raise ValueError("Invalid phone number")
        return normalized


class ModifyReservation(StrictToolArguments):
    reservation_id: str = Field(min_length=6, max_length=40, pattern=r"^[A-Za-z0-9-]+$")
    requested_date: date | None = None
    requested_time: time | None = None
    requested_party_size: int | None = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def require_change(self) -> "ModifyReservation":
        if not any((self.requested_date, self.requested_time, self.requested_party_size)):
            raise ValueError("At least one requested change is required")
        return self


class CancelReservation(StrictToolArguments):
    reservation_id: str = Field(min_length=6, max_length=40, pattern=r"^[A-Za-z0-9-]+$")
