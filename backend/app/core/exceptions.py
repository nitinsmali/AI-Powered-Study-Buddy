from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


# ── Base exception ────────────────────────────────────────────────────────────

class StudyBuddyException(Exception):
    """Base exception for all application-level errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


# ── Concrete exceptions ───────────────────────────────────────────────────────

class NotFoundError(StudyBuddyException):
    status_code = 404
    error_code = "NOT_FOUND"
    default_message = "The requested resource was not found."


class AuthorizationError(StudyBuddyException):
    status_code = 403
    error_code = "AUTHORIZATION_ERROR"
    default_message = "You do not have permission to perform this action."


class AuthenticationError(StudyBuddyException):
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    default_message = "Authentication is required."


class ValidationError(StudyBuddyException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    default_message = "The provided data is invalid."


class DocumentProcessingError(StudyBuddyException):
    status_code = 422
    error_code = "DOCUMENT_PROCESSING_ERROR"
    default_message = "Failed to process the document."


class AIServiceError(StudyBuddyException):
    status_code = 502
    error_code = "AI_SERVICE_ERROR"
    default_message = "The AI service encountered an error."


class StorageError(StudyBuddyException):
    status_code = 500
    error_code = "STORAGE_ERROR"
    default_message = "A storage error occurred."


class RateLimitError(StudyBuddyException):
    status_code = 429
    error_code = "RATE_LIMIT_ERROR"
    default_message = "Too many requests. Please slow down."


class ConflictError(StudyBuddyException):
    status_code = 409
    error_code = "CONFLICT_ERROR"
    default_message = "The resource already exists."


# ── Response helpers ──────────────────────────────────────────────────────────

def _error_response(error_code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
            },
        },
    )


# ── Global exception handlers ─────────────────────────────────────────────────

async def study_buddy_exception_handler(
    request: Request, exc: StudyBuddyException
) -> JSONResponse:
    return _error_response(exc.error_code, exc.message, exc.status_code)


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return _error_response("VALIDATION_ERROR", str(exc), 422)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    logger.exception("Unhandled exception: %s", exc)
    return _error_response(
        "INTERNAL_ERROR",
        "An unexpected error occurred. Please try again later.",
        500,
    )


def register_exception_handlers(app) -> None:  # noqa: ANN001
    """Attach all custom exception handlers to a FastAPI application."""
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse as _JSONResponse

    app.add_exception_handler(StudyBuddyException, study_buddy_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    @app.exception_handler(RequestValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> _JSONResponse:
        errors = exc.errors()
        message = "; ".join(
            f"{' -> '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in errors
        )
        return _error_response("VALIDATION_ERROR", message, 422)
