"""Ownership-safe Redis and in-memory locks."""

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import Any, cast

from restaurant_voice_ai.persistence.redis.client import RedisClientManager

RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


class RedisDistributedLock:
    def __init__(self, manager: RedisClientManager, ttl_seconds: int = 30) -> None:
        self.manager = manager
        self.ttl_seconds = ttl_seconds

    @asynccontextmanager
    async def acquire(self, identifier: str, timeout: float = 5) -> AsyncIterator[None]:
        client = await self.manager.get_client()
        key = self.manager.key("lock", identifier)
        token = uuid.uuid4().hex
        deadline = asyncio.get_running_loop().time() + timeout
        while not await client.set(key, token, ex=self.ttl_seconds, nx=True):
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("Distributed lock acquisition timed out")
            await asyncio.sleep(0.05)
        try:
            yield
        finally:
            await cast(Awaitable[Any], client.eval(RELEASE_SCRIPT, 1, key, token))


class InMemoryDistributedLock:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, identifier: str, timeout: float = 5) -> AsyncIterator[None]:
        async with self._guard:
            lock = self._locks.setdefault(identifier, asyncio.Lock())
        await asyncio.wait_for(lock.acquire(), timeout)
        try:
            yield
        finally:
            lock.release()
