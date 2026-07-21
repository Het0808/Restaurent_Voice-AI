"""Internal knowledge-document and retrieval models."""

from dataclasses import dataclass, field

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class SourceDocument:
    text: str
    source: str
    title: str
    document_type: str
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Chunk:
    chunk_id: str
    text: str
    source: str
    title: str
    section: str
    document_type: str
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    chunk: Chunk
    score: float


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunk: Chunk
    vector_score: float
    bm25_score: float
    hybrid_score: float


@dataclass(frozen=True, slots=True)
class RetrievalContext:
    context: str
    citations: list[str]
    results: list[RetrievalResult]
    evidence_found: bool


@dataclass(frozen=True, slots=True)
class IngestionResult:
    sources: list[str]
    source_count: int
    chunk_count: int


@dataclass(frozen=True, slots=True)
class KnowledgeStats:
    collection_name: str
    chunk_count: int
    indexed_source_count: int
    bm25_ready: bool
