"""Versioned Redis implementation of Stage 6 conversation memory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pydantic import BaseModel, ValidationError

from restaurant_voice_ai.conversation.memory.models import ConversationSnapshot
from restaurant_voice_ai.persistence.redis.client import RedisClientManager
from restaurant_voice_ai.persistence.redis.locks import RedisDistributedLock


class StoredConversation(BaseModel):
    schema_version: int = 1
    snapshot: ConversationSnapshot


class RedisConversationMemory:
    def __init__(
        self, manager: RedisClientManager, ttl_seconds: int, max_history_messages: int
    ) -> None:
        self.manager = manager
        self.ttl_seconds = ttl_seconds
        self.max_history_messages = max_history_messages
        self.locks = RedisDistributedLock(manager)

    async def load(self, conversation_id: str) -> ConversationSnapshot | None:
        client = await self.manager.get_client()
        raw = await client.get(self.manager.key("conversation", conversation_id))
        if raw is None:
            return None
        try:
            stored = StoredConversation.model_validate_json(raw)
        except ValidationError:
            await self.delete(conversation_id)
            return None
        if stored.schema_version != 1:
            return None
        await client.expire(self.manager.key("conversation", conversation_id), self.ttl_seconds)
        return stored.snapshot.model_copy(deep=True)

    async def save(self, snapshot: ConversationSnapshot) -> None:
        safe = snapshot.model_copy(deep=True)
        safe.message_history = safe.message_history[-self.max_history_messages :]
        payload = StoredConversation(snapshot=safe).model_dump_json()
        client = await self.manager.get_client()
        await client.set(
            self.manager.key("conversation", snapshot.conversation_id),
            payload,
            ex=self.ttl_seconds,
        )

    async def delete(self, conversation_id: str) -> None:
        client = await self.manager.get_client()
        await client.delete(self.manager.key("conversation", conversation_id))

    @asynccontextmanager
    async def conversation_lock(self, conversation_id: str) -> AsyncIterator[None]:
        async with self.locks.acquire(conversation_id):
            yield
