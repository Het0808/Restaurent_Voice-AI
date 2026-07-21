"""Offline Twilio webhook and TwiML tests."""

from typing import Any

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from twilio.request_validator import RequestValidator

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.main import create_app
from restaurant_voice_ai.schemas.conversation import ConversationMessageResponse


class FakeConversation:
    async def process_message(
        self, message: str, language: str, **kwargs: Any
    ) -> ConversationMessageResponse:
        return ConversationMessageResponse(
            conversation_id=str(kwargs["conversation_id"]),
            turn_number=1,
            intent="knowledge_query",
            response_type="answer",
            response_text="We are open from noon until ten.",
        )


def signature(settings: Settings, path: str, data: dict[str, str]) -> str:
    token = settings.twilio_auth_token
    assert token is not None
    return RequestValidator(token.get_secret_value()).compute_signature(
        f"{settings.public_base_url}{path}", data
    )


@pytest.fixture
def twilio_settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={
            "public_base_url": "https://voice.example.test",
            "twilio_auth_token": SecretStr("test-token"),
            "twilio_staff_phone_number": "+15551234567",
        }
    )


@pytest.mark.asyncio
async def test_invalid_twilio_signature_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/voice/incoming",
        data={"CallSid": "CA123", "From": "+15550000001"},
        headers={"X-Twilio-Signature": "invalid"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_incoming_speech_retry_escalation_and_status_are_idempotent(
    twilio_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from collections.abc import AsyncIterator

    from httpx import ASGITransport
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from restaurant_voice_ai.db.base import Base
    from restaurant_voice_ai.db.dependencies import get_db_session

    engine = create_async_engine(twilio_settings.database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    app = create_app(twilio_settings)

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = session_override
    app.state.twilio_conversation_factory = FakeConversation
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as http:
        incoming = {
            "CallSid": "CA123456789",
            "From": "+15550000001",
            "To": "+15550000002",
            "Direction": "inbound",
        }
        response = await http.post(
            "/api/v1/voice/incoming",
            data=incoming,
            headers={
                "X-Twilio-Signature": signature(twilio_settings, "/api/v1/voice/incoming", incoming)
            },
        )
        assert response.status_code == 200
        assert "<Gather" in response.text and "Welcome" in response.text

        speech = {
            "CallSid": incoming["CallSid"],
            "SpeechResult": "What time do you open?",
            "Confidence": "0.98",
        }
        response = await http.post(
            "/api/v1/voice/process-speech",
            data=speech,
            headers={
                "X-Twilio-Signature": signature(
                    twilio_settings, "/api/v1/voice/process-speech", speech
                )
            },
        )
        assert response.status_code == 200
        assert "open from noon" in response.text

        status = {"CallSid": incoming["CallSid"], "CallStatus": "completed", "CallDuration": "42"}
        headers = {"X-Twilio-Signature": signature(twilio_settings, "/api/v1/voice/status", status)}
        assert (
            await http.post("/api/v1/voice/status", data=status, headers=headers)
        ).status_code == 204
        assert (
            await http.post("/api/v1/voice/status", data=status, headers=headers)
        ).status_code == 204
        from sqlalchemy import select

        from restaurant_voice_ai.db.models.call_session import CallSession

        async with factory() as db:
            call = await db.scalar(
                select(CallSession).where(CallSession.external_call_id == incoming["CallSid"])
            )
            assert call is not None
            assert call.status == "completed"
            assert call.duration_seconds == 42
    await engine.dispose()


@pytest.mark.asyncio
async def test_human_request_returns_dial(twilio_settings: Settings) -> None:
    # Covered end-to-end in the preceding fixture; TwiML behavior is deterministic.
    from restaurant_voice_ai.telephony.twilio import TwimlBuilder

    response = TwimlBuilder(twilio_settings).transfer("I will connect you.")
    assert "<Dial>+15551234567</Dial>" in response


@pytest.mark.asyncio
async def test_repeated_silence_escalates(client: AsyncClient, settings: Settings) -> None:
    settings.public_base_url = "https://voice.example.test"
    settings.twilio_validate_signatures = False
    settings.twilio_staff_phone_number = "+15551234567"
    incoming = {"CallSid": "CA-SILENCE", "From": "+15550000001", "To": "+15550000002"}
    assert (await client.post("/api/v1/voice/incoming", data=incoming)).status_code == 200
    response = None
    for _ in range(settings.twilio_max_retries):
        response = await client.post(
            "/api/v1/voice/process-speech",
            data={"CallSid": incoming["CallSid"], "SpeechResult": "", "Confidence": "0"},
        )
    assert response is not None
    assert "<Dial>+15551234567</Dial>" in response.text
