"""Tests for document text extraction utilities — standalone (no FastAPI)."""
from __future__ import annotations

from pathlib import Path

import pytest


# ── Inline the text extraction logic ─────────────────────────────────────────


def _clean_text(text: str) -> str:
    """Normalise whitespace while preserving paragraph breaks."""
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines]
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


def _extract_text(path: Path) -> tuple[str, int]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        text = _clean_text(text)
        words = len(text.split())
        pages = max(1, round(words / 300))
        return text, pages
    except FileNotFoundError:
        raise ValueError(f"File not found: {path}")
    except Exception as exc:
        raise ValueError(f"Could not read text file: {exc}") from exc


def extract_text_from_file(file_path: str, mime_type: str) -> tuple[str, int]:
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")

    if mime_type in ("text/plain", "text/markdown", "text/x-markdown"):
        return _extract_text(path)
    elif mime_type == "application/pdf":
        raise ValueError("PDF extraction requires pypdf — not tested standalone")
    else:
        raise ValueError(f"Unsupported MIME type for extraction: {mime_type}")


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestCleanText:
    def test_strips_leading_trailing_whitespace(self):
        result = _clean_text("  hello world  ")
        assert result == "hello world"

    def test_collapses_excessive_blank_lines(self):
        text = "line1\n\n\n\n\n\n\nline2"
        result = _clean_text(text)
        # The function allows up to 2 blank lines between sections (3 \n total)
        # but should collapse 5+ blank lines down to max 2
        assert "\n\n\n\n" not in result  # no 4+ consecutive newlines
        assert "line1" in result
        assert "line2" in result

    def test_preserves_paragraph_breaks(self):
        text = "paragraph one\n\nparagraph two"
        result = _clean_text(text)
        assert "paragraph one" in result
        assert "paragraph two" in result

    def test_empty_string(self):
        assert _clean_text("") == ""

    def test_only_whitespace(self):
        assert _clean_text("   \n   \n   ") == ""


class TestExtractTextFile:
    def test_plain_text_extraction(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!\nSecond line.", encoding="utf-8")
        text, pages = _extract_text(test_file)
        assert "Hello, World!" in text
        assert pages >= 1

    def test_markdown_extraction(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Heading\n\nParagraph text here.", encoding="utf-8")
        text, pages = _extract_text(test_file)
        assert "Heading" in text
        assert "Paragraph text here" in text

    def test_page_count_estimate(self, tmp_path):
        """~600 words ≈ 2 pages."""
        content = ("word " * 600).strip()
        test_file = tmp_path / "long.txt"
        test_file.write_text(content, encoding="utf-8")
        text, pages = _extract_text(test_file)
        assert pages >= 2

    def test_missing_file_raises(self, tmp_path):
        missing = tmp_path / "nonexistent.txt"
        with pytest.raises(ValueError, match="not found"):
            _extract_text(missing)


class TestExtractFromFile:
    """Integration tests for the extract_text_from_file dispatcher."""

    def test_txt_mime_type(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("Study notes content here.", encoding="utf-8")
        text, pages = extract_text_from_file(str(f), "text/plain")
        assert "Study notes" in text

    def test_markdown_mime_type(self, tmp_path):
        f = tmp_path / "notes.md"
        f.write_text("# Notes\nSome content.", encoding="utf-8")
        text, pages = extract_text_from_file(str(f), "text/markdown")
        assert "Notes" in text

    def test_unsupported_mime_raises(self, tmp_path):
        f = tmp_path / "file.xyz"
        f.write_bytes(b"\x00\x01\x02")
        with pytest.raises(ValueError, match="Unsupported MIME"):
            extract_text_from_file(str(f), "application/octet-stream")

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            extract_text_from_file(str(tmp_path / "missing.txt"), "text/plain")
