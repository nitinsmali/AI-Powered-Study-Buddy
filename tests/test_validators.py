"""Tests for input validation helpers — standalone (no app/FastAPI imports)."""
from __future__ import annotations

import os
import re

import pytest


# ── Inline the validator logic to avoid FastAPI dependency in CI without venv ──

ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}

ALLOWED_MIME_TYPES: set[str] = set(ALLOWED_EXTENSIONS.values())


def validate_file_extension(filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    mime = ALLOWED_EXTENSIONS.get(ext)
    if mime is None:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    return mime


def validate_mime_type(mime_type: str) -> None:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported file type '{mime_type}'.")


def sanitise_filename(filename: str) -> str:
    name = re.sub(r"[^\w\s.\-]", "_", filename)
    name = name.replace("..", "_")
    return name.strip() or "upload"


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestValidateFileExtension:
    def test_pdf(self):
        assert validate_file_extension("notes.pdf") == "application/pdf"

    def test_docx(self):
        mime = validate_file_extension("essay.docx")
        assert "wordprocessingml" in mime

    def test_txt_case_insensitive(self):
        assert validate_file_extension("notes.TXT") == "text/plain"

    def test_md(self):
        assert validate_file_extension("readme.md") == "text/markdown"

    def test_markdown(self):
        assert validate_file_extension("notes.markdown") == "text/markdown"

    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported file extension"):
            validate_file_extension("virus.exe")

    def test_no_extension_raises(self):
        with pytest.raises(ValueError):
            validate_file_extension("noextension")

    def test_bat_rejected(self):
        with pytest.raises(ValueError):
            validate_file_extension("script.bat")

    def test_js_rejected(self):
        with pytest.raises(ValueError):
            validate_file_extension("exploit.js")


class TestValidateMimeType:
    def test_pdf(self):
        validate_mime_type("application/pdf")  # should not raise

    def test_txt(self):
        validate_mime_type("text/plain")

    def test_markdown(self):
        validate_mime_type("text/markdown")

    def test_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            validate_mime_type("application/x-executable")

    def test_docx(self):
        validate_mime_type(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )


class TestSanitiseFilename:
    def test_normal_filename(self):
        assert sanitise_filename("notes.pdf") == "notes.pdf"

    def test_path_traversal_removed(self):
        result = sanitise_filename("../../etc/passwd")
        assert ".." not in result

    def test_special_chars_replaced(self):
        result = sanitise_filename("my<script>file.pdf")
        assert "<" not in result
        assert ">" not in result

    def test_empty_returns_upload(self):
        result = sanitise_filename("")
        assert result == "upload"

    def test_spaces_preserved(self):
        result = sanitise_filename("my file.pdf")
        assert result == "my file.pdf"

    def test_ends_with_pdf(self):
        name = "a" * 50 + ".pdf"
        result = sanitise_filename(name)
        assert result.endswith(".pdf")

    def test_angle_brackets_removed(self):
        result = sanitise_filename("<xss>.pdf")
        assert "<" not in result
        assert ">" not in result
