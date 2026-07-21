"""Voice transport coordination around the authoritative conversation service."""

import asyncio
import re
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.schemas.conversation import ConversationMessageResponse
from restaurant_voice_ai.voice.models import (
    AudioFormat,
    SynthesisRequest,
    SynthesisResult,
    TranscriptionRequest,
    VoiceSessionRuntime,
)
from restaurant_voice_ai.voice.protocols import SpeechToTextProvider, TextToSpeechProvider


class VoiceServiceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


class ConversationGateway(Protocol):
    async def process_message(
        self,
        message: str,
        language: str = "en",
        *,
        conversation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        debug: bool = False,
    ) -> ConversationMessageResponse: ...

    async def reset(self, conversation_id: str) -> None: ...


@dataclass(slots=True)
class VoiceTurnResult:
    transcript: str
    language: str
    response: ConversationMessageResponse
    synthesis: SynthesisResult | None
    tts_error: str | None = None


class VoiceService:
    def __init__(
        self,
        settings: Settings,
        stt: SpeechToTextProvider,
        tts: TextToSpeechProvider,
        conversation: ConversationGateway,
    ) -> None:
        self.settings = settings
        self.stt = stt
        self.tts = tts
        self.conversation = conversation

    def resolve_language(self, explicit: str | None, detected: str | None = None) -> str:
        language = explicit or detected or self.settings.voice_default_language
        if language not in self.settings.voice_supported_languages:
            raise VoiceServiceError("unsupported_language", "The language is not supported.")
        return language

    def validate_transcript(self, transcript: str) -> str:
        text = transcript.strip()
        if not text:
            raise VoiceServiceError("empty_transcript", "No speech was recognized.")
        if len(text) > self.settings.voice_max_transcript_chars:
            raise VoiceServiceError("transcript_too_long", "The transcript is too long.")
        controls = len(re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", text))
        if controls > max(2, len(text) // 20):
            raise VoiceServiceError("invalid_transcript", "The transcript contains invalid text.")
        return text

    async def process_completed_utterance(
        self, runtime: VoiceSessionRuntime, audio: bytes
    ) -> VoiceTurnResult:
        async with runtime.processing_lock:
            utterance_id = str(uuid.uuid4())
            session = runtime.session
            session.current_utterance_id = utterance_id
            request = TranscriptionRequest(
                audio=audio,
                format=session.input_format,
                sample_rate=session.input_sample_rate,
                channels=1,
                language_hints=[session.language],
                utterance_id=utterance_id,
            )
            try:
                transcription = await asyncio.wait_for(
                    self.stt.transcribe(request),
                    timeout=self.settings.voice_stt_timeout_seconds,
                )
            except TimeoutError as error:
                raise VoiceServiceError("stt_timeout", "Speech recognition timed out.") from error
            except Exception as error:
                raise VoiceServiceError(
                    "stt_unavailable", "Speech recognition is unavailable."
                ) from error
            transcript = self.validate_transcript(transcription.transcript)
            language = self.resolve_language(session.language, transcription.detected_language)
            stage6_language = language.split("-", 1)[0]
            try:
                response = await asyncio.wait_for(
                    self.conversation.process_message(
                        transcript,
                        stage6_language,
                        conversation_id=session.conversation_id,
                        metadata={
                            "channel": "voice",
                            "language": language,
                            "voice_session_id": session.session_id,
                        },
                    ),
                    timeout=self.settings.voice_conversation_timeout_seconds,
                )
            except Exception as error:
                raise VoiceServiceError(
                    "conversation_unavailable", "The request could not be processed."
                ) from error
            session.conversation_id = response.conversation_id
            session.transcript_count += 1
            response_id = str(uuid.uuid4())
            session.current_response_id = response_id
            try:
                synthesis = await asyncio.wait_for(
                    self.tts.synthesize(
                        SynthesisRequest(
                            text=response.response_text,
                            language=language,
                            output_format=AudioFormat.PCM_S16LE,
                            sample_rate=session.output_sample_rate,
                            response_id=response_id,
                        )
                    ),
                    timeout=self.settings.voice_tts_timeout_seconds,
                )
                return VoiceTurnResult(transcript, language, response, synthesis)
            except Exception:
                return VoiceTurnResult(
                    transcript, language, response, None, "Text-to-speech is unavailable."
                )

    async def reset_conversation(self, conversation_id: str) -> None:
        await self.conversation.reset(conversation_id)
