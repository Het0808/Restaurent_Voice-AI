"""Lazy FastAPI construction for the RAG service."""

from fastapi import Request

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.rag.bm25_store import BM25Store
from restaurant_voice_ai.rag.providers.factory import create_embedding_provider
from restaurant_voice_ai.rag.service import RagService
from restaurant_voice_ai.rag.vector_store import ChromaVectorStore


def build_rag_service(settings: Settings) -> RagService:
    return RagService(
        settings=settings,
        embeddings=create_embedding_provider(settings),
        vector_store=ChromaVectorStore(
            settings.chroma_persist_directory, settings.chroma_collection_name
        ),
        bm25_store=BM25Store(),
    )


def get_rag_service(request: Request) -> RagService:
    """Create one service lazily per app, without embedding calls or ingestion."""
    service = getattr(request.app.state, "rag_service", None)
    if service is None:
        service = build_rag_service(request.app.state.settings)
        request.app.state.rag_service = service
    return service
