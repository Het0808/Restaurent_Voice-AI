"""Concurrency-safe TTL memory for one application process."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from restaurant_voice_ai.conversation.memory.models import ConversationSnapshot


class InMemoryConversationMemory:
    def __init__(
        self,
        ttl_seconds: int,
        max_history_messages: int,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_history_messages = max_history_messages
        self.now = now or (lambda: datetime.now(UTC))
        self._items: dict[str, ConversationSnapshot] = {}
        self._guard = asyncio.Lock()
        self._conversation_locks: dict[str, asyncio.Lock] = {}

    async def load(self, conversation_id: str) -> ConversationSnapshot | None:
        async with self._guard:
            snapshot = self._items.get(conversation_id)
            if snapshot is None:
                return None
            if self.now() - snapshot.updated_at >= self.ttl:
                self._items.pop(conversation_id, None)
                return None
            return snapshot.model_copy(deep=True)

    async def save(self, snapshot: ConversationSnapshot) -> None:
        copied = snapshot.model_copy(deep=True)
        copied.message_history = copied.message_history[-self.max_history_messages :]
        copied.updated_at = self.now()
        async with self._guard:
            self._items[copied.conversation_id] = copied

    async def delete(self, conversation_id: str) -> None:
        async with self._guard:
            self._items.pop(conversation_id, None)

    @asynccontextmanager
    async def conversation_lock(self, conversation_id: str) -> AsyncIterator[None]:
        async with self._guard:
            lock = self._conversation_locks.setdefault(conversation_id, asyncio.Lock())
        async with lock:
            yield
