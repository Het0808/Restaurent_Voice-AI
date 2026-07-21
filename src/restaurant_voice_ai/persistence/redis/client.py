"""Lazy async Redis client lifecycle."""

import asyncio

from redis.asyncio import Redis

from restaurant_voice_ai.core.config import Settings


class RedisClientManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Redis | None = None
        self._lock = asyncio.Lock()

    def key(self, resource: str, identifier: str) -> str:
        return f"{self.settings.redis_prefix}:{self.settings.app_env}:{resource}:{identifier}"

    async def get_client(self) -> Redis:
        async with self._lock:
            if self._client is None:
                self._client = Redis.from_url(
                    self.settings.redis_url.get_secret_value(),
                    decode_responses=False,
                    socket_connect_timeout=self.settings.redis_connect_timeout_seconds,
                    socket_timeout=self.settings.redis_socket_timeout_seconds,
                    max_connections=self.settings.redis_max_connections,
                )
            return self._client

    async def ping(self) -> bool:
        client = await self.get_client()
        return bool(await client.ping())

    async def close(self) -> None:
        async with self._lock:
            client, self._client = self._client, None
        if client is not None:
            await client.aclose()
