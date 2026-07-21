"""Voice provider factories and process-local session manager."""

from functools import lru_cache

from restaurant_voice_ai.conversation.service import ConversationService
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.voice.protocols import SpeechToTextProvider, TextToSpeechProvider
from restaurant_voice_ai.voice.service import VoiceService
from restaurant_voice_ai.voice.session_manager import SessionManager
from restaurant_voice_ai.voice.stt import (
    FakeSpeechToTextProvider,
    GoogleCloudSpeechToTextProvider,
)
from restaurant_voice_ai.voice.tts import (
    FakeTextToSpeechProvider,
    GoogleCloudTextToSpeechProvider,
)


def build_voice_service(settings: Settings, conversation: ConversationService) -> VoiceService:
    if settings.voice_stt_provider == "fake":
        stt: SpeechToTextProvider = FakeSpeechToTextProvider()
    elif settings.voice_stt_provider == "google_cloud":
        stt = GoogleCloudSpeechToTextProvider(
            settings.google_cloud_project,
            settings.google_cloud_stt_model,
            settings.voice_stt_timeout_seconds,
        )
    else:
        raise ValueError("Gemini Live STT is an extension boundary and is not configured")
    if settings.voice_tts_provider == "fake":
        tts: TextToSpeechProvider = FakeTextToSpeechProvider()
    elif settings.voice_tts_provider == "google_cloud":
        tts = GoogleCloudTextToSpeechProvider(
            settings.google_cloud_tts_voice, settings.voice_tts_timeout_seconds
        )
    else:
        raise ValueError("Gemini Live TTS is an extension boundary and is not configured")
    return VoiceService(settings, stt, tts, conversation)


@lru_cache
def get_session_manager(max_sessions: int, idle: int, maximum: int) -> SessionManager:
    return SessionManager(max_sessions, idle, maximum)
