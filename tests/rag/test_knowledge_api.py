"""Knowledge endpoint contract tests with fake embeddings."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.main import create_app
from restaurant_voice_ai.rag.bm25_store import BM25Store
from restaurant_voice_ai.rag.dependencies import get_rag_service
from restaurant_voice_ai.rag.service import RagService
from restaurant_voice_ai.rag.vector_store import ChromaVectorStore
from tests.rag.helpers import FakeEmbeddings


@pytest_asyncio.fixture
async def knowledge_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    settings = Settings(
        app_env="test",
        cors_origins=[],
        chroma_persist_directory=str(tmp_path / "chroma"),
        chroma_collection_name="api_knowledge",
        rag_chunk_size=120,
        rag_chunk_overlap=20,
        rag_score_threshold=0,
    )
    service = RagService(
        settings,
        FakeEmbeddings(),
        ChromaVectorStore(settings.chroma_persist_directory, settings.chroma_collection_name),
        BM25Store(),
    )
    source = tmp_path / "menu.md"
    source.write_text("# Menu\n\n## Paneer Tikka\n\nPaneer tikka contains dairy yogurt.")
    await service.ingest_file(source)
    app = create_app(settings)
    app.dependency_overrides[get_rag_service] = lambda: service
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_search_response_and_stats(knowledge_client: AsyncClient) -> None:
    response = await knowledge_client.post(
        "/api/v1/knowledge/search",
        json={"query": "Does paneer tikka contain dairy?", "top_k": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"query", "results", "context", "citations", "evidence_found"}
    assert body["evidence_found"] is True
    assert body["results"][0]["source"] == "menu.md"
    assert "hybrid_score" in body["results"][0]

    stats = await knowledge_client.get("/api/v1/knowledge/stats")
    assert stats.status_code == 200
    assert stats.json()["chunk_count"] == 1
    assert stats.json()["bm25_ready"] is True


@pytest.mark.asyncio
async def test_search_validation_and_source_deletion(knowledge_client: AsyncClient) -> None:
    blank = await knowledge_client.post(
        "/api/v1/knowledge/search", json={"query": "   ", "top_k": 5}
    )
    invalid_top_k = await knowledge_client.post(
        "/api/v1/knowledge/search", json={"query": "parking", "top_k": 100}
    )
    deleted = await knowledge_client.delete("/api/v1/knowledge/source/menu.md")
    assert blank.status_code == 422
    assert invalid_top_k.status_code == 422
    assert deleted.status_code == 200
    assert deleted.json()["deleted_chunks"] == 1
