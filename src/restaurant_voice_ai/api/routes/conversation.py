"""Stateless conversation workflow endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.auth.dependencies import require_permission
from restaurant_voice_ai.auth.models import AuthIdentity, Permission
from restaurant_voice_ai.conversation.dependencies import build_conversation_dependencies
from restaurant_voice_ai.conversation.service import ConversationService
from restaurant_voice_ai.core.config import Settings, get_settings
from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.persistence.redis.factory import (
    get_conversation_memory,
    get_idempotency_store,
)
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
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    rag_service: Annotated[RagService, Depends(get_rag_service)],
    _: Annotated[AuthIdentity, Depends(require_permission(Permission.SEND_TEXT_MESSAGE))],
) -> ConversationMessageResponse:
    service = ConversationService(
        build_conversation_dependencies(
            settings,
            session,
            rag_service,
            get_conversation_memory(request),
            get_idempotency_store(request),
        )
    )
    return await service.process_message(
        data.message,
        data.language,
        conversation_id=data.conversation_id,
        metadata=data.metadata,
        debug=data.debug,
    )
