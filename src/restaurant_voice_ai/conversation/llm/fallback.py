"""Deterministic model used when Gemini is disabled or unavailable."""

from restaurant_voice_ai.conversation.llm.schemas import (
    InterpretationResult,
    ResponseGenerationInput,
)
from restaurant_voice_ai.conversation.memory.models import ConversationMessage
from restaurant_voice_ai.conversation.models import EntityExtractor, IntentClassifier


class DeterministicConversationModel:
    provider_name = "rules"

    def __init__(self, classifier: IntentClassifier, extractor: EntityExtractor) -> None:
        self.classifier = classifier
        self.extractor = extractor

    async def interpret(
        self, message: str, language: str, history: list[ConversationMessage]
    ) -> InterpretationResult:
        del history
        classification = await self.classifier.classify(message, language)
        entities = await self.extractor.extract(message, classification.intent, language)
        return InterpretationResult(
            intent=classification.intent,
            confidence=classification.confidence,
            entities=entities.model_dump(exclude_none=True),
            language=language,
            reason_category="deterministic_rule_match",
        )

    async def generate_response(self, data: ResponseGenerationInput) -> str:
        return data.deterministic_fallback
