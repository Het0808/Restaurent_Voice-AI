"""Pydantic schemas for retrieval-only knowledge APIs."""

from pydantic import BaseModel, Field, field_validator


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value


class RetrievalResultResponse(BaseModel):
    source: str
    title: str
    section: str
    chunk_id: str
    vector_score: float
    bm25_score: float
    hybrid_score: float
    text_excerpt: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[RetrievalResultResponse]
    context: str
    citations: list[str]
    evidence_found: bool


class IngestionResponse(BaseModel):
    sources: list[str]
    source_count: int
    chunk_count: int


class KnowledgeStatsResponse(BaseModel):
    collection_name: str
    chunk_count: int
    indexed_source_count: int
    bm25_ready: bool


class DeleteSourceResponse(BaseModel):
    source: str
    deleted_chunks: int
