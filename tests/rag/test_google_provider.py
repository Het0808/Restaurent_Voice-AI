"""Offline tests for the synchronous Google GenAI embedding adapter."""

from collections.abc import Callable
from typing import Any, cast

import pytest
from google import genai
from google.genai import types

from restaurant_voice_ai.core.exceptions import EmbeddingProviderError
from restaurant_voice_ai.rag.providers import google_provider as provider_module
from restaurant_voice_ai.rag.providers.google_provider import GoogleEmbeddingProvider


def response(*vectors: list[float]) -> types.EmbedContentResponse:
    return types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=vector) for vector in vectors]
    )


class FakeModels:
    def __init__(
        self,
        result: types.EmbedContentResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def embed_content(self, **kwargs: Any) -> types.EmbedContentResponse:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


class FakeClient:
    def __init__(self, models: FakeModels) -> None:
        self.models = models
        self.closed = False

    def close(self) -> None:
        self.closed = True


def provider_with(models: FakeModels) -> tuple[GoogleEmbeddingProvider, FakeClient]:
    provider = GoogleEmbeddingProvider("test-key", "text-embedding-004")
    client = FakeClient(models)
    provider._client_instance = cast(genai.Client, client)
    return provider, client


@pytest.mark.asyncio
async def test_document_embedding_uses_to_thread_and_document_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = FakeModels(response([1, 2.5], [3.0, 4]))
    provider, _ = provider_with(models)
    thread_calls: list[Callable[..., object]] = []

    async def fake_to_thread(function: Callable[..., object], /, *args: Any, **kwargs: Any) -> Any:
        thread_calls.append(function)
        return function(*args, **kwargs)

    monkeypatch.setattr(provider_module.asyncio, "to_thread", fake_to_thread)
    vectors = await provider.embed_documents(["first", "second"])

    assert vectors == [[1.0, 2.5], [3.0, 4.0]]
    assert thread_calls == [models.embed_content]
    assert models.calls[0]["model"] == "text-embedding-004"
    assert models.calls[0]["contents"] == ["first", "second"]
    assert models.calls[0]["config"].task_type == "RETRIEVAL_DOCUMENT"


@pytest.mark.asyncio
async def test_query_embedding_uses_query_task() -> None:
    models = FakeModels(response([0.25, 0.75]))
    provider, _ = provider_with(models)

    vector = await provider.embed_query("where is parking?")

    assert vector == [0.25, 0.75]
    assert models.calls[0]["contents"] == ["where is parking?"]
    assert models.calls[0]["config"].task_type == "RETRIEVAL_QUERY"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result",
    [
        types.EmbedContentResponse(embeddings=[]),
        response([]),
        response([1.0]),
    ],
)
async def test_invalid_embedding_responses_are_rejected(
    result: types.EmbedContentResponse,
) -> None:
    provider, _ = provider_with(FakeModels(result))
    with pytest.raises(EmbeddingProviderError, match="google"):
        await provider.embed_documents(["first", "second"])


@pytest.mark.asyncio
async def test_sdk_exception_is_converted_without_network() -> None:
    provider, _ = provider_with(FakeModels(error=RuntimeError("sdk failed")))
    with pytest.raises(EmbeddingProviderError, match="google"):
        await provider.embed_query("test")


def test_close_discards_client_and_does_not_reuse_it(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, original = provider_with(FakeModels(response([1.0])))
    replacement = FakeClient(FakeModels(response([2.0])))
    monkeypatch.setattr(provider_module.genai, "Client", lambda **_: replacement)

    provider.close()

    assert original.closed is True
    assert provider._get_client() is replacement
