"""Offline end-to-end verification of the Stage 7 WebSocket voice pipeline."""

from collections.abc import AsyncIterator
from typing import Any

from fastapi.testclient import TestClient

from restaurant_voice_ai.conversation.models import (
    ConversationDependencies,
    ConversationEntities,
)
from restaurant_voice_ai.conversation.nodes.classify_intent import RuleBasedIntentClassifier
from restaurant_voice_ai.conversation.nodes.extract_entities import RuleBasedEntityExtractor
from restaurant_voice_ai.conversation.service import ConversationService
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.main import create_app
from restaurant_voice_ai.voice.service import VoiceService
from restaurant_voice_ai.voice.stt import FakeSpeechToTextProvider
from restaurant_voice_ai.voice.tts import FakeTextToSpeechProvider


class OfflineKnowledge:
    async def retrieve(self, query: str) -> dict[str, Any]:
        return {"evidence_found": False, "citations": [], "retrieved_context": ""}


class TrackingReservations:
    def __init__(self) -> None:
        self.creations = 0

    async def check_availability(self, entities: ConversationEntities) -> dict[str, Any]:
        return {"available": True, "table_count": 1}

    async def create(self, entities: ConversationEntities, language: str) -> dict[str, Any]:
        self.creations += 1
        return {"confirmation_code": "RSV-OFFLINE1", "status": "confirmed"}

    async def modify(self, entities: ConversationEntities) -> dict[str, Any]:
        raise AssertionError("Unexpected modification")

    async def cancel(self, reservation_id: str) -> dict[str, Any]:
        raise AssertionError("Unexpected cancellation")


async def no_database() -> AsyncIterator[None]:
    yield None


def main() -> None:
    transcripts = [
        "Book a table for four tomorrow at 7 PM",
        "Het Patel",
        "9999999999",
        "Yes, confirm it",
    ]
    settings = Settings(
        _env_file=None,
        app_env="test",
        cors_origins=[],
        conversation_mode="rules",
        conversation_intent_provider="rules",
        conversation_entity_provider="rules",
        conversation_response_provider="rules",
    )
    reservations = TrackingReservations()
    conversation = ConversationService(
        ConversationDependencies(
            classifier=RuleBasedIntentClassifier(),
            extractor=RuleBasedEntityExtractor("Asia/Kolkata"),
            knowledge=OfflineKnowledge(),
            reservations=reservations,
            settings=settings,
        )
    )
    service = VoiceService(
        settings,
        FakeSpeechToTextProvider(transcripts),
        FakeTextToSpeechProvider(),
        conversation,
    )
    app = create_app(settings)
    app.dependency_overrides[get_db_session] = no_database
    app.state.voice_service_factory = lambda: service
    turns: list[int] = []
    mutation_counts: list[int] = []
    final_transcripts = 0
    assistant_texts = 0
    audio_starts = 0
    audio_ends = 0
    binary_chunks = 0

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/voice/ws") as websocket:
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
            conversation_id = ready["conversation_id"]
            for expected_turn in range(1, 5):
                for index in range(10):
                    websocket.send_bytes(b"\xff\x7f" * 320)
                    if index == 0:
                        assert websocket.receive_json()["type"] == "speech.started"
                websocket.send_json({"type": "audio.commit"})
                assert websocket.receive_json()["type"] == "speech.ended"
                while True:
                    event = websocket.receive()
                    if event.get("bytes") is not None:
                        binary_chunks += 1
                        continue
                    data = event.get("text")
                    assert data is not None
                    import json

                    payload = json.loads(data)
                    if payload["type"] == "transcript.final":
                        final_transcripts += 1
                    elif payload["type"] == "assistant.text":
                        assistant_texts += 1
                        turns.append(payload["turn_number"])
                    elif payload["type"] == "assistant.audio.start":
                        audio_starts += 1
                    elif payload["type"] == "assistant.audio.end":
                        audio_ends += 1
                        break
                mutation_counts.append(reservations.creations)
                assert turns[-1] == expected_turn
            websocket.send_json({"type": "session.end"})
            assert websocket.receive_json()["type"] == "session.ended"

    assert conversation_id
    assert turns == [1, 2, 3, 4]
    assert final_transcripts == assistant_texts == audio_starts == audio_ends == 4
    assert binary_chunks >= 4
    assert mutation_counts[:3] == [0, 0, 0]
    assert mutation_counts[3] == reservations.creations == 1
    print("Offline voice WebSocket verification passed.")


if __name__ == "__main__":
    main()
