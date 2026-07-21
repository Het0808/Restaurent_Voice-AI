"""Provider-neutral conversation model contract."""

from typing import Protocol

from restaurant_voice_ai.conversation.llm.schemas import (
    InterpretationResult,
    ResponseGenerationInput,
)
from restaurant_voice_ai.conversation.memory.models import ConversationMessage


class ConversationModel(Protocol):
    provider_name: str

    async def interpret(
        self, message: str, language: str, history: list[ConversationMessage]
    ) -> InterpretationResult: ...

    async def generate_response(self, data: ResponseGenerationInput) -> str: ...
