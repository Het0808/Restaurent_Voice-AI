"""Network-free Redis conversation-memory contract tests."""

from typing import Any

import pytest

from restaurant_voice_ai.conversation.memory.models import (
    ConversationMessage,
    ConversationSnapshot,
)
from restaurant_voice_ai.persistence.redis.memory import RedisConversationMemory


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.expirations: dict[str, int] = {}

    async def get(self, key: str) -> bytes | None:
        return self.values.get(key)

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int,
        nx: bool | None = None,
        xx: bool | None = None,
    ) -> bool:
        if nx and key in self.values:
            return False
        if xx and key not in self.values:
            return False
        self.values[key] = value.encode()
        self.expirations[key] = ex
        return True

    async def expire(self, key: str, ttl: int) -> bool:
        self.expirations[key] = ttl
        return True

    async def delete(self, key: str) -> int:
        return int(self.values.pop(key, None) is not None)


class FakeManager:
    def __init__(self) -> None:
        self.client = FakeRedis()

    def key(self, resource: str, identifier: str) -> str:
        return f"restaurant_voice_ai:test:{resource}:{identifier}"

    async def get_client(self) -> Any:
        return self.client


@pytest.mark.asyncio
async def test_redis_memory_versions_limits_refreshes_and_deletes() -> None:
    manager = FakeManager()
    memory = RedisConversationMemory(manager, 30, 2)  # type: ignore[arg-type]
    snapshot = ConversationSnapshot(
        conversation_id="redis-conversation",
        message_history=[
            ConversationMessage(role="user", content="one"),
            ConversationMessage(role="assistant", content="two"),
            ConversationMessage(role="user", content="three"),
        ],
    )
    await memory.save(snapshot)
    loaded = await memory.load(snapshot.conversation_id)
    assert loaded is not None
    assert [item.content for item in loaded.message_history] == ["two", "three"]
    loaded.message_history.clear()
    independent = await memory.load(snapshot.conversation_id)
    assert independent and len(independent.message_history) == 2
    key = manager.key("conversation", snapshot.conversation_id)
    assert manager.client.expirations[key] == 30
    await memory.delete(snapshot.conversation_id)
    assert await memory.load(snapshot.conversation_id) is None


@pytest.mark.asyncio
async def test_corrupt_redis_memory_is_removed_safely() -> None:
    manager = FakeManager()
    memory = RedisConversationMemory(manager, 30, 2)  # type: ignore[arg-type]
    key = manager.key("conversation", "corrupt")
    manager.client.values[key] = b"not-json"
    assert await memory.load("corrupt") is None
    assert key not in manager.client.values
