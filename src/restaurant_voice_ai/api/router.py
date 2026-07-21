"""Versioned API router."""

from fastapi import APIRouter

from restaurant_voice_ai.api.routes.conversation import router as conversation_router
from restaurant_voice_ai.api.routes.health import router as health_router
from restaurant_voice_ai.api.routes.knowledge import router as knowledge_router
from restaurant_voice_ai.api.routes.reservations import router as reservations_router
from restaurant_voice_ai.api.routes.tables import router as tables_router
from restaurant_voice_ai.api.routes.voice import router as voice_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(conversation_router)
api_router.include_router(tables_router)
api_router.include_router(reservations_router)
api_router.include_router(knowledge_router)
api_router.include_router(voice_router)
