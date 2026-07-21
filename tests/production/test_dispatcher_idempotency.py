"""Cross-dispatcher mutation idempotency behavior."""

import pytest
from tests.conversation.helpers import FakeKnowledge, FakeReservations

from restaurant_voice_ai.conversation.enums import ConfirmationStatus
from restaurant_voice_ai.conversation.tools.dispatcher import (
    ConversationToolDispatcher,
    ToolExecutionContext,
)
from restaurant_voice_ai.persistence.redis.idempotency import InMemoryIdempotencyStore


@pytest.mark.asyncio
async def test_duplicate_mutation_replays_across_dispatchers() -> None:
    store = InMemoryIdempotencyStore()
    reservations = FakeReservations()
    first = ConversationToolDispatcher(FakeKnowledge(), reservations, 20, store)
    second = ConversationToolDispatcher(FakeKnowledge(), reservations, 20, store)
    arguments = {
        "customer_name": "Het Patel",
        "customer_phone": "9999999999",
        "reservation_date": "2030-01-01",
        "reservation_time": "19:00",
        "party_size": 4,
    }
    context = ToolExecutionContext("shared-conversation", ConfirmationStatus.CONFIRMED, 0, 3)

    created = await first.execute("create_reservation", arguments, context)
    replayed = await second.execute("create_reservation", arguments, context)

    assert created.success and replayed.success
    assert replayed.status == "replayed"
    assert reservations.calls == ["create"]
