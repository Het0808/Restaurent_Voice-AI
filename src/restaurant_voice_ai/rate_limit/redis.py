"""Atomic Redis fixed-window rate limiter."""

import time
from collections.abc import Awaitable
from typing import Any, cast

from restaurant_voice_ai.persistence.redis.client import RedisClientManager
from restaurant_voice_ai.rate_limit.base import RateLimitResult

RATE_SCRIPT = """
local count = redis.call('incr', KEYS[1])
if count == 1 then redis.call('expire', KEYS[1], ARGV[1]) end
local ttl = redis.call('ttl', KEYS[1])
return {count, ttl}
"""


class RedisRateLimiter:
    def __init__(self, manager: RedisClientManager) -> None:
        self.manager = manager

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        client = await self.manager.get_client()
        window = int(time.time()) // window_seconds
        redis_key = self.manager.key("rate", f"{key}:{window}")
        raw = await cast(
            Awaitable[Any], client.eval(RATE_SCRIPT, 1, redis_key, str(window_seconds))
        )
        count, ttl = raw
        numeric_count, numeric_ttl = int(count), max(0, int(ttl))
        return RateLimitResult(
            allowed=numeric_count <= limit,
            limit=limit,
            remaining=max(0, limit - numeric_count),
            reset_after_seconds=numeric_ttl,
        )
