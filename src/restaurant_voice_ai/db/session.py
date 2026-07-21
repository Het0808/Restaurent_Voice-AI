"""Process-wide async SQLAlchemy engine and session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from restaurant_voice_ai.core.config import get_settings

settings = get_settings()
engine: AsyncEngine = create_async_engine(settings.database_url, echo=settings.db_echo)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def dispose_engine() -> None:
    """Release pooled database connections during application shutdown."""
    await engine.dispose()
