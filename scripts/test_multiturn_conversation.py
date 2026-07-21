"""Offline smoke test for the Stage 6 multi-turn reservation flow."""

import asyncio
from typing import Any

from restaurant_voice_ai.conversation.enums import ConfirmationStatus
from restaurant_voice_ai.conversation.models import (
    ConversationDependencies,
    ConversationEntities,
)
from restaurant_voice_ai.conversation.nodes.classify_intent import RuleBasedIntentClassifier
from restaurant_voice_ai.conversation.nodes.extract_entities import RuleBasedEntityExtractor
from restaurant_voice_ai.conversation.service import ConversationService
from restaurant_voice_ai.core.config import Settings


class FakeKnowledge:
    """Offline knowledge gateway; this scenario must not invoke it."""

    async def retrieve(self, query: str) -> dict[str, Any]:
        raise AssertionError("Unexpected knowledge retrieval")


class TrackingReservations:
    """Offline reservation gateway that records mutation timing."""

    def __init__(self) -> None:
        self.create_calls = 0

    async def check_availability(self, entities: ConversationEntities) -> dict[str, Any]:
        return {"available": True, "table_count": 1}

    async def create(self, entities: ConversationEntities, language: str) -> dict[str, Any]:
        self.create_calls += 1
        return {"confirmation_code": "RSV-OFFLINE1", "status": "confirmed"}

    async def modify(self, entities: ConversationEntities) -> dict[str, Any]:
        raise AssertionError("Unexpected modification")

    async def cancel(self, reservation_id: str) -> dict[str, Any]:
        raise AssertionError("Unexpected cancellation")


async def main() -> None:
    reservations = TrackingReservations()
    settings = Settings(
        _env_file=None,
        app_env="test",
        cors_origins=[],
        conversation_mode="rules",
        conversation_intent_provider="rules",
        conversation_entity_provider="rules",
        conversation_response_provider="rules",
    )
    configured = ConversationDependencies(
        classifier=RuleBasedIntentClassifier(),
        extractor=RuleBasedEntityExtractor("Asia/Kolkata"),
        knowledge=FakeKnowledge(),
        reservations=reservations,
        settings=settings,
    )
    service = ConversationService(configured)
    messages = (
        "Book a table for four tomorrow at 7 PM",
        "Het Patel",
        "9999999999",
        "Yes, confirm it",
    )
    conversation_id: str | None = None
    returned_ids: list[str] = []
    turn_numbers: list[int] = []
    mutation_counts: list[int] = []

    for message in messages:
        response = await service.process_message(
            message,
            conversation_id=conversation_id,
        )
        conversation_id = response.conversation_id
        returned_ids.append(response.conversation_id)
        turn_numbers.append(response.turn_number)
        mutation_counts.append(reservations.create_calls)
        pending = response.pending_operation or {}
        confirmation_status = pending.get(
            "confirmation_status",
            ConfirmationStatus.COMPLETED.value
            if response.reservation
            else ConfirmationStatus.NOT_REQUIRED.value,
        )
        print(
            f"turn={response.turn_number} conversation_id={response.conversation_id}\n"
            f"response={response.response_text}\n"
            f"next_action={response.next_action.value} "
            f"confirmation_status={confirmation_status} "
            f"mutation_executed={reservations.create_calls > 0}\n"
        )

    assert len(set(returned_ids)) == 1, "Conversation ID changed between turns"
    assert turn_numbers == [1, 2, 3, 4], "Turn numbers were not monotonic"
    assert mutation_counts[:3] == [0, 0, 0], "Mutation ran before confirmation"
    assert mutation_counts[3] == 1, "Reservation creation did not run exactly once"
    print("Offline multi-turn verification passed.")


if __name__ == "__main__":
    asyncio.run(main())
