"""Opt-in PostgreSQL and Redis integration checks."""

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from restaurant_voice_ai.conversation.memory.models import ConversationSnapshot
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.persistence.redis.client import RedisClientManager
from restaurant_voice_ai.persistence.redis.memory import RedisConversationMemory


@pytest.mark.integration
@pytest.mark.redis
@pytest.mark.asyncio
async def test_real_redis_conversation_memory() -> None:
    if not os.getenv("REDIS_ENABLED"):
        pytest.skip("Redis integration is not configured")
    settings = Settings(redis_prefix=f"test-{uuid.uuid4().hex}")
    manager = RedisClientManager(settings)
    memory = RedisConversationMemory(manager, 30, 10)
    snapshot = ConversationSnapshot(conversation_id="integration-conversation", turn_number=2)
    await memory.save(snapshot)
    loaded = await memory.load(snapshot.conversation_id)
    assert loaded and loaded.turn_number == 2
    await memory.delete(snapshot.conversation_id)
    await manager.close()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.asyncio
async def test_postgres_migration_tables_exist() -> None:
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("PostgreSQL integration is not configured")
    engine = create_async_engine(url)
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT to_regclass('public.conversation_turns')"))
        assert result.scalar_one() == "conversation_turns"
    await engine.dispose()
