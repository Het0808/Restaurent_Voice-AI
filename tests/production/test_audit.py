"""SQLite-backed safe conversation audit persistence test."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from restaurant_voice_ai.conversation.enums import Intent, ResponseType
from restaurant_voice_ai.db.base import Base
from restaurant_voice_ai.db.models.conversation_audit import (
    ConversationTurnAudit,
    ToolAuditEvent,
)
from restaurant_voice_ai.persistence.conversation_history.service import SqlConversationAudit
from restaurant_voice_ai.schemas.conversation import ConversationMessageResponse


@pytest.mark.asyncio
async def test_audit_masks_phone_and_stores_no_audio(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'audit.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        audit = SqlConversationAudit(session)
        response = ConversationMessageResponse(
            conversation_id="audit-conversation",
            turn_number=1,
            intent=Intent.CREATE_RESERVATION,
            response_type=ResponseType.CLARIFICATION,
            response_text="What phone number should I use?",
            entities={"customer_phone": "9999999999"},
        )
        await audit.record_turn(
            "My number is 9999999999",
            response,
            {"channel": "voice", "raw_audio": b"must-not-persist"},
            12.5,
        )
        saved = await session.scalar(select(ConversationTurnAudit))
        assert saved is not None
        assert "9999999999" not in saved.user_message_masked
        assert "audio" not in saved.user_message_masked
        tool = await session.scalar(select(ToolAuditEvent))
        assert tool is not None
        assert "9999999999" not in str(tool.safe_arguments)
    await engine.dispose()
