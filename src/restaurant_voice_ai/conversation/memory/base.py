"""Replaceable conversation memory contract."""

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from restaurant_voice_ai.conversation.memory.models import ConversationSnapshot


class ConversationMemory(Protocol):
    async def load(self, conversation_id: str) -> ConversationSnapshot | None: ...

    async def save(self, snapshot: ConversationSnapshot) -> None: ...

    async def delete(self, conversation_id: str) -> None: ...

    def conversation_lock(self, conversation_id: str) -> AbstractAsyncContextManager[None]: ...
