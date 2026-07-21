"""Wait for PostgreSQL without printing its URL."""

import asyncio
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from restaurant_voice_ai.core.config import Settings


async def main() -> None:
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    deadline = time.monotonic() + settings.startup_database_timeout_seconds
    try:
        while True:
            try:
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
                print("PostgreSQL is ready.")
                return
            except Exception:
                if time.monotonic() >= deadline:
                    raise SystemExit("PostgreSQL readiness timed out") from None
                await asyncio.sleep(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
