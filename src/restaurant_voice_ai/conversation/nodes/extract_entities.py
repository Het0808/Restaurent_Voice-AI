"""Conservative structured entity extraction."""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

from restaurant_voice_ai.conversation.enums import Intent
from restaurant_voice_ai.conversation.models import ConversationDependencies, ConversationEntities
from restaurant_voice_ai.conversation.state import ConversationState
from restaurant_voice_ai.core.config import Settings

logger = logging.getLogger(__name__)
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


class RuleBasedEntityExtractor:
    def __init__(self, timezone: str, now: Any | None = None) -> None:
        self.timezone = ZoneInfo(timezone)
        self.now = now or (lambda: datetime.now(self.timezone))

    async def extract(self, message: str, intent: Intent, language: str) -> ConversationEntities:
        del language
        text = message.strip()
        lower = text.casefold()
        data: dict[str, Any] = {}
        date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", lower)
        if date_match:
            data["reservation_date"] = date_match.group(1)
        elif "tomorrow" in lower:
            data["reservation_date"] = (self.now().date() + timedelta(days=1)).isoformat()
        time_match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\s*(am|pm)?\b", lower)
        if not time_match:
            time_match = re.search(r"\b(1[0-2]|[1-9])\s*(am|pm)\b", lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = (
                int(time_match.group(2))
                if time_match.lastindex
                and time_match.lastindex >= 2
                and time_match.group(2)
                and time_match.group(2).isdigit()
                else 0
            )
            meridiem = time_match.group(time_match.lastindex or 0)
            if meridiem in {"am", "pm"}:
                hour = hour % 12 + (12 if meridiem == "pm" else 0)
            data["reservation_time"] = f"{hour:02d}:{minute:02d}"
        party = re.search(r"\b(?:table\s+)?for\s+(\d+|" + "|".join(NUMBER_WORDS) + r")\b", lower)
        if party:
            data["party_size"] = (
                int(party.group(1)) if party.group(1).isdigit() else NUMBER_WORDS[party.group(1)]
            )
        identifier = re.search(
            r"\b(?:reservation|booking|confirmation)(?:\s+(?:id|code))?\s*(?:is|#|:)?\s*([A-Z0-9-]{6,40})\b",
            text,
            re.I,
        )
        if identifier:
            data["reservation_id"] = identifier.group(1).upper()
        name = re.search(
            r"\b(?:my name is|name is)\s+([A-Za-z][A-Za-z .'-]{0,60}?)"
            r"(?=\s+(?:and|phone|number)\b|[,.;]|$)",
            text,
            re.I,
        )
        if name:
            data["customer_name"] = name.group(1).strip()
        phone = re.search(
            r"\b(?:phone|number)(?:\s+(?:is))?\s*[:=-]?\s*(\+?[\d][\d ()-]{6,20})", text, re.I
        )
        if phone:
            normalized = (
                "+" + re.sub(r"\D", "", phone.group(1))
                if phone.group(1).startswith("+")
                else re.sub(r"\D", "", phone.group(1))
            )
            if 7 <= len(normalized.lstrip("+")) <= 15:
                data["customer_phone"] = normalized
        if intent is Intent.MODIFY_RESERVATION:
            for source, target in (
                ("reservation_date", "requested_date"),
                ("reservation_time", "requested_time"),
                ("party_size", "requested_party_size"),
            ):
                if source in data:
                    data[target] = data.pop(source)
        return ConversationEntities.model_validate(data)


class GoogleEntityExtractor:
    def __init__(self, settings: Settings, fallback: RuleBasedEntityExtractor) -> None:
        self.fallback = fallback
        self.model = settings.google_chat_model
        self.client = (
            genai.Client(api_key=settings.google_api_key) if settings.google_api_key else None
        )

    async def extract(self, message: str, intent: Intent, language: str) -> ConversationEntities:
        if self.client is None or not self.model:
            return await self.fallback.extract(message, intent, language)
        prompt = (
            "Extract only explicit restaurant reservation entities as JSON. "
            f"Intent: {intent.value}. Language: {language}. Message: {message}"
        )
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return ConversationEntities.model_validate(json.loads(response.text or "{}"))
        except Exception:
            logger.warning("Google entity extraction failed; using rules", exc_info=True)
            return await self.fallback.extract(message, intent, language)


def build_node(dependencies: ConversationDependencies) -> Any:
    async def extract_entities(state: ConversationState) -> ConversationState:
        entities = await dependencies.extractor.extract(
            state["message"], Intent(state["intent"]), state["language"]
        )
        return {"entities": entities.model_dump(exclude_none=True)}

    return extract_entities
