"""Embedding provider selection from application settings."""

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.core.exceptions import EmbeddingProviderConfigurationError
from restaurant_voice_ai.rag.providers.base import EmbeddingProvider
from restaurant_voice_ai.rag.providers.google_provider import GoogleEmbeddingProvider
from restaurant_voice_ai.rag.providers.local_provider import LocalEmbeddingProvider
from restaurant_voice_ai.rag.providers.openai_provider import OpenAIEmbeddingProvider


def create_embedding_provider(settings: Settings, provider: str | None = None) -> EmbeddingProvider:
    selected = provider or settings.embedding_provider
    if selected == "google":
        return GoogleEmbeddingProvider(settings.google_api_key, settings.google_embedding_model)
    if selected == "openai":
        return OpenAIEmbeddingProvider(settings.openai_api_key, settings.openai_embedding_model)
    if selected == "local":
        return LocalEmbeddingProvider(settings.local_embedding_model)
    raise EmbeddingProviderConfigurationError(selected)
