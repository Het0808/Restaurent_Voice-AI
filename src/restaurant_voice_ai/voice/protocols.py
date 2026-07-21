"""Voice provider contracts."""

from typing import Protocol

from restaurant_voice_ai.voice.models import (
    AudioFrame,
    SynthesisRequest,
    SynthesisResult,
    TranscriptionRequest,
    TranscriptionResult,
    VadResult,
)


class VoiceActivityDetector(Protocol):
    def analyze(self, frame: AudioFrame) -> VadResult: ...


class SpeechToTextProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult: ...


class TextToSpeechProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult: ...
