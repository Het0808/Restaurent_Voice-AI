"""Document loading and deterministic chunking tests."""

from pathlib import Path

import pytest

from restaurant_voice_ai.core.exceptions import EmptyDocumentError, UnsupportedDocumentTypeError
from restaurant_voice_ai.rag.chunking import chunk_document
from restaurant_voice_ai.rag.loaders import load_document
from restaurant_voice_ai.rag.models import SourceDocument


def test_markdown_loading_preserves_source_and_title(tmp_path: Path) -> None:
    path = tmp_path / "menu.md"
    path.write_text(
        "# Sample Menu\n\n## Starters\n\nPaneer tikka contains dairy.", encoding="utf-8"
    )
    document = load_document(path)
    assert document.source == "menu.md"
    assert document.title == "Sample Menu"
    assert document.document_type == "markdown"


def test_unsupported_and_empty_documents_are_rejected(tmp_path: Path) -> None:
    unsupported = tmp_path / "menu.csv"
    unsupported.write_text("item,price", encoding="utf-8")
    empty = tmp_path / "empty.txt"
    empty.write_text("  \n", encoding="utf-8")
    with pytest.raises(UnsupportedDocumentTypeError):
        load_document(unsupported)
    with pytest.raises(EmptyDocumentError):
        load_document(empty)


def test_chunk_ids_are_deterministic_and_headings_are_retained() -> None:
    document = SourceDocument(
        text="# Menu\n\n## Starters\n\nPaneer tikka contains dairy and spices.",
        source="menu.md",
        title="Menu",
        document_type="markdown",
    )
    first = chunk_document(document, chunk_size=100, overlap=20)
    second = chunk_document(document, chunk_size=100, overlap=20)
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert first[0].section == "Starters"


def test_long_paragraph_chunks_overlap() -> None:
    text = "".join(str(number % 10) for number in range(260))
    document = SourceDocument(text=text, source="faq.txt", title="FAQ", document_type="text")
    chunks = chunk_document(document, chunk_size=100, overlap=20)
    assert len(chunks) == 4
    assert chunks[0].text[-20:] == chunks[1].text[:20]
