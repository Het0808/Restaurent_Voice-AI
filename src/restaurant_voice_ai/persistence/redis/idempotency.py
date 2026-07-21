"""Protocol-neutral in-memory and atomic Redis idempotency stores."""

import asyncio
import json
import time
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from restaurant_voice_ai.persistence.redis.client import RedisClientManager


class IdempotencyStatus(StrEnum):
    RESERVED = "reserved"
    COMPLETED = "completed"
    FAILED = "failed"


class IdempotencyRecord(BaseModel):
    status: IdempotencyStatus
    result: dict[str, Any] = Field(default_factory=dict)


class IdempotencyStore(Protocol):
    async def get(self, key: str) -> IdempotencyRecord | None: ...
    async def reserve(self, key: str, ttl_seconds: int) -> bool: ...
    async def complete(self, key: str, result: dict[str, Any], ttl_seconds: int) -> None: ...
    async def fail(self, key: str, ttl_seconds: int) -> None: ...


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[str, tuple[IdempotencyRecord, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> IdempotencyRecord | None:
        async with self._lock:
            saved = self._records.get(key)
            if saved is None:
                return None
            record, expires_at = saved
            if expires_at <= time.monotonic():
                self._records.pop(key, None)
                return None
            return record.model_copy(deep=True)

    async def reserve(self, key: str, ttl_seconds: int) -> bool:
        async with self._lock:
            saved = self._records.get(key)
            if saved is not None and saved[1] > time.monotonic():
                return False
            self._records[key] = (
                IdempotencyRecord(status=IdempotencyStatus.RESERVED),
                time.monotonic() + ttl_seconds,
            )
            return True

    async def complete(self, key: str, result: dict[str, Any], ttl_seconds: int) -> None:
        async with self._lock:
            self._records[key] = (
                IdempotencyRecord(status=IdempotencyStatus.COMPLETED, result=result),
                time.monotonic() + ttl_seconds,
            )

    async def fail(self, key: str, ttl_seconds: int) -> None:
        async with self._lock:
            self._records[key] = (
                IdempotencyRecord(status=IdempotencyStatus.FAILED),
                time.monotonic() + ttl_seconds,
            )


class RedisIdempotencyStore:
    def __init__(self, manager: RedisClientManager) -> None:
        self.manager = manager

    async def get(self, key: str) -> IdempotencyRecord | None:
        client = await self.manager.get_client()
        raw = await client.get(self.manager.key("idempotency", key))
        return IdempotencyRecord.model_validate_json(raw) if raw else None

    async def reserve(self, key: str, ttl_seconds: int) -> bool:
        client = await self.manager.get_client()
        payload = IdempotencyRecord(status=IdempotencyStatus.RESERVED).model_dump_json()
        return bool(
            await client.set(self.manager.key("idempotency", key), payload, ex=ttl_seconds, nx=True)
        )

    async def complete(self, key: str, result: dict[str, Any], ttl_seconds: int) -> None:
        client = await self.manager.get_client()
        record = IdempotencyRecord(status=IdempotencyStatus.COMPLETED, result=result)
        await client.set(
            self.manager.key("idempotency", key), record.model_dump_json(), ex=ttl_seconds
        )

    async def fail(self, key: str, ttl_seconds: int) -> None:
        client = await self.manager.get_client()
        payload = json.dumps({"status": "failed", "result": {}})
        await client.set(self.manager.key("idempotency", key), payload, ex=ttl_seconds)
