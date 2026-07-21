"""Temporary-Chroma RAG service tests."""

from pathlib import Path

import pytest

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.core.exceptions import KnowledgeSourceNotFoundError
from restaurant_voice_ai.rag.bm25_store import BM25Store
from restaurant_voice_ai.rag.service import RagService
from restaurant_voice_ai.rag.vector_store import ChromaVectorStore
from tests.rag.helpers import FakeEmbeddings


def service(tmp_path: Path) -> RagService:
    settings = Settings(
        app_env="test",
        cors_origins=[],
        chroma_persist_directory=str(tmp_path / "chroma"),
        chroma_collection_name="test_knowledge",
        rag_chunk_size=120,
        rag_chunk_overlap=20,
        rag_score_threshold=0,
    )
    return RagService(
        settings,
        FakeEmbeddings(),
        ChromaVectorStore(settings.chroma_persist_directory, settings.chroma_collection_name),
        BM25Store(),
    )


@pytest.mark.asyncio
async def test_ingestion_is_deduplicated_and_deletable(tmp_path: Path) -> None:
    path = tmp_path / "menu.md"
    path.write_text(
        "# Menu\n\n## Paneer Tikka\n\nPaneer tikka contains dairy yogurt.", encoding="utf-8"
    )
    rag = service(tmp_path)
    first = await rag.ingest_file(path)
    second = await rag.ingest_file(path)
    assert first.chunk_count == second.chunk_count
    assert rag.get_stats().chunk_count == first.chunk_count
    assert rag.get_stats().indexed_source_count == 1
    assert rag.delete_source("menu.md") == first.chunk_count
    assert rag.get_stats().chunk_count == 0
    with pytest.raises(KnowledgeSourceNotFoundError):
        rag.delete_source("menu.md")


@pytest.mark.asyncio
async def test_context_and_citations_use_only_results(tmp_path: Path) -> None:
    path = tmp_path / "menu.md"
    path.write_text(
        "# Menu\n\n## Paneer Tikka\n\nPaneer tikka contains dairy yogurt.", encoding="utf-8"
    )
    rag = service(tmp_path)
    await rag.ingest_file(path)
    context = await rag.retrieve_context("Does paneer tikka contain dairy?", 3)
    assert context.evidence_found is True
    assert "[Source: menu.md | Section: Paneer Tikka]" in context.context
    assert context.citations == ["[Source: menu.md | Section: Paneer Tikka]"]
