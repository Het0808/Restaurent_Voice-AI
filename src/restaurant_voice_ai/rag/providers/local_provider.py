"""Lazy local Sentence Transformers embedding provider."""

import asyncio
import logging
from typing import Any

from restaurant_voice_ai.core.exceptions import (
    EmbeddingProviderError,
    EmbeddingProviderInitializationError,
)
from restaurant_voice_ai.rag.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str) -> None:
        self.model_name = model
        self._model: Any | None = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except Exception as exc:
                logger.exception("Local embedding model initialization failed")
                raise EmbeddingProviderInitializationError("local") from exc
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        try:
            values = self._get_model().encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [[float(value) for value in vector] for vector in values]
        except EmbeddingProviderInitializationError:
            raise
        except Exception as exc:
            logger.exception("Local embedding request failed")
            raise EmbeddingProviderError("local") from exc

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = await asyncio.to_thread(self._encode, texts)
        self.validate_vectors(vectors, len(texts), "local")
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]
