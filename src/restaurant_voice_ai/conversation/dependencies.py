"""Production adapters and classifier/extractor construction."""

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.conversation.models import (
    ConversationDependencies,
    ConversationEntities,
    EntityExtractor,
    IntentClassifier,
)
from restaurant_voice_ai.conversation.nodes.classify_intent import (
    GoogleIntentClassifier,
    RuleBasedIntentClassifier,
)
from restaurant_voice_ai.conversation.nodes.extract_entities import (
    GoogleEntityExtractor,
    RuleBasedEntityExtractor,
)
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.db.schemas.reservation import ReservationCreate, ReservationUpdate
from restaurant_voice_ai.db.services.reservation_service import ReservationService
from restaurant_voice_ai.rag.service import RagService


def _reservation_dict(reservation: Any) -> dict[str, Any]:
    return {
        "id": str(reservation.id),
        "confirmation_code": reservation.confirmation_code,
        "status": str(reservation.status.value),
        "customer_name": reservation.customer_name,
        "party_size": reservation.party_size,
        "reservation_start": reservation.reservation_start.isoformat(),
        "reservation_end": reservation.reservation_end.isoformat(),
    }


class RagKnowledgeGateway:
    def __init__(self, service: RagService) -> None:
        self.service = service

    async def retrieve(self, query: str) -> dict[str, Any]:
        context = await self.service.retrieve_context(query)
        results = [
            {
                "text": result.chunk.text,
                "content": result.chunk.text,
                "source": result.chunk.source,
                "source_filename": Path(result.chunk.source).name,
                "chunk_id": result.chunk.chunk_id,
                "section": result.chunk.section,
                "heading": result.chunk.section,
                "title": result.chunk.title,
                "score": result.hybrid_score,
                "vector_score": result.vector_score,
                "bm25_score": result.bm25_score,
                "metadata": dict(result.chunk.metadata),
            }
            for result in context.results
        ]
        seen: set[tuple[str, str]] = set()
        citations: list[dict[str, Any]] = []
        for result in results:
            identity = (str(result["source"]), str(result["chunk_id"]))
            if identity in seen:
                continue
            seen.add(identity)
            citations.append(
                {
                    "source": result["source"],
                    "source_filename": result["source_filename"],
                    "chunk_id": result["chunk_id"],
                    "section": result["section"],
                    "score": result["score"],
                    "metadata": result["metadata"],
                }
            )
        return {
            "retrieval_results": results,
            "retrieved_context": context.context,
            "citations": citations,
            "evidence_found": context.evidence_found,
        }


class DatabaseReservationGateway:
    def __init__(self, service: ReservationService, settings: Settings) -> None:
        self.service = service
        self.settings = settings

    def _start(self, entities: ConversationEntities, *, requested: bool = False) -> datetime:
        date = entities.requested_date if requested else entities.reservation_date
        time = entities.requested_time if requested else entities.reservation_time
        if not date or not time:
            raise ValueError("Reservation date and time are required")
        return datetime.fromisoformat(f"{date}T{time}").replace(
            tzinfo=ZoneInfo(self.settings.restaurant_timezone)
        )

    async def check_availability(self, entities: ConversationEntities) -> dict[str, Any]:
        start = self._start(entities)
        end = start + timedelta(minutes=self.settings.default_reservation_duration_minutes)
        tables = await self.service.check_availability(entities.party_size or 0, start, end)
        return {"available": bool(tables), "table_count": len(tables)}

    async def create(self, entities: ConversationEntities, language: str) -> dict[str, Any]:
        reservation = await self.service.create(
            ReservationCreate(
                customer_name=entities.customer_name or "",
                customer_phone=entities.customer_phone or "",
                party_size=entities.party_size or 0,
                reservation_start=self._start(entities),
                language=language,
            )
        )
        return _reservation_dict(reservation)

    async def _resolve(self, identifier: str) -> Any:
        try:
            return await self.service.get(uuid.UUID(identifier))
        except ValueError:
            return await self.service.get_by_code(identifier.upper())

    async def cancel(self, reservation_id: str) -> dict[str, Any]:
        existing = await self._resolve(reservation_id)
        reservation = await self.service.cancel(existing.id)
        return _reservation_dict(reservation)

    async def modify(self, entities: ConversationEntities) -> dict[str, Any]:
        existing = await self._resolve(entities.reservation_id or "")
        updates: dict[str, Any] = {}
        if entities.requested_party_size is not None:
            updates["party_size"] = entities.requested_party_size
        if entities.requested_date or entities.requested_time:
            current = existing.reservation_start
            date = entities.requested_date or current.date().isoformat()
            time = entities.requested_time or current.strftime("%H:%M")
            updates["reservation_start"] = datetime.fromisoformat(f"{date}T{time}").replace(
                tzinfo=ZoneInfo(self.settings.restaurant_timezone)
            )
        reservation = await self.service.update(existing.id, ReservationUpdate(**updates))
        return _reservation_dict(reservation)


def build_conversation_dependencies(
    settings: Settings, session: AsyncSession, rag_service: RagService
) -> ConversationDependencies:
    rule_classifier = RuleBasedIntentClassifier()
    rule_extractor = RuleBasedEntityExtractor(settings.restaurant_timezone)
    classifier: IntentClassifier = rule_classifier
    extractor: EntityExtractor = rule_extractor
    if settings.conversation_intent_provider == "google":
        classifier = GoogleIntentClassifier(settings, rule_classifier)
        extractor = GoogleEntityExtractor(settings, rule_extractor)
    return ConversationDependencies(
        classifier=classifier,
        extractor=extractor,
        knowledge=RagKnowledgeGateway(rag_service),
        reservations=DatabaseReservationGateway(ReservationService(session, settings), settings),
        settings=settings,
    )
