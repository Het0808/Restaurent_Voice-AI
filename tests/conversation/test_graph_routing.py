import pytest

from restaurant_voice_ai.conversation.service import ConversationService
from tests.conversation.helpers import FakeKnowledge, FakeReservations, dependencies


@pytest.mark.asyncio
async def test_each_intent_routes_to_only_its_dependency() -> None:
    knowledge = FakeKnowledge()
    reservations = FakeReservations()
    service = ConversationService(dependencies(knowledge=knowledge, reservations=reservations))
    await service.process_message("What is on the menu?")
    assert len(knowledge.calls) == 1
    assert reservations.calls == []
    await service.process_message("Is a table available 2030-04-01 at 19:00 for 4?")
    assert reservations.calls == ["availability"]


@pytest.mark.asyncio
async def test_graph_exposes_safe_trace_only_in_debug() -> None:
    service = ConversationService(dependencies())
    normal = await service.process_message("hello")
    debug = await service.process_message("hello", debug=True)
    assert normal.trace is None
    assert debug.trace
    assert all(set(item) == {"node", "status"} for item in debug.trace or [])
