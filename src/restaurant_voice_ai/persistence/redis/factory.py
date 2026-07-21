"""Application-scoped Redis and conversation-memory factories."""

from starlette.requests import HTTPConnection

from restaurant_voice_ai.conversation.memory.base import ConversationMemory
from restaurant_voice_ai.conversation.memory.in_memory import InMemoryConversationMemory
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.persistence.redis.client import RedisClientManager
from restaurant_voice_ai.persistence.redis.idempotency import (
    IdempotencyStore,
    InMemoryIdempotencyStore,
    RedisIdempotencyStore,
)
from restaurant_voice_ai.persistence.redis.memory import RedisConversationMemory


def get_redis_manager(connection: HTTPConnection) -> RedisClientManager:
    manager = getattr(connection.app.state, "redis_manager", None)
    if manager is None:
        manager = RedisClientManager(connection.app.state.settings)
        connection.app.state.redis_manager = manager
    return manager


def get_conversation_memory(connection: HTTPConnection) -> ConversationMemory:
    existing: ConversationMemory | None = getattr(connection.app.state, "conversation_memory", None)
    if existing is not None:
        return existing
    settings: Settings = connection.app.state.settings
    memory: ConversationMemory
    if settings.conversation_memory_backend == "redis":
        memory = RedisConversationMemory(
            get_redis_manager(connection),
            settings.conversation_memory_ttl_seconds,
            settings.conversation_max_history_messages,
        )
    else:
        memory = InMemoryConversationMemory(
            settings.conversation_memory_ttl_seconds,
            settings.conversation_max_history_messages,
        )
    connection.app.state.conversation_memory = memory
    return memory


def get_idempotency_store(connection: HTTPConnection) -> IdempotencyStore:
    existing: IdempotencyStore | None = getattr(connection.app.state, "idempotency_store", None)
    if existing is not None:
        return existing
    settings: Settings = connection.app.state.settings
    store: IdempotencyStore
    if settings.idempotency_backend == "redis":
        store = RedisIdempotencyStore(get_redis_manager(connection))
    else:
        store = InMemoryIdempotencyStore()
    connection.app.state.idempotency_store = store
    return store
