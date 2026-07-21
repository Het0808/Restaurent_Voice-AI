"""Deterministic, heading-aware text chunking."""

import hashlib
import re

from restaurant_voice_ai.rag.models import Chunk, SourceDocument

HEADING = re.compile(r"^(#{1,6})\s+(.+)$")


def _sections(document: SourceDocument) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading = "General"
    lines: list[str] = []
    for line in document.text.splitlines():
        match = HEADING.match(line.strip())
        if match:
            if "\n".join(lines).strip():
                sections.append((heading, "\n".join(lines).strip()))
            heading = match.group(2).strip()
            lines = []
        else:
            lines.append(line)
    if "\n".join(lines).strip():
        sections.append((heading, "\n".join(lines).strip()))
    return sections


def _window_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            step = chunk_size - overlap
            chunks.extend(
                paragraph[start : start + chunk_size] for start in range(0, len(paragraph), step)
            )
            continue
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > chunk_size:
            chunks.append(current)
            prefix = current[-overlap:] if overlap else ""
            current = f"{prefix}\n\n{paragraph}".strip()
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def chunk_document(document: SourceDocument, chunk_size: int, overlap: int) -> list[Chunk]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Chunk size must be positive and overlap smaller than chunk size")
    chunks: list[Chunk] = []
    for section, text in _sections(document):
        for position, content in enumerate(_window_text(text, chunk_size, overlap)):
            identity = f"{document.source}\0{section}\0{position}\0{content}"
            chunk_id = hashlib.sha256(identity.encode()).hexdigest()
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=content,
                    source=document.source,
                    title=document.title,
                    section=section,
                    document_type=document.document_type,
                    metadata=dict(document.metadata),
                )
            )
    return chunks
