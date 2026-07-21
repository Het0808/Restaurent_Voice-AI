"""Offline fakes for conversation tests."""

from typing import Any

from restaurant_voice_ai.conversation.models import ConversationDependencies, ConversationEntities
from restaurant_voice_ai.conversation.nodes.classify_intent import RuleBasedIntentClassifier
from restaurant_voice_ai.conversation.nodes.extract_entities import RuleBasedEntityExtractor


class FakeKnowledge:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[str] = []

    async def retrieve(self, query: str) -> dict[str, Any]:
        self.calls.append(query)
        if self.fail:
            raise RuntimeError("offline")
        return {
            "retrieved_context": (
                "[Source: menu.md | Section: Paneer Tikka]\nPaneer tikka contains dairy yogurt."
            ),
            "retrieval_results": [
                {
                    "text": "Paneer tikka contains dairy yogurt.",
                    "source": "menu.md",
                    "source_filename": "menu.md",
                    "chunk_id": "menu-paneer",
                    "section": "Paneer Tikka",
                    "score": 0.9,
                    "metadata": {"extension": ".md"},
                }
            ],
            "citations": [
                {
                    "source": "menu.md",
                    "source_filename": "menu.md",
                    "chunk_id": "menu-paneer",
                    "section": "Paneer Tikka",
                    "score": 0.9,
                    "metadata": {"extension": ".md"},
                }
            ],
            "evidence_found": True,
        }


class FakeReservations:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.calls: list[str] = []

    async def check_availability(self, entities: ConversationEntities) -> dict[str, Any]:
        self.calls.append("availability")
        return {"available": self.available, "table_count": int(self.available)}

    async def create(self, entities: ConversationEntities, language: str) -> dict[str, Any]:
        self.calls.append("create")
        return {"confirmation_code": "RSV-ABC12345", "status": "confirmed"}

    async def cancel(self, reservation_id: str) -> dict[str, Any]:
        self.calls.append("cancel")
        return {"confirmation_code": reservation_id, "status": "cancelled"}

    async def modify(self, entities: ConversationEntities) -> dict[str, Any]:
        self.calls.append("modify")
        return {"confirmation_code": entities.reservation_id, "status": "confirmed"}


def dependencies(
    *, knowledge: FakeKnowledge | None = None, reservations: FakeReservations | None = None
) -> ConversationDependencies:
    return ConversationDependencies(
        classifier=RuleBasedIntentClassifier(),
        extractor=RuleBasedEntityExtractor("Asia/Kolkata"),
        knowledge=knowledge or FakeKnowledge(),
        reservations=reservations or FakeReservations(),
    )
