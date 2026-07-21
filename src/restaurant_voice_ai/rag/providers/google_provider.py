"""Google Gen AI embedding provider using the official current SDK."""

import asyncio
import logging
import math
from threading import Lock

from google import genai
from google.genai import types

from restaurant_voice_ai.core.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
)
from restaurant_voice_ai.rag.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class GoogleEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self._client_instance: genai.Client | None = None
        self._client_lock = Lock()

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise EmbeddingConfigurationError("google")
        with self._client_lock:
            if self._client_instance is None:
                self._client_instance = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(
                        timeout=30_000,
                        retry_options=types.HttpRetryOptions(
                            attempts=3,
                            initial_delay=1.0,
                            max_delay=8.0,
                            exp_base=2.0,
                            jitter=0.2,
                            http_status_codes=[408, 429, 500, 502, 503, 504],
                        ),
                    ),
                )
        return self._client_instance

    def close(self) -> None:
        """Close the cached synchronous client; a later request creates a fresh client."""
        with self._client_lock:
            client = self._client_instance
            self._client_instance = None
        if client is not None:
            client.close()

    @staticmethod
    def _parse_vectors(response: types.EmbedContentResponse, expected: int) -> list[list[float]]:
        if not response.embeddings:
            raise EmbeddingProviderError("google")
        vectors: list[list[float]] = []
        for embedding in response.embeddings:
            if not embedding.values:
                raise EmbeddingProviderError("google")
            vector: list[float] = []
            for value in embedding.values:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise EmbeddingProviderError("google")
                numeric_value = float(value)
                if not math.isfinite(numeric_value):
                    raise EmbeddingProviderError("google")
                vector.append(numeric_value)
            vectors.append(vector)
        EmbeddingProvider.validate_vectors(vectors, expected, "google")
        return vectors

    async def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        if not texts:
            return []
        config = types.EmbedContentConfig(task_type=task_type)
        try:
            client = self._get_client()
            response = await asyncio.to_thread(
                client.models.embed_content,
                model=self.model,
                contents=texts,
                config=config,
            )
        except EmbeddingConfigurationError:
            raise
        except Exception as exc:
            logger.warning("Google embedding request failed: %s", type(exc).__name__)
            raise EmbeddingProviderError("google") from exc
        return self._parse_vectors(response, len(texts))

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(texts, "RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed([text], "RETRIEVAL_QUERY")
        return vectors[0]
