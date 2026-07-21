import pytest

from restaurant_voice_ai.conversation.enums import NextAction, ResponseType
from restaurant_voice_ai.conversation.service import ConversationService
from tests.conversation.helpers import dependencies


@pytest.mark.asyncio
async def test_create_requests_first_missing_field() -> None:
    response = await ConversationService(dependencies()).process_message(
        "Book a table tomorrow at 7 PM for 4"
    )
    assert response.response_type is ResponseType.CLARIFICATION
    assert response.next_action is NextAction.ASK_CUSTOMER_NAME


@pytest.mark.asyncio
async def test_modify_requires_requested_change() -> None:
    response = await ConversationService(dependencies()).process_message(
        "Change reservation RSV-123456"
    )
    assert response.next_action is NextAction.ASK_REQUESTED_CHANGE
