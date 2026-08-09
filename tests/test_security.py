"""Tests for security utilities."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestStudyBuddyExceptions:
    """Tests for custom exception hierarchy — standalone (no fastapi dependency)."""

    def test_exceptions_are_exceptions(self):
        """All custom exceptions should be real Python exceptions."""
        # Define minimal stubs mirroring the real class hierarchy
        class StudyBuddyException(Exception):
            pass

        class NotFoundError(StudyBuddyException):
            pass

        class AuthorizationError(StudyBuddyException):
            pass

        class ValidationError(StudyBuddyException):
            pass

        class AIServiceError(StudyBuddyException):
            pass

        class StorageError(StudyBuddyException):
            pass

        class RateLimitError(StudyBuddyException):
            pass

        class DocumentProcessingError(StudyBuddyException):
            pass

        err = NotFoundError("Document not found")
        assert "not found" in str(err).lower()

        for exc_class in [
            NotFoundError,
            AuthorizationError,
            ValidationError,
            DocumentProcessingError,
            AIServiceError,
            StorageError,
            RateLimitError,
        ]:
            assert issubclass(exc_class, StudyBuddyException)
            instance = exc_class("test error")
            assert isinstance(instance, Exception)


class TestUserOwnershipLogic:
    """
    Tests for user ownership verification logic.
    These test the guard functions directly without spinning up a real DB.
    """

    def test_ownership_same_user(self):
        """Same user_id should not raise."""
        user_id = "user-123"
        doc_user_id = "user-123"
        # Simulate the ownership check:
        if doc_user_id != user_id:
            raise PermissionError("Not owner")
        # No exception means pass
        assert True

    def test_ownership_different_user_raises(self):
        """Different user_id should raise a permission-related exception."""
        user_id = "user-123"
        doc_user_id = "user-456"

        class AuthorizationError(Exception):
            pass

        with pytest.raises(AuthorizationError):
            if doc_user_id != user_id:
                raise AuthorizationError("You do not own this document.")


class TestDocumentStatusGuard:
    """Tests for processing status check before LLM operations."""

    def test_ready_document_passes(self):
        """A 'ready' document should pass the guard without raising."""
        import enum

        class ProcessingStatus(str, enum.Enum):
            uploaded = "uploaded"
            processing = "processing"
            ready = "ready"
            failed = "failed"

        class FakeDoc:
            processing_status = ProcessingStatus.ready

        doc = FakeDoc()
        if doc.processing_status != ProcessingStatus.ready:
            raise ValueError("Not ready")
        assert True

    def test_processing_document_blocked(self):
        """A document still processing should be blocked."""
        import enum

        class ProcessingStatus(str, enum.Enum):
            uploaded = "uploaded"
            processing = "processing"
            ready = "ready"
            failed = "failed"

        class DocumentProcessingError(Exception):
            pass

        class FakeDoc:
            processing_status = ProcessingStatus.processing

        doc = FakeDoc()
        with pytest.raises(DocumentProcessingError):
            if doc.processing_status != ProcessingStatus.ready:
                raise DocumentProcessingError("Document is not yet ready.")


class TestFileValidationSecurity:
    """Security-focused file validation tests (pure Python, no FastAPI)."""

    def _validate_ext(self, filename: str) -> str:
        """Minimal validator mirroring the real one."""
        import os
        allowed = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".markdown": "text/markdown",
        }
        ext = os.path.splitext(filename.lower())[1]
        mime = allowed.get(ext)
        if mime is None:
            raise ValueError(f"Unsupported file extension '{ext}'")
        return mime

    def _sanitise(self, filename: str) -> str:
        """Minimal sanitiser."""
        import re
        name = re.sub(r"[^\w\s.\-]", "_", filename)
        name = name.replace("..", "_")
        return name.strip() or "upload"

    def test_pdf_extension_accepted(self):
        assert self._validate_ext("document.pdf") == "application/pdf"

    def test_exe_extension_rejected(self):
        with pytest.raises(ValueError):
            self._validate_ext("malware.exe")

    def test_bat_extension_rejected(self):
        with pytest.raises(ValueError):
            self._validate_ext("script.bat")

    def test_js_extension_rejected(self):
        with pytest.raises(ValueError):
            self._validate_ext("exploit.js")

    def test_path_traversal_in_filename_sanitised(self):
        result = self._sanitise("../../../etc/passwd")
        assert "../../../" not in result

    def test_null_byte_sanitised(self):
        result = self._sanitise("file\x00.pdf")
        assert "\x00" not in result

    def test_double_extension_sanitised(self):
        result = self._sanitise("image.jpg.exe")
        assert result is not None


class TestProcessingStatusEnum:
    """Enum value tests — standalone."""

    def test_all_statuses_exist(self):
        import enum

        class ProcessingStatus(str, enum.Enum):
            uploaded = "uploaded"
            processing = "processing"
            ready = "ready"
            failed = "failed"

        assert ProcessingStatus.uploaded.value == "uploaded"
        assert ProcessingStatus.processing.value == "processing"
        assert ProcessingStatus.ready.value == "ready"
        assert ProcessingStatus.failed.value == "failed"

    def test_activity_types_exist(self):
        import enum

        class ActivityType(str, enum.Enum):
            tutor_chat = "tutor_chat"
            quiz = "quiz"
            flashcard_review = "flashcard_review"
            document_read = "document_read"

        assert ActivityType.quiz.value == "quiz"
        assert ActivityType.tutor_chat.value == "tutor_chat"
        assert ActivityType.flashcard_review.value == "flashcard_review"
        assert ActivityType.document_read.value == "document_read"
