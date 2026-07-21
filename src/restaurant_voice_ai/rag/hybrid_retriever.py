"""Weighted normalized-score hybrid retrieval and optional reranking."""

from typing import Protocol

from restaurant_voice_ai.rag.models import RetrievalResult, ScoredChunk


class VectorSearcher(Protocol):
    def query(self, embedding: list[float], top_k: int) -> list[ScoredChunk]: ...


class LexicalSearcher(Protocol):
    def search(self, query: str, top_k: int) -> list[ScoredChunk]: ...


class Reranker(Protocol):
    def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]: ...


class NoOpReranker:
    def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        return results


def _normalize(results: list[ScoredChunk]) -> dict[str, float]:
    if not results:
        return {}
    scores = [item.score for item in results]
    low, high = min(scores), max(scores)
    if high == low:
        value = 1.0 if high > 0 else 0.0
        return {item.chunk.chunk_id: value for item in results}
    return {item.chunk.chunk_id: (item.score - low) / (high - low) for item in results}


class HybridRetriever:
    """Fuse normalized semantic and lexical scores using configured weights."""

    def __init__(
        self,
        vector_store: VectorSearcher,
        bm25_store: LexicalSearcher,
        vector_weight: float,
        bm25_weight: float,
        threshold: float,
        reranker: Reranker | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.bm25_store = bm25_store
        total = vector_weight + bm25_weight
        self.vector_weight = vector_weight / total
        self.bm25_weight = bm25_weight / total
        self.threshold = threshold
        self.reranker = reranker or NoOpReranker()

    def retrieve(self, query: str, embedding: list[float], top_k: int) -> list[RetrievalResult]:
        candidate_count = max(top_k * 3, top_k)
        vector_results = self.vector_store.query(embedding, candidate_count)
        bm25_results = self.bm25_store.search(query, candidate_count)
        vector_scores = _normalize(vector_results)
        bm25_scores = _normalize(bm25_results)
        chunks = {item.chunk.chunk_id: item.chunk for item in vector_results + bm25_results}
        results = [
            RetrievalResult(
                chunk=chunk,
                vector_score=vector_scores.get(chunk_id, 0.0),
                bm25_score=bm25_scores.get(chunk_id, 0.0),
                hybrid_score=(
                    self.vector_weight * vector_scores.get(chunk_id, 0.0)
                    + self.bm25_weight * bm25_scores.get(chunk_id, 0.0)
                ),
            )
            for chunk_id, chunk in chunks.items()
        ]
        results = [item for item in results if item.hybrid_score >= self.threshold]
        results.sort(key=lambda item: (-item.hybrid_score, item.chunk.chunk_id))
        return self.reranker.rerank(query, results)[:top_k]
