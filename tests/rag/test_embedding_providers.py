"""Embedding provider selection and configuration tests without network access."""

import pytest
from pydantic import ValidationError

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.core.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderConfigurationError,
)
from restaurant_voice_ai.rag.providers.factory import create_embedding_provider
from restaurant_voice_ai.rag.providers.google_provider import GoogleEmbeddingProvider
from restaurant_voice_ai.rag.providers.local_provider import LocalEmbeddingProvider
from restaurant_voice_ai.rag.providers.openai_provider import OpenAIEmbeddingProvider


def settings(**values: object) -> Settings:
    defaults: dict[str, object] = {
        "app_env": "test",
        "cors_origins": [],
        "google_api_key": None,
        "openai_api_key": None,
        "google_embedding_model": "text-embedding-004",
        "openai_embedding_model": "text-embedding-3-small",
        "local_embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    }
    defaults.update(values)
    return Settings(**defaults)


def test_google_is_default_provider() -> None:
    provider = create_embedding_provider(settings())
    assert isinstance(provider, GoogleEmbeddingProvider)
    assert provider.model == "text-embedding-004"


def test_openai_provider_selection() -> None:
    provider = create_embedding_provider(settings(embedding_provider="openai"))
    assert isinstance(provider, OpenAIEmbeddingProvider)
    assert provider.model == "text-embedding-3-small"


def test_local_provider_selection_is_lazy() -> None:
    provider = create_embedding_provider(settings(embedding_provider="local"))
    assert isinstance(provider, LocalEmbeddingProvider)
    assert provider.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert provider._model is None


def test_provider_switching_changes_implementation() -> None:
    configured = settings(embedding_provider="google")
    assert isinstance(create_embedding_provider(configured), GoogleEmbeddingProvider)
    assert isinstance(create_embedding_provider(configured, "openai"), OpenAIEmbeddingProvider)
    assert isinstance(create_embedding_provider(configured, "local"), LocalEmbeddingProvider)


def test_invalid_settings_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        settings(embedding_provider="unsupported")


def test_factory_rejects_unsupported_override() -> None:
    with pytest.raises(EmbeddingProviderConfigurationError):
        create_embedding_provider(settings(), "unsupported")


@pytest.mark.asyncio
async def test_remote_providers_report_missing_keys_without_network() -> None:
    google = create_embedding_provider(settings())
    openai = create_embedding_provider(settings(embedding_provider="openai"))
    with pytest.raises(EmbeddingConfigurationError, match="google"):
        await google.embed_query("test")
    with pytest.raises(EmbeddingConfigurationError, match="openai"):
        await openai.embed_query("test")
