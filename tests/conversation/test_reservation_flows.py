import pytest

from restaurant_voice_ai.conversation.enums import Intent, ResponseType
from restaurant_voice_ai.conversation.service import ConversationService
from tests.conversation.helpers import FakeReservations, dependencies


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "intent", "call"),
    [
        (
            "Book 2030-04-01 at 19:00 for 4, my name is Asha and phone is 9876543210",
            Intent.CREATE_RESERVATION,
            "create",
        ),
        ("Cancel reservation RSV-123456", Intent.CANCEL_RESERVATION, "cancel"),
        (
            "Change reservation RSV-123456 to 2030-04-02 at 20:00",
            Intent.MODIFY_RESERVATION,
            "modify",
        ),
    ],
)
async def test_reservation_intent_end_to_end(message: str, intent: Intent, call: str) -> None:
    reservations = FakeReservations()
    response = await ConversationService(dependencies(reservations=reservations)).process_message(
        message
    )
    assert response.intent is intent
    assert response.response_type is ResponseType.CONFIRMATION
    assert reservations.calls == [call]


@pytest.mark.asyncio
async def test_availability_does_not_use_rag() -> None:
    reservations = FakeReservations(available=False)
    response = await ConversationService(dependencies(reservations=reservations)).process_message(
        "Availability 2030-04-01 at 19:00 for 4"
    )
    assert response.availability == {"available": False, "table_count": 0}
