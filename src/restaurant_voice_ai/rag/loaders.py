"""Local Markdown, text, and PDF document loaders."""

from pathlib import Path

from pypdf import PdfReader

from restaurant_voice_ai.core.exceptions import EmptyDocumentError, UnsupportedDocumentTypeError
from restaurant_voice_ai.rag.models import SourceDocument

SUPPORTED_EXTENSIONS = {".md": "markdown", ".txt": "text", ".pdf": "pdf"}


def load_document(path: Path, *, source_name: str | None = None) -> SourceDocument:
    """Load one supported local file without OCR or web access."""
    document_type = SUPPORTED_EXTENSIONS.get(path.suffix.lower())
    if document_type is None:
        raise UnsupportedDocumentTypeError()
    if document_type == "pdf":
        text = "\n\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    else:
        text = path.read_text(encoding="utf-8")
    text = text.strip()
    if not text:
        raise EmptyDocumentError()
    source = source_name or path.name
    title = next(
        (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")),
        Path(source).stem.replace("-", " ").title(),
    )
    return SourceDocument(
        text=text,
        source=source,
        title=title,
        document_type=document_type,
        metadata={"extension": path.suffix.lower()},
    )
