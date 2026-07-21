"""Reusable API response models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ResponseModel(BaseModel):
    """Base response model with explicit schema behavior."""

    model_config = ConfigDict(extra="forbid")


class HealthResponse(ResponseModel):
    status: Literal["healthy"]
    service: str
    version: str
    environment: str


class RootResponse(ResponseModel):
    message: str
    docs: str
    health: str


class ErrorResponse(ResponseModel):
    code: str
    message: str
