"""Restaurant knowledge ingestion and retrieval routes."""

import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from restaurant_voice_ai.core.exceptions import UnsupportedDocumentTypeError
from restaurant_voice_ai.rag.dependencies import get_rag_service
from restaurant_voice_ai.rag.loaders import SUPPORTED_EXTENSIONS
from restaurant_voice_ai.rag.models import RetrievalResult
from restaurant_voice_ai.rag.schemas.rag import (
    DeleteSourceResponse,
    IngestionResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatsResponse,
    RetrievalResultResponse,
)
from restaurant_voice_ai.rag.service import RagService

router = APIRouter(prefix="/knowledge", tags=["Restaurant knowledge"])
RagDependency = Annotated[RagService, Depends(get_rag_service)]
DEFAULT_KNOWLEDGE_DIRECTORY = Path("data/knowledge")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _result_response(result: RetrievalResult) -> RetrievalResultResponse:
    return RetrievalResultResponse(
        source=result.chunk.source,
        title=result.chunk.title,
        section=result.chunk.section,
        chunk_id=result.chunk.chunk_id,
        vector_score=result.vector_score,
        bm25_score=result.bm25_score,
        hybrid_score=result.hybrid_score,
        text_excerpt=result.chunk.text[:500],
    )


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    data: KnowledgeSearchRequest, service: RagDependency
) -> KnowledgeSearchResponse:
    context = await service.retrieve_context(data.query, data.top_k)
    return KnowledgeSearchResponse(
        query=data.query,
        results=[_result_response(result) for result in context.results],
        context=context.context,
        citations=context.citations,
        evidence_found=context.evidence_found,
    )


@router.post("/ingest/default", response_model=IngestionResponse)
async def ingest_default(service: RagDependency) -> IngestionResponse:
    result = await service.ingest_directory(DEFAULT_KNOWLEDGE_DIRECTORY)
    return IngestionResponse(
        sources=result.sources, source_count=result.source_count, chunk_count=result.chunk_count
    )


@router.post("/upload", response_model=IngestionResponse)
async def upload_knowledge(
    service: RagDependency, file: Annotated[UploadFile, File()]
) -> IngestionResponse:
    source = Path(file.filename or "").name
    suffix = Path(source).suffix.lower()
    if not source or suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedDocumentTypeError()
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise UnsupportedDocumentTypeError()
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        result = await service.ingest_file(temporary_path, source_name=source)
        return IngestionResponse(
            sources=result.sources, source_count=result.source_count, chunk_count=result.chunk_count
        )
    finally:
        if temporary_path is not None:
            os.unlink(temporary_path)


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def knowledge_stats(service: RagDependency) -> KnowledgeStatsResponse:
    stats = service.get_stats()
    return KnowledgeStatsResponse(
        collection_name=stats.collection_name,
        chunk_count=stats.chunk_count,
        indexed_source_count=stats.indexed_source_count,
        bm25_ready=stats.bm25_ready,
    )


@router.delete("/source/{source_name}", response_model=DeleteSourceResponse)
async def delete_source(source_name: str, service: RagDependency) -> DeleteSourceResponse:
    deleted = service.delete_source(source_name)
    return DeleteSourceResponse(source=source_name, deleted_chunks=deleted)
