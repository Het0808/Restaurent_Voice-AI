"""BM25 lexical retrieval tests."""

from restaurant_voice_ai.rag.bm25_store import BM25Store, tokenize
from restaurant_voice_ai.rag.models import Chunk


def make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id, text, "faq.md", "FAQ", "General", "markdown")


def test_tokenization_and_bm25_ranking() -> None:
    store = BM25Store()
    store.rebuild(
        [
            make_chunk("dairy", "Paneer tikka contains dairy yogurt"),
            make_chunk("parking", "Parking is behind the restaurant"),
            make_chunk("hours", "Opening hours include lunch and dinner"),
        ]
    )
    results = store.search("Does paneer contain dairy?", 3)
    assert tokenize("Paneer, DAIRY!") == ["paneer", "dairy"]
    assert results[0].chunk.chunk_id == "dairy"
    assert store.ready is True


def test_empty_bm25_index_is_safe() -> None:
    store = BM25Store()
    assert store.search("anything", 5) == []
