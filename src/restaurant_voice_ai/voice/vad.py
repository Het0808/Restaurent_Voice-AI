"""Deterministic energy-based voice activity detection."""

import math
import sys
from array import array

from restaurant_voice_ai.voice.models import AudioFrame, VadResult


class EnergyVoiceActivityDetector:
    def __init__(self, threshold: int) -> None:
        self.threshold = threshold
        self._speaking = False

    def analyze(self, frame: AudioFrame) -> VadResult:
        samples = array("h")
        samples.frombytes(frame.data)
        if sys.byteorder != "little":
            samples.byteswap()
        energy = (
            math.sqrt(sum(sample * sample for sample in samples) / len(samples)) if samples else 0.0
        )
        speech = energy >= self.threshold
        started = speech and not self._speaking
        ended = not speech and self._speaking
        self._speaking = speech
        return VadResult(
            is_speech=speech,
            energy=energy,
            speech_started=started,
            speech_ended=ended,
        )

    def reset(self) -> None:
        self._speaking = False
