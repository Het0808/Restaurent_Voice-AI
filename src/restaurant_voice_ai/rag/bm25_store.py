"""In-memory lexical BM25 index."""

import re

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

from restaurant_voice_ai.rag.models import Chunk, ScoredChunk

TOKEN = re.compile(r"[\w]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


class BM25Store:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.index: BM25Okapi | None = None

    @property
    def ready(self) -> bool:
        return self.index is not None and bool(self.chunks)

    def rebuild(self, chunks: list[Chunk]) -> None:
        self.chunks = list(chunks)
        corpus = [tokenize(chunk.text) for chunk in self.chunks]
        self.index = BM25Okapi(corpus) if corpus and all(corpus) else None

    def search(self, query: str, top_k: int) -> list[ScoredChunk]:
        tokens = tokenize(query)
        if not self.ready or not tokens or self.index is None:
            return []
        scores = self.index.get_scores(tokens)
        ranked = sorted(
            (
                ScoredChunk(chunk=chunk, score=max(0.0, float(score)))
                for chunk, score in zip(self.chunks, scores, strict=True)
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        return [item for item in ranked if item.score > 0][:top_k]
