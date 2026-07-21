"""Google GenAI conversation model using synchronous calls in worker threads."""

import asyncio
import json
import logging

from google import genai
from google.genai import types

from restaurant_voice_ai.conversation.llm.prompts import (
    INTERPRETATION_SYSTEM_PROMPT,
    RESPONSE_SYSTEM_PROMPT,
)
from restaurant_voice_ai.conversation.llm.schemas import (
    InterpretationResult,
    ResponseGenerationInput,
)
from restaurant_voice_ai.conversation.memory.models import ConversationMessage

logger = logging.getLogger(__name__)


class GoogleConversationModel:
    provider_name = "google"

    def __init__(self, api_key: str | None, model: str | None) -> None:
        self.model = model
        self._client = genai.Client(api_key=api_key) if api_key and model else None

    async def interpret(
        self, message: str, language: str, history: list[ConversationMessage]
    ) -> InterpretationResult:
        if self._client is None or self.model is None:
            raise RuntimeError("Google conversation model is not configured")
        safe_history = [{"role": item.role, "content": item.content} for item in history[-6:]]
        prompt = json.dumps(
            {"message": message, "language": language, "recent_history": safe_history}
        )
        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=INTERPRETATION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=InterpretationResult,
            ),
        )
        return InterpretationResult.model_validate_json(response.text or "{}")

    async def generate_response(self, data: ResponseGenerationInput) -> str:
        if self._client is None or self.model is None:
            raise RuntimeError("Google conversation model is not configured")
        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.model,
            contents=data.model_dump_json(),
            config=types.GenerateContentConfig(system_instruction=RESPONSE_SYSTEM_PROMPT),
        )
        return (response.text or "").strip()
