"""Offline tests for Stage 7 audio, VAD, providers, sessions, and orchestration."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from restaurant_voice_ai.conversation.enums import Intent, ResponseType
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.schemas.conversation import ConversationMessageResponse
from restaurant_voice_ai.voice.audio import (
    UtteranceBuffer,
    VoiceProtocolError,
    chunk_audio,
    validate_audio_frame,
)
from restaurant_voice_ai.voice.models import (
    AudioFormat,
    AudioFrame,
    VoiceSession,
    VoiceSessionRuntime,
)
from restaurant_voice_ai.voice.service import VoiceService, VoiceServiceError
from restaurant_voice_ai.voice.session_manager import SessionManager
from restaurant_voice_ai.voice.stt import FakeSpeechToTextProvider
from restaurant_voice_ai.voice.tts import FakeTextToSpeechProvider
from restaurant_voice_ai.voice.vad import EnergyVoiceActivityDetector


class FakeConversation:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def process_message(
        self, message: str, language: str, **kwargs: Any
    ) -> ConversationMessageResponse:
        self.calls.append({"message": message, "language": language, **kwargs})
        return ConversationMessageResponse(
            conversation_id=str(kwargs["conversation_id"]),
            turn_number=len(self.calls),
            intent=Intent.GREETING,
            response_type=ResponseType.ANSWER,
            response_text="Hello",
        )

    async def reset(self, conversation_id: str) -> None:
        return None


def runtime() -> VoiceSessionRuntime:
    return VoiceSessionRuntime(
        VoiceSession(
            session_id="session-123",
            conversation_id="conversation-123",
            language="en-IN",
            input_format=AudioFormat.PCM_S16LE,
            input_sample_rate=16000,
            output_format=AudioFormat.PCM_S16LE,
            output_sample_rate=24000,
        ),
        100,
    )


def test_audio_validation_buffer_and_chunking() -> None:
    validate_audio_frame(b"\x00\x00", format=AudioFormat.PCM_S16LE, max_bytes=4)
    with pytest.raises(VoiceProtocolError):
        validate_audio_frame(b"", format=AudioFormat.PCM_S16LE, max_bytes=4)
    with pytest.raises(VoiceProtocolError):
        validate_audio_frame(b"\x00", format=AudioFormat.PCM_S16LE, max_bytes=4)
    with pytest.raises(VoiceProtocolError):
        validate_audio_frame(b"\x00" * 6, format=AudioFormat.PCM_S16LE, max_bytes=4)
    buffer = UtteranceBuffer(8, 1)
    buffer.add_pre_speech(b"\x00\x00")
    buffer.start_speech()
    buffer.append(b"\x01\x00", 20, speech=True)
    assert buffer.byte_length == 4
    assert buffer.sample_count == 2
    assert buffer.snapshot() == b"\x00\x00\x01\x00"
    assert chunk_audio(b"12345", 2) == [b"12", b"34", b"5"]


def test_energy_vad_detects_silence_and_speech() -> None:
    vad = EnergyVoiceActivityDetector(500)
    silence = vad.analyze(AudioFrame(data=b"\x00\x00" * 160, sample_rate=16000))
    speech = vad.analyze(AudioFrame(data=b"\xff\x7f" * 160, sample_rate=16000))
    ended = vad.analyze(AudioFrame(data=b"\x00\x00" * 160, sample_rate=16000))
    assert not silence.is_speech
    assert speech.is_speech and speech.speech_started
    assert ended.speech_ended


@pytest.mark.asyncio
async def test_session_manager_lifecycle_and_limits() -> None:
    manager = SessionManager(1, 10, 20)
    item = runtime()
    await manager.register(item)
    assert await manager.get("session-123") is item
    with pytest.raises(ValueError):
        await manager.register(runtime())
    item.session.last_activity_at = datetime.now(UTC) - timedelta(seconds=11)
    assert await manager.expired_reason("session-123") == "idle_timeout"
    await manager.remove("session-123")
    assert await manager.active_count() == 0
    assert not item.frames


@pytest.mark.asyncio
async def test_voice_service_preserves_identity_metadata_and_returns_pcm() -> None:
    settings = Settings(_env_file=None, app_env="test", cors_origins=[])
    conversation = FakeConversation()
    service = VoiceService(
        settings,
        FakeSpeechToTextProvider(["Hello"]),
        FakeTextToSpeechProvider(),
        conversation,
    )
    result = await service.process_completed_utterance(runtime(), b"\x01\x00" * 320)
    assert result.transcript == "Hello"
    assert result.synthesis and result.synthesis.audio
    assert conversation.calls[0]["conversation_id"] == "conversation-123"
    assert conversation.calls[0]["metadata"]["channel"] == "voice"


def test_language_and_transcript_validation() -> None:
    settings = Settings(_env_file=None, app_env="test", cors_origins=[])
    service = VoiceService(
        settings,
        FakeSpeechToTextProvider(),
        FakeTextToSpeechProvider(),
        FakeConversation(),
    )
    assert service.resolve_language("gu-IN") == "gu-IN"
    with pytest.raises(VoiceServiceError):
        service.resolve_language("fr-FR")
    with pytest.raises(VoiceServiceError):
        service.validate_transcript("   ")
