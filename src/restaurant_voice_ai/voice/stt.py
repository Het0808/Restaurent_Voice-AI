"""Offline and optional Google Cloud speech-to-text providers."""

import asyncio
import importlib
from collections import deque
from typing import Any

from restaurant_voice_ai.voice.models import TranscriptionRequest, TranscriptionResult


class SpeechProviderError(RuntimeError):
    pass


class FakeSpeechToTextProvider:
    provider_name = "fake"

    def __init__(self, transcripts: list[str] | None = None) -> None:
        self.transcripts = deque(transcripts or ["Hello"])

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        if not self.transcripts:
            raise SpeechProviderError("No fake transcript is queued")
        text = self.transcripts.popleft()
        return TranscriptionResult(
            transcript=text,
            detected_language=request.language_hints[0] if request.language_hints else None,
            duration_ms=round(len(request.audio) / 2 / request.sample_rate * 1000),
            provider=self.provider_name,
        )


class GoogleCloudSpeechToTextProvider:
    provider_name = "google_cloud"

    def __init__(self, project: str | None, model: str, timeout: float) -> None:
        self.project = project
        self.model = model
        self.timeout = timeout
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                speech_v1 = importlib.import_module("google.cloud.speech_v1")
            except ImportError as error:
                raise SpeechProviderError("Google Cloud Speech is not installed") from error
            self._client = speech_v1.SpeechClient()
        return self._client

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        try:
            speech_v1 = importlib.import_module("google.cloud.speech_v1")
        except ImportError as error:
            raise SpeechProviderError("Google Cloud Speech is not installed") from error
        config = speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=request.sample_rate,
            audio_channel_count=request.channels,
            language_code=request.language_hints[0],
            alternative_language_codes=request.language_hints[1:],
            model=self.model,
        )
        try:
            response = await asyncio.to_thread(
                self._get_client().recognize,
                config=config,
                audio=speech_v1.RecognitionAudio(content=request.audio),
                timeout=self.timeout,
            )
            transcript = " ".join(
                result.alternatives[0].transcript
                for result in response.results
                if result.alternatives
            ).strip()
        except Exception as error:
            raise SpeechProviderError("Google Cloud transcription failed") from error
        return TranscriptionResult(transcript=transcript, provider=self.provider_name)
