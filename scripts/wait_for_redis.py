"""Wait for required Redis without printing credentials."""

import asyncio
import time

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.persistence.redis.client import RedisClientManager


async def main() -> None:
    settings = Settings()
    required = settings.redis_enabled and any(
        item == "redis"
        for item in (
            settings.conversation_memory_backend,
            settings.idempotency_backend,
            settings.rate_limit_backend,
        )
    )
    if not required:
        print("Redis is not required by configured backends.")
        return
    manager = RedisClientManager(settings)
    deadline = time.monotonic() + settings.startup_redis_timeout_seconds
    try:
        while True:
            try:
                if await manager.ping():
                    print("Redis is ready.")
                    return
            except Exception:
                if time.monotonic() >= deadline:
                    raise SystemExit("Redis readiness timed out") from None
                await asyncio.sleep(1)
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
