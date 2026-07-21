"""Bounded PCM validation, buffering, and chunking."""

from collections import deque

from restaurant_voice_ai.voice.models import AudioFormat


class VoiceProtocolError(ValueError):
    def __init__(self, code: str, message: str, *, recoverable: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.recoverable = recoverable


def validate_audio_frame(data: bytes, *, format: AudioFormat, max_bytes: int) -> None:
    if not data:
        raise VoiceProtocolError("empty_audio_frame", "Audio frames cannot be empty.")
    if len(data) > max_bytes:
        raise VoiceProtocolError("audio_frame_too_large", "The audio frame is too large.")
    if format is AudioFormat.PCM_S16LE and len(data) % 2:
        raise VoiceProtocolError("misaligned_audio", "PCM audio must contain complete samples.")


class UtteranceBuffer:
    def __init__(self, max_bytes: int, pre_speech_frames: int) -> None:
        self.max_bytes = max_bytes
        self._frames: list[bytes] = []
        self._pre: deque[bytes] = deque(maxlen=pre_speech_frames)
        self.speech_ms = 0
        self.silence_ms = 0

    def add_pre_speech(self, frame: bytes) -> None:
        self._pre.append(bytes(frame))

    def start_speech(self) -> None:
        if not self._frames:
            self._frames.extend(self._pre)
        self._pre.clear()

    def append(self, frame: bytes, duration_ms: int, *, speech: bool) -> None:
        if self.byte_length + len(frame) > self.max_bytes:
            raise VoiceProtocolError("utterance_too_long", "The utterance is too long.")
        self._frames.append(bytes(frame))
        if speech:
            self.speech_ms += duration_ms
            self.silence_ms = 0
        else:
            self.silence_ms += duration_ms

    @property
    def byte_length(self) -> int:
        return sum(map(len, self._frames))

    @property
    def sample_count(self) -> int:
        return self.byte_length // 2

    def duration_ms(self, sample_rate: int) -> int:
        return round(self.sample_count * 1000 / sample_rate)

    def snapshot(self) -> bytes:
        return b"".join(self._frames)

    def reset(self) -> None:
        self._frames.clear()
        self._pre.clear()
        self.speech_ms = 0
        self.silence_ms = 0


def chunk_audio(audio: bytes, size: int) -> list[bytes]:
    return [audio[index : index + size] for index in range(0, len(audio), size)]
