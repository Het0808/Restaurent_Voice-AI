"""Concurrency-safe fixed-window rate limiter."""

import asyncio
import time

from restaurant_voice_ai.rate_limit.base import RateLimitResult


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, tuple[int, int]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        window = int(time.time()) // window_seconds
        async with self._lock:
            saved_window, count = self._windows.get(key, (window, 0))
            if saved_window != window:
                count = 0
            count += 1
            self._windows[key] = (window, count)
        remaining = max(0, limit - count)
        reset = window_seconds - int(time.time()) % window_seconds
        return RateLimitResult(
            allowed=count <= limit,
            limit=limit,
            remaining=remaining,
            reset_after_seconds=reset,
        )
