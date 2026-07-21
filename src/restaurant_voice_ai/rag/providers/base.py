"""Common embedding provider contract."""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider-neutral asynchronous embedding interface."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document chunks in input order."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed one retrieval query."""

    @staticmethod
    def validate_vectors(vectors: list[list[float]], expected: int, provider: str) -> None:
        if len(vectors) != expected or any(not vector for vector in vectors):
            from restaurant_voice_ai.core.exceptions import EmbeddingProviderError

            raise EmbeddingProviderError(provider)
