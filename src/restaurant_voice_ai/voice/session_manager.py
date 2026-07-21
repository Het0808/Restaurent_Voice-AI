"""Concurrency-safe in-process voice-session registry."""

import asyncio
from datetime import UTC, datetime, timedelta

from restaurant_voice_ai.voice.models import SessionStatus, VoiceSessionRuntime


class SessionManager:
    def __init__(self, max_sessions: int, idle_seconds: int, max_seconds: int) -> None:
        self.max_sessions = max_sessions
        self.idle = timedelta(seconds=idle_seconds)
        self.maximum = timedelta(seconds=max_seconds)
        self._sessions: dict[str, VoiceSessionRuntime] = {}
        self._lock = asyncio.Lock()

    async def register(self, runtime: VoiceSessionRuntime) -> None:
        async with self._lock:
            if runtime.session.session_id in self._sessions:
                raise ValueError("Duplicate voice session")
            if len(self._sessions) >= self.max_sessions:
                raise ValueError("Voice session limit reached")
            self._sessions[runtime.session.session_id] = runtime

    async def get(self, session_id: str) -> VoiceSessionRuntime | None:
        async with self._lock:
            return self._sessions.get(session_id)

    async def remove(self, session_id: str) -> None:
        async with self._lock:
            runtime = self._sessions.pop(session_id, None)
        if runtime is not None:
            if runtime.playback_task is not None:
                runtime.playback_task.cancel()
            runtime.clear_audio()
            runtime.session.status = SessionStatus.CLOSED

    async def expired_reason(self, session_id: str) -> str | None:
        runtime = await self.get(session_id)
        if runtime is None:
            return "closed"
        now = datetime.now(UTC)
        if now - runtime.session.connected_at >= self.maximum:
            return "maximum_duration"
        if now - runtime.session.last_activity_at >= self.idle:
            return "idle_timeout"
        return None

    async def active_count(self) -> int:
        async with self._lock:
            return len(self._sessions)

    async def shutdown(self) -> None:
        async with self._lock:
            identifiers = list(self._sessions)
        for identifier in identifiers:
            await self.remove(identifier)
