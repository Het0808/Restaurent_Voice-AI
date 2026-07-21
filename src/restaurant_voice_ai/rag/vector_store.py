"""Persistent Chroma vector store adapter."""

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Embeddings

from restaurant_voice_ai.core.exceptions import VectorStoreError
from restaurant_voice_ai.rag.models import Chunk, ScoredChunk

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self, persist_directory: str | Path, collection_name: str) -> None:
        self.collection_name = collection_name
        try:
            self.client = chromadb.PersistentClient(path=str(persist_directory))
            self.collection: Collection = self.client.get_or_create_collection(
                name=collection_name, metadata={"hnsw:space": "cosine"}
            )
        except Exception as exc:
            logger.exception("Failed to initialize Chroma store")
            raise VectorStoreError() from exc

    @staticmethod
    def _metadata(chunk: Chunk) -> dict[str, str]:
        return {
            "source": chunk.source,
            "title": chunk.title,
            "section": chunk.section,
            "document_type": chunk.document_type,
            "metadata_json": json.dumps(chunk.metadata, sort_keys=True),
        }

    @staticmethod
    def _chunk(chunk_id: str, text: str, metadata: Mapping[str, Any]) -> Chunk:
        extra = json.loads(str(metadata.get("metadata_json", "{}")))
        return Chunk(
            chunk_id=chunk_id,
            text=text,
            source=str(metadata["source"]),
            title=str(metadata["title"]),
            section=str(metadata["section"]),
            document_type=str(metadata["document_type"]),
            metadata=extra,
        )

    def replace_source(
        self, source: str, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> None:
        if len(chunks) != len(embeddings):
            raise VectorStoreError()
        try:
            self.collection.delete(where={"source": source})
            if chunks:
                self.collection.upsert(
                    ids=[chunk.chunk_id for chunk in chunks],
                    documents=[chunk.text for chunk in chunks],
                    metadatas=[self._metadata(chunk) for chunk in chunks],
                    embeddings=cast(Embeddings, embeddings),
                )
        except Exception as exc:
            logger.exception("Failed to replace knowledge source in Chroma")
            raise VectorStoreError() from exc

    def delete_source(self, source: str) -> int:
        try:
            existing = self.collection.get(where={"source": source}, include=[])
            count = len(existing["ids"])
            if count:
                self.collection.delete(where={"source": source})
            return count
        except Exception as exc:
            logger.exception("Failed to delete Chroma source")
            raise VectorStoreError() from exc

    def query(self, embedding: list[float], top_k: int) -> list[ScoredChunk]:
        if self.count() == 0:
            return []
        try:
            response = self.collection.query(
                query_embeddings=cast(Embeddings, [embedding]),
                n_results=min(top_k, self.count()),
                include=["documents", "metadatas", "distances"],
            )
            ids = response["ids"][0]
            documents = response["documents"][0] if response["documents"] else []
            metadatas = response["metadatas"][0] if response["metadatas"] else []
            distances = response["distances"][0] if response["distances"] else []
            return [
                ScoredChunk(
                    chunk=self._chunk(chunk_id, document, metadata),
                    score=max(0.0, 1.0 - float(distance)),
                )
                for chunk_id, document, metadata, distance in zip(
                    ids, documents, metadatas, distances, strict=True
                )
            ]
        except Exception as exc:
            logger.exception("Chroma query failed")
            raise VectorStoreError() from exc

    def all_chunks(self) -> list[Chunk]:
        try:
            response = self.collection.get(include=["documents", "metadatas"])
            documents = response["documents"] or []
            metadatas = response["metadatas"] or []
            return [
                self._chunk(chunk_id, document, metadata)
                for chunk_id, document, metadata in zip(
                    response["ids"], documents, metadatas, strict=True
                )
            ]
        except Exception as exc:
            logger.exception("Failed to read Chroma chunks")
            raise VectorStoreError() from exc

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception as exc:
            raise VectorStoreError() from exc

    def source_count(self) -> int:
        return len({chunk.source for chunk in self.all_chunks()})
