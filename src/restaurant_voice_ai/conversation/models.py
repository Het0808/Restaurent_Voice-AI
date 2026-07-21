"""Conversation contracts and dependency abstractions."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, Field

from restaurant_voice_ai.conversation.enums import Intent

if TYPE_CHECKING:
    from restaurant_voice_ai.conversation.llm.base import ConversationModel
    from restaurant_voice_ai.conversation.memory.base import ConversationMemory
    from restaurant_voice_ai.conversation.tools.dispatcher import ConversationToolDispatcher
    from restaurant_voice_ai.core.config import Settings
    from restaurant_voice_ai.persistence.conversation_history.service import ConversationAudit
    from restaurant_voice_ai.persistence.redis.idempotency import IdempotencyStore


class ConversationEntities(BaseModel):
    customer_name: str | None = None
    customer_phone: str | None = None
    reservation_date: str | None = None
    reservation_time: str | None = None
    party_size: int | None = Field(default=None, ge=1)
    reservation_id: str | None = None
    requested_date: str | None = None
    requested_time: str | None = None
    requested_party_size: int | None = Field(default=None, ge=1)


class Classification(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0, le=1)


class IntentClassifier(Protocol):
    async def classify(self, message: str, language: str) -> Classification: ...


class EntityExtractor(Protocol):
    async def extract(
        self, message: str, intent: Intent, language: str
    ) -> ConversationEntities: ...


class KnowledgeGateway(Protocol):
    async def retrieve(self, query: str) -> dict[str, Any]: ...


class ReservationGateway(Protocol):
    async def check_availability(self, entities: ConversationEntities) -> dict[str, Any]: ...

    async def create(self, entities: ConversationEntities, language: str) -> dict[str, Any]: ...

    async def cancel(self, reservation_id: str) -> dict[str, Any]: ...

    async def modify(self, entities: ConversationEntities) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ConversationDependencies:
    classifier: IntentClassifier
    extractor: EntityExtractor
    knowledge: KnowledgeGateway
    reservations: ReservationGateway
    settings: "Settings | None" = None
    memory: "ConversationMemory | None" = None
    conversation_model: "ConversationModel | None" = None
    dispatcher: "ConversationToolDispatcher | None" = None
    audit: "ConversationAudit | None" = None
    idempotency: "IdempotencyStore | None" = None
