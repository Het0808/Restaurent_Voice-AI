"""Hybrid score fusion tests."""

from restaurant_voice_ai.rag.hybrid_retriever import HybridRetriever
from restaurant_voice_ai.rag.models import Chunk, ScoredChunk


def chunk(chunk_id: str) -> Chunk:
    return Chunk(chunk_id, f"Text {chunk_id}", "faq.md", "FAQ", "General", "markdown")


class FakeVectorStore:
    def __init__(self, results: list[ScoredChunk]) -> None:
        self.results = results

    def query(self, embedding: list[float], top_k: int) -> list[ScoredChunk]:
        return self.results[:top_k]


class FakeBM25Store:
    def __init__(self, results: list[ScoredChunk]) -> None:
        self.results = results

    def search(self, query: str, top_k: int) -> list[ScoredChunk]:
        return self.results[:top_k]


def retrieve(vector: list[ScoredChunk], lexical: list[ScoredChunk], threshold: float = 0.0):
    retriever = HybridRetriever(
        FakeVectorStore(vector), FakeBM25Store(lexical), 0.6, 0.4, threshold
    )
    return retriever.retrieve("query", [1.0], 10)


def test_fusion_deduplicates_and_orders_results() -> None:
    results = retrieve(
        [ScoredChunk(chunk("shared"), 0.9), ScoredChunk(chunk("vector"), 0.2)],
        [ScoredChunk(chunk("shared"), 4.0), ScoredChunk(chunk("lexical"), 2.0)],
    )
    assert [result.chunk.chunk_id for result in results].count("shared") == 1
    assert results[0].chunk.chunk_id == "shared"
    assert results == sorted(results, key=lambda result: result.hybrid_score, reverse=True)


def test_threshold_and_missing_retriever_results() -> None:
    vector_only = retrieve([ScoredChunk(chunk("vector"), 0.8)], [], threshold=0.5)
    lexical_only = retrieve([], [ScoredChunk(chunk("lexical"), 3.0)], threshold=0.3)
    filtered = retrieve([ScoredChunk(chunk("vector"), 0.8)], [], threshold=0.9)
    assert vector_only[0].vector_score == 1.0
    assert lexical_only[0].bm25_score == 1.0
    assert filtered == []
