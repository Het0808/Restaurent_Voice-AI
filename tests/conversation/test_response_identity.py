"""Conversation identity and turn-number response guarantees."""

import uuid

import pytest

from restaurant_voice_ai.conversation.service import ConversationService
from tests.conversation.helpers import dependencies


@pytest.mark.asyncio
async def test_omitted_conversation_id_generates_uuid_on_initial_turn() -> None:
    response = await ConversationService(dependencies()).process_message("hello")

    assert str(uuid.UUID(response.conversation_id)) == response.conversation_id
    assert response.turn_number == 1


@pytest.mark.asyncio
async def test_supplied_conversation_id_is_preserved_and_turn_increments() -> None:
    service = ConversationService(dependencies())
    conversation_id = "test-conversation-123"

    first = await service.process_message("hello", conversation_id=conversation_id)
    second = await service.process_message("hello", conversation_id=conversation_id)

    assert first.conversation_id == conversation_id
    assert second.conversation_id == conversation_id
    assert (first.turn_number, second.turn_number) == (1, 2)


@pytest.mark.asyncio
async def test_response_fallback_never_omits_identity_fields() -> None:
    response = await ConversationService(dependencies()).process_message("unsupported gibberish")

    assert response.conversation_id
    assert response.turn_number >= 1
