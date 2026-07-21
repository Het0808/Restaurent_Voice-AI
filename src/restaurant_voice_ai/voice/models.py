"""Provider-neutral voice models and runtime session state."""

import asyncio
from collections import deque
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AudioFormat(StrEnum):
    PCM_S16LE = "pcm_s16le"
    WEBM = "webm"


class SessionStatus(StrEnum):
    CONNECTED = "connected"
    READY = "ready"
    PROCESSING = "processing"
    CLOSED = "closed"


class AudioFrame(BaseModel):
    data: bytes
    sample_rate: int
    channels: int = 1
    duration_ms: int = 20


class VadResult(BaseModel):
    is_speech: bool
    energy: float
    speech_started: bool = False
    speech_ended: bool = False


class TranscriptionRequest(BaseModel):
    audio: bytes
    format: AudioFormat
    sample_rate: int
    channels: int
    language_hints: list[str]
    utterance_id: str


class TranscriptionResult(BaseModel):
    transcript: str
    alternatives: list[str] = Field(default_factory=list)
    confidence: float | None = None
    detected_language: str | None = None
    duration_ms: int = 0
    provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SynthesisRequest(BaseModel):
    text: str
    language: str
    output_format: AudioFormat
    sample_rate: int
    response_id: str
    voice_name: str | None = None
    speaking_rate: float = 1.0


class SynthesisResult(BaseModel):
    audio: bytes
    format: AudioFormat
    sample_rate: int
    channels: int = 1
    provider: str
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceSession(BaseModel):
    session_id: str
    conversation_id: str
    connected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    language: str
    input_format: AudioFormat
    input_sample_rate: int
    output_format: AudioFormat
    output_sample_rate: int
    status: SessionStatus = SessionStatus.CONNECTED
    speech_state: str = "idle"
    assistant_playing: bool = False
    current_utterance_id: str | None = None
    current_response_id: str | None = None
    transcript_count: int = 0
    interruption_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceSessionRuntime:
    """Non-serializable bounded runtime resources for one connection."""

    def __init__(self, session: VoiceSession, max_frames: int) -> None:
        self.session = session
        self.frames: deque[bytes] = deque(maxlen=max_frames)
        self.processing_lock = asyncio.Lock()
        self.lock = asyncio.Lock()
        self.playback_task: asyncio.Task[None] | None = None
        self.speech_ms = 0
        self.silence_ms = 0

    def clear_audio(self) -> None:
        self.frames.clear()
        self.speech_ms = 0
        self.silence_ms = 0
