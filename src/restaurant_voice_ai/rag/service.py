"""Knowledge ingestion and retrieval orchestration without answer generation."""

import logging
from pathlib import Path

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.core.exceptions import (
    EmptyDocumentError,
    KnowledgeSourceNotFoundError,
    RetrievalError,
)
from restaurant_voice_ai.rag.bm25_store import BM25Store
from restaurant_voice_ai.rag.chunking import chunk_document
from restaurant_voice_ai.rag.hybrid_retriever import HybridRetriever
from restaurant_voice_ai.rag.loaders import SUPPORTED_EXTENSIONS, load_document
from restaurant_voice_ai.rag.models import (
    IngestionResult,
    KnowledgeStats,
    RetrievalContext,
    RetrievalResult,
)
from restaurant_voice_ai.rag.providers.base import EmbeddingProvider
from restaurant_voice_ai.rag.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class RagService:
    def __init__(
        self,
        settings: Settings,
        embeddings: EmbeddingProvider,
        vector_store: ChromaVectorStore,
        bm25_store: BM25Store,
    ) -> None:
        self.settings = settings
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.bm25_store = bm25_store
        self.bm25_store.rebuild(self.vector_store.all_chunks())
        self.retriever = HybridRetriever(
            vector_store,
            bm25_store,
            settings.rag_vector_weight,
            settings.rag_bm25_weight,
            settings.rag_score_threshold,
        )

    async def ingest_file(self, path: Path, *, source_name: str | None = None) -> IngestionResult:
        document = load_document(path, source_name=source_name)
        chunks = chunk_document(
            document, self.settings.rag_chunk_size, self.settings.rag_chunk_overlap
        )
        if not chunks:
            raise EmptyDocumentError()
        vectors = await self.embeddings.embed_documents([chunk.text for chunk in chunks])
        self.vector_store.replace_source(document.source, chunks, vectors)
        self.bm25_store.rebuild(self.vector_store.all_chunks())
        return IngestionResult(sources=[document.source], source_count=1, chunk_count=len(chunks))

    async def ingest_directory(self, directory: Path) -> IngestionResult:
        sources: list[str] = []
        chunk_count = 0
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                result = await self.ingest_file(path)
                sources.extend(result.sources)
                chunk_count += result.chunk_count
        return IngestionResult(sources=sources, source_count=len(sources), chunk_count=chunk_count)

    async def search(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        try:
            embedding = await self.embeddings.embed_query(query)
            return self.retriever.retrieve(query, embedding, top_k or self.settings.rag_top_k)
        except Exception as exc:
            from restaurant_voice_ai.core.exceptions import ApplicationError

            if isinstance(exc, ApplicationError):
                raise
            logger.exception("Unexpected hybrid retrieval failure")
            raise RetrievalError() from exc

    async def retrieve_context(self, query: str, top_k: int | None = None) -> RetrievalContext:
        results = await self.search(query, top_k)
        markers: list[str] = []
        citations: list[str] = []
        for result in results:
            marker = f"[Source: {result.chunk.source} | Section: {result.chunk.section}]"
            markers.append(f"{marker}\n{result.chunk.text}")
            citations.append(marker)
        return RetrievalContext(
            context="\n\n".join(markers),
            citations=citations,
            results=results,
            evidence_found=bool(results),
        )

    def delete_source(self, source: str) -> int:
        safe_source = Path(source).name
        if safe_source != source:
            raise KnowledgeSourceNotFoundError()
        deleted = self.vector_store.delete_source(safe_source)
        if not deleted:
            raise KnowledgeSourceNotFoundError()
        self.bm25_store.rebuild(self.vector_store.all_chunks())
        return deleted

    def get_stats(self) -> KnowledgeStats:
        return KnowledgeStats(
            collection_name=self.vector_store.collection_name,
            chunk_count=self.vector_store.count(),
            indexed_source_count=self.vector_store.source_count(),
            bm25_ready=self.bm25_store.ready,
        )
