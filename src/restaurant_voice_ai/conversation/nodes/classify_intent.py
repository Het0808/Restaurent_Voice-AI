"""Intent classification node and deterministic classifiers."""

import asyncio
import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types

from restaurant_voice_ai.conversation.enums import Intent
from restaurant_voice_ai.conversation.models import Classification, ConversationDependencies
from restaurant_voice_ai.conversation.state import ConversationState
from restaurant_voice_ai.core.config import Settings

logger = logging.getLogger(__name__)

RESERVATION_TERMS = ("reservation", "booking", "book", "table", "बुक", "બુક")
KNOWLEDGE_TERMS = (
    "menu",
    "dish",
    "food",
    "ingredient",
    "contain",
    "dairy",
    "milk",
    "cheese",
    "paneer",
    "nut",
    "peanut",
    "allergen",
    "allergy",
    "vegan",
    "vegetarian",
    "gluten",
    "gluten-free",
    "spicy",
    "dessert",
    "starter",
    "main course",
    "beverage",
    "serve",
    "available",
    "opening",
    "open",
    "closing",
    "close",
    "hours",
    "location",
    "located",
    "address",
    "parking",
    "takeaway",
    "delivery",
    "policy",
    "pets",
    "restaurant",
    "मेनू",
    "મેનુ",
)
QUESTION_SIGNALS = (
    "what ",
    "where ",
    "when ",
    "does ",
    "do ",
    "is ",
    "are ",
    "can ",
    "tell me",
    "about ",
)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _contains_word(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)


def _is_reservation_request(text: str, action_terms: tuple[str, ...]) -> bool:
    return _contains_any(text, action_terms) and _contains_any(text, RESERVATION_TERMS)


def _is_knowledge_question(text: str) -> bool:
    has_domain_term = _contains_any(text, KNOWLEDGE_TERMS)
    has_question_signal = text.rstrip().endswith("?") or _contains_any(text, QUESTION_SIGNALS)
    return has_domain_term and has_question_signal


class RuleBasedIntentClassifier:
    async def classify(self, message: str, language: str) -> Classification:
        del language
        text = message.casefold()
        if _is_reservation_request(text, ("cancel", "रद्द", "રદ")):
            return Classification(intent=Intent.CANCEL_RESERVATION, confidence=0.9)
        if _is_reservation_request(text, ("modify", "change", "reschedule", "बदल", "ફેરફાર")):
            return Classification(intent=Intent.MODIFY_RESERVATION, confidence=0.9)
        if _is_reservation_request(text, ("book", "reserve", "make a reservation", "बुक", "બુક")):
            return Classification(intent=Intent.CREATE_RESERVATION, confidence=0.9)
        availability_terms = ("available", "availability", "free", "खाली", "ઉપલબ્ધ")
        if _contains_any(text, availability_terms) and (
            _contains_any(text, RESERVATION_TERMS) or not _is_knowledge_question(text)
        ):
            return Classification(intent=Intent.CHECK_AVAILABILITY, confidence=0.9)
        if _contains_word(text, ("hello", "hi", "hey", "namaste", "नमस्ते", "નમસ્તે")):
            return Classification(intent=Intent.GREETING, confidence=0.9)
        if _is_knowledge_question(text):
            return Classification(intent=Intent.KNOWLEDGE_QUERY, confidence=0.9)
        if any(term in text for term in ("weather", "stock", "flight", "code")):
            return Classification(intent=Intent.UNSUPPORTED, confidence=0.9)
        return Classification(intent=Intent.UNKNOWN, confidence=0.4)


class GoogleIntentClassifier:
    def __init__(self, settings: Settings, fallback: RuleBasedIntentClassifier) -> None:
        self.fallback = fallback
        self.model = settings.google_chat_model
        self.client = (
            genai.Client(api_key=settings.google_api_key) if settings.google_api_key else None
        )

    async def classify(self, message: str, language: str) -> Classification:
        if self.client is None or not self.model:
            return await self.fallback.classify(message, language)
        prompt = (
            "Classify this restaurant receptionist message. Return JSON with intent and "
            "confidence. "
            f"Allowed intents: {', '.join(intent.value for intent in Intent)}. "
            f"Language: {language}. Message: {message}"
        )
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return Classification.model_validate(json.loads(response.text or "{}"))
        except Exception:
            logger.warning("Google intent classification failed; using rules", exc_info=True)
            return await self.fallback.classify(message, language)


def build_node(dependencies: ConversationDependencies) -> Any:
    async def classify_intent(state: ConversationState) -> ConversationState:
        result = await dependencies.classifier.classify(state["message"], state["language"])
        return {"intent": result.intent.value, "intent_confidence": result.confidence}

    return classify_intent
