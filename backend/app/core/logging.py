from __future__ import annotations

import json
import logging
import sys
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


def _configure_logging(log_level: str, is_production: bool) -> None:
    """Configure root logger once at application startup."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    if is_production:
        # JSON formatter for structured log aggregation
        formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger; call after _configure_logging has been called."""
    return logging.getLogger(name)


def setup_logging() -> None:
    """Initialise logging from application settings."""
    from app.core.config import settings

    _configure_logging(settings.LOG_LEVEL, settings.is_production)


# ── Request logging middleware ────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status and duration."""

    def __init__(self, app, *, exclude_paths: list[str] | None = None):
        super().__init__(app)
        self._exclude = set(exclude_paths or ["/health", "/favicon.ico"])
        self._logger = get_logger("api.access")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self._exclude:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        self._logger.info(
            "%s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 1),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        return response
