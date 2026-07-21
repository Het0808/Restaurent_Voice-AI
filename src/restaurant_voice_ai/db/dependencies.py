"""FastAPI database dependencies."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.db.session import async_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield one correctly closed session per request."""
    async with async_session_factory() as session:
        yield session
