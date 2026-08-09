"""Input validation helpers."""
from __future__ import annotations

import re

# Allowed file extensions mapped to expected MIME types
ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}

ALLOWED_MIME_TYPES: set[str] = set(ALLOWED_EXTENSIONS.values())


def validate_file_extension(filename: str) -> str:
    """
    Return the normalised MIME type for a filename or raise ValueError.
    """
    import os

    ext = os.path.splitext(filename.lower())[1]
    mime = ALLOWED_EXTENSIONS.get(ext)
    if mime is None:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    return mime


def validate_mime_type(mime_type: str) -> None:
    """Raise ValueError if the MIME type is not allowed."""
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Unsupported file type '{mime_type}'. "
            f"Allowed: PDF, DOCX, TXT, Markdown."
        )


def sanitise_filename(filename: str) -> str:
    """Remove dangerous characters from a user-supplied filename."""
    # Keep alphanumeric, dots, dashes, underscores, spaces
    name = re.sub(r"[^\w\s.\-]", "_", filename)
    # Prevent path traversal
    name = name.replace("..", "_")
    return name.strip() or "upload"
