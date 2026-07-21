"""Conversation contracts and dependency abstractions."""

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field

from restaurant_voice_ai.conversation.enums import Intent


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
