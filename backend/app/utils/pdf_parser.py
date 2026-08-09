"""Document text extraction utilities.

Supports:
- PDF  (via pypdf)
- DOCX (via python-docx)
- TXT  (plain UTF-8)
- MD   (treated as plain text)
"""
from __future__ import annotations

import io
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_file(file_path: str, mime_type: str) -> tuple[str, int]:
    """
    Extract plain text from a file on disk.

    Returns:
        (extracted_text, page_count)

    Raises:
        ValueError if the mime type is unsupported or the file cannot be read.
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")

    if mime_type == "application/pdf":
        return _extract_pdf(path)
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        return _extract_docx(path)
    elif mime_type in ("text/plain", "text/markdown", "text/x-markdown"):
        return _extract_text(path)
    else:
        raise ValueError(f"Unsupported MIME type for extraction: {mime_type}")


def _extract_pdf(path: Path) -> tuple[str, int]:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages_text.append(text)

        full_text = "\n\n".join(pages_text)
        full_text = _clean_text(full_text)
        return full_text, len(reader.pages)
    except Exception as exc:
        logger.error("PDF extraction failed for %s: %s", path, exc)
        raise ValueError(f"Could not extract text from PDF: {exc}") from exc


def _extract_docx(path: Path) -> tuple[str, int]:
    try:
        import docx  # type: ignore

        doc = docx.Document(str(path))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        full_text = "\n\n".join(paragraphs)
        full_text = _clean_text(full_text)
        # DOCX doesn't have a reliable page count without rendering
        return full_text, 1
    except Exception as exc:
        logger.error("DOCX extraction failed for %s: %s", path, exc)
        raise ValueError(f"Could not extract text from DOCX: {exc}") from exc


def _extract_text(path: Path) -> tuple[str, int]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        text = _clean_text(text)
        # Estimate pages (roughly 300 words per page)
        words = len(text.split())
        pages = max(1, round(words / 300))
        return text, pages
    except Exception as exc:
        logger.error("Text extraction failed for %s: %s", path, exc)
        raise ValueError(f"Could not read text file: {exc}") from exc


def _clean_text(text: str) -> str:
    """Normalise whitespace while preserving paragraph breaks."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        cleaned.append(stripped)
    # Collapse more than 2 consecutive blank lines
    result_lines: list[str] = []
    blank_count = 0
    for line in cleaned:
        if line == "":
            blank_count += 1
            if blank_count <= 2:
                result_lines.append("")
        else:
            blank_count = 0
            result_lines.append(line)
    return "\n".join(result_lines).strip()
