from pathlib import Path

from fastapi import FastAPI
from starlette.requests import Request

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.rag.dependencies import get_rag_service
from restaurant_voice_ai.rag.models import Chunk
from restaurant_voice_ai.rag.service import RagService
from restaurant_voice_ai.rag.vector_store import ChromaVectorStore


def test_relative_chroma_path_resolves_from_project_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings(
        app_env="test",
        cors_origins=[],
        embedding_provider="local",
        chroma_persist_directory="data/chroma-test",
    )
    project_root = Path(__file__).resolve().parents[2]
    assert Path(settings.chroma_persist_directory) == project_root / "data/chroma-test"


def test_development_dependency_builds_and_caches_real_rag_service(tmp_path: Path) -> None:
    settings = Settings(
        app_env="development",
        cors_origins=[],
        embedding_provider="local",
        chroma_persist_directory=str(tmp_path / "chroma"),
    )
    app = FastAPI()
    app.state.settings = settings
    request = Request({"type": "http", "app": app})

    first = get_rag_service(request)
    second = get_rag_service(request)

    assert isinstance(first, RagService)
    assert second is first


def test_chroma_cosine_distance_is_converted_to_descending_similarity(
    tmp_path: Path,
) -> None:
    store = ChromaVectorStore(tmp_path / "distance-chroma", "distance_test")
    near = Chunk("near", "Paneer dairy", "menu.md", "Menu", "Paneer", "markdown")
    far = Chunk("far", "Parking", "faq.md", "FAQ", "Parking", "markdown")
    store.replace_source("menu.md", [near], [[1.0, 0.0]])
    store.replace_source("faq.md", [far], [[0.0, 1.0]])

    results = store.query([1.0, 0.0], 2)

    assert [result.chunk.chunk_id for result in results] == ["near", "far"]
    assert results[0].score > results[1].score
