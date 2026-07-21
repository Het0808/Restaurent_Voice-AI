"""Rate limiter protocol and result."""

from typing import Protocol

from pydantic import BaseModel


class RateLimitResult(BaseModel):
    allowed: bool
    limit: int
    remaining: int
    reset_after_seconds: int


class RateLimiter(Protocol):
    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult: ...
