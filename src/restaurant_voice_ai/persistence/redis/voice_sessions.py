"""Safe Redis visibility for process-local voice sessions."""

from datetime import UTC, datetime

from pydantic import BaseModel

from restaurant_voice_ai.persistence.redis.client import RedisClientManager


class CoordinatedVoiceSession(BaseModel):
    session_id: str
    conversation_id: str
    node_id: str
    connected_at: datetime
    last_activity_at: datetime
    status: str


class RedisVoiceSessionCoordinator:
    def __init__(self, manager: RedisClientManager, ttl_seconds: int) -> None:
        self.manager = manager
        self.ttl_seconds = ttl_seconds

    async def register(self, session: CoordinatedVoiceSession) -> bool:
        client = await self.manager.get_client()
        return bool(
            await client.set(
                self.manager.key("voice-session", session.session_id),
                session.model_dump_json(),
                ex=self.ttl_seconds,
                nx=True,
            )
        )

    async def touch(self, session_id: str) -> bool:
        client = await self.manager.get_client()
        key = self.manager.key("voice-session", session_id)
        raw = await client.get(key)
        if raw is None:
            return False
        session = CoordinatedVoiceSession.model_validate_json(raw)
        session.last_activity_at = datetime.now(UTC)
        await client.set(key, session.model_dump_json(), ex=self.ttl_seconds, xx=True)
        return True

    async def remove(self, session_id: str) -> None:
        client = await self.manager.get_client()
        await client.delete(self.manager.key("voice-session", session_id))
