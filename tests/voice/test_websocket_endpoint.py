"""Offline WebSocket protocol coverage."""

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from tests.voice.test_voice_core import FakeConversation

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.main import create_app
from restaurant_voice_ai.voice.service import VoiceService
from restaurant_voice_ai.voice.stt import FakeSpeechToTextProvider
from restaurant_voice_ai.voice.tts import FakeTextToSpeechProvider


async def no_database() -> AsyncIterator[None]:
    yield None


def test_websocket_handshake_turn_ping_and_clean_end() -> None:
    settings = Settings(_env_file=None, app_env="test", cors_origins=[])
    app = create_app(settings)
    app.dependency_overrides[get_db_session] = no_database
    app.state.voice_service_factory = lambda: VoiceService(
        settings,
        FakeSpeechToTextProvider(["Hello"]),
        FakeTextToSpeechProvider(),
        FakeConversation(),
    )
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/voice/ws") as websocket:
            websocket.send_bytes(b"\x00\x00")
            assert websocket.receive_json()["code"] == "session_not_started"
            websocket.send_json(
                {
                    "type": "session.start",
                    "protocol_version": "1.0",
                    "language": "en-IN",
                    "audio": {
                        "format": "pcm_s16le",
                        "sample_rate": 16000,
                        "channels": 1,
                        "frame_duration_ms": 20,
                    },
                }
            )
            ready = websocket.receive_json()
            assert ready["type"] == "session.ready"
            for index in range(10):
                websocket.send_bytes(b"\xff\x7f" * 320)
                if index == 0:
                    assert websocket.receive_json()["type"] == "speech.started"
            websocket.send_json({"type": "audio.commit"})
            assert websocket.receive_json()["type"] == "speech.ended"
            assert websocket.receive_json()["type"] == "transcript.final"
            assistant = websocket.receive_json()
            assert assistant["type"] == "assistant.text"
            assert assistant["turn_number"] == 1
            assert websocket.receive_json()["type"] == "assistant.audio.start"
            audio_chunks = 0
            while True:
                event = websocket.receive()
                if event.get("bytes") is not None:
                    audio_chunks += 1
                    continue
                end = event["text"]
                break
            import json

            assert audio_chunks >= 1
            assert json.loads(end) == {
                "type": "assistant.audio.end",
                "interrupted": False,
            }
            websocket.send_json({"type": "ping"})
            assert websocket.receive_json()["type"] == "pong"
            websocket.send_json({"type": "session.end"})
            assert websocket.receive_json()["type"] == "session.ended"
