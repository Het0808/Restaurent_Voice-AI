"""OpenAI embedding provider."""

import logging

from openai import AsyncOpenAI, OpenAIError

from restaurant_voice_ai.core.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
)
from restaurant_voice_ai.rag.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _client(self) -> AsyncOpenAI:
        if not self.api_key:
            raise EmbeddingConfigurationError("openai")
        return AsyncOpenAI(api_key=self.api_key)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self._client().embeddings.create(model=self.model, input=texts)
        except OpenAIError as exc:
            logger.exception("OpenAI embedding request failed")
            raise EmbeddingProviderError("openai") from exc
        vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        self.validate_vectors(vectors, len(texts), "openai")
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]
