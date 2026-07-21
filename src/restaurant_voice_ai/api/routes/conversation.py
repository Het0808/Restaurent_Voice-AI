"""Stateless conversation workflow endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.conversation.dependencies import build_conversation_dependencies
from restaurant_voice_ai.conversation.service import ConversationService
from restaurant_voice_ai.core.config import Settings, get_settings
from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.rag.dependencies import get_rag_service
from restaurant_voice_ai.rag.service import RagService
from restaurant_voice_ai.schemas.conversation import (
    ConversationMessageRequest,
    ConversationMessageResponse,
)

router = APIRouter(prefix="/conversation", tags=["Conversation"])


@router.post("/message", response_model=ConversationMessageResponse)
async def process_conversation_message(
    data: ConversationMessageRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    rag_service: Annotated[RagService, Depends(get_rag_service)],
) -> ConversationMessageResponse:
    service = ConversationService(build_conversation_dependencies(settings, session, rag_service))
    return await service.process_message(data.message, data.language, debug=data.debug)
