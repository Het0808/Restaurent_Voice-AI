import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_conversation_message_api_hides_trace_by_default(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/conversation/message", json={"message": "hello", "language": "en"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "greeting"
    assert body["trace"] is None


@pytest.mark.asyncio
async def test_conversation_message_api_validates_language(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/conversation/message", json={"message": "hello", "language": "fr"}
    )
    assert response.status_code == 422
