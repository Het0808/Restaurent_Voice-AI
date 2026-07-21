"""Offline and optional Google Cloud text-to-speech providers."""

import asyncio
import importlib
import math
import struct
from typing import Any

from restaurant_voice_ai.voice.models import SynthesisRequest, SynthesisResult


class TextToSpeechProviderError(RuntimeError):
    pass


class FakeTextToSpeechProvider:
    provider_name = "fake"

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        sample_count = max(request.sample_rate // 10, 1)
        audio = b"".join(
            struct.pack("<h", int(1200 * math.sin(2 * math.pi * 440 * i / request.sample_rate)))
            for i in range(sample_count)
        )
        return SynthesisResult(
            audio=audio,
            format=request.output_format,
            sample_rate=request.sample_rate,
            provider=self.provider_name,
            duration_ms=100,
        )


class GoogleCloudTextToSpeechProvider:
    provider_name = "google_cloud"

    def __init__(self, voice_name: str | None, timeout: float) -> None:
        self.voice_name = voice_name
        self.timeout = timeout
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                texttospeech = importlib.import_module("google.cloud.texttospeech")
            except ImportError as error:
                raise TextToSpeechProviderError(
                    "Google Cloud Text-to-Speech is not installed"
                ) from error
            self._client = texttospeech.TextToSpeechClient()
        return self._client

    async def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        try:
            texttospeech = importlib.import_module("google.cloud.texttospeech")

            response = await asyncio.to_thread(
                self._get_client().synthesize_speech,
                input=texttospeech.SynthesisInput(text=request.text),
                voice=texttospeech.VoiceSelectionParams(
                    language_code=request.language,
                    name=request.voice_name or self.voice_name,
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                    sample_rate_hertz=request.sample_rate,
                    speaking_rate=request.speaking_rate,
                ),
                timeout=self.timeout,
            )
            wav = bytes(response.audio_content)
            if len(wav) < 44 or wav[:4] != b"RIFF":
                raise ValueError("Expected a LINEAR16 WAV response")
            audio = wav[44:]
        except Exception as error:
            raise TextToSpeechProviderError("Google Cloud synthesis failed") from error
        return SynthesisResult(
            audio=audio,
            format=request.output_format,
            sample_rate=request.sample_rate,
            provider=self.provider_name,
        )
