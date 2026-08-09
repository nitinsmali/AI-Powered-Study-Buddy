"""Document routes — upload, list, get, delete."""
from __future__ import annotations

import os
import uuid
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import (
    AuthorizationError,
    DocumentProcessingError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.document import Document, ProcessingStatus
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import process_document
from app.services.session_service import log_activity
from app.models.study_session import ActivityType
from app.utils.validators import sanitise_filename

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate MIME type
    content_type = file.content_type or ""
    # Allow text/plain for .md files browsers may send incorrectly
    if content_type not in ALLOWED_MIME_TYPES:
        # Fallback: check extension
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext in (".md", ".markdown"):
            content_type = "text/markdown"
        else:
            raise ValidationError(
                f"Unsupported file type: {content_type}. "
                f"Allowed: PDF, DOCX, TXT, Markdown."
            )

    # Read into memory to check size before writing
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise ValidationError(
            f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB."
        )

    # Persist to storage path with a safe UUID-based filename
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "file")[1].lower()
    safe_ext = ext if ext in (".pdf", ".docx", ".txt", ".md", ".markdown") else ".bin"
    file_path = os.path.join(settings.STORAGE_PATH, f"{file_id}{safe_ext}")

    try:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
    except OSError as exc:
        raise StorageError(f"Could not save file: {exc}") from exc

    safe_filename = sanitise_filename(file.filename or "upload")
    doc = Document(
        user_id=current_user.id,
        title=title or os.path.splitext(safe_filename)[0],
        original_filename=safe_filename,
        file_path=file_path,
        mime_type=content_type,
        file_size=len(content),
        processing_status=ProcessingStatus.uploaded,
    )
    db.add(doc)
    await db.flush()

    # Log study session
    await log_activity(
        db, current_user.id, ActivityType.document_read,
        duration_seconds=0, document_id=doc.id,
        notes=f"Uploaded document: {doc.title}"
    )

    logger.info("Document uploaded: %s by user %s", doc.id, current_user.id)

    # Trigger background text extraction
    doc_id = doc.id
    background_tasks.add_task(process_document, doc_id)

    return {
        "success": True,
        "data": DocumentResponse.model_validate(doc).model_dump(),
    }


@router.get(
    "",
    response_model=dict,
    summary="List all documents for the current user",
)
async def list_documents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    docs = result.scalars().all()
    return {
        "success": True,
        "data": [DocumentResponse.model_validate(d).model_dump() for d in docs],
        "total": len(docs),
    }


@router.get(
    "/{document_id}",
    response_model=dict,
    summary="Get a single document",
)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_owned_doc(document_id, current_user.id, db)
    return {"success": True, "data": DocumentResponse.model_validate(doc).model_dump()}


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document",
)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_owned_doc(document_id, current_user.id, db)

    # Remove the physical file
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError as exc:
            logger.warning("Could not delete file %s: %s", doc.file_path, exc)

    await db.delete(doc)
    return {"success": True, "message": "Document deleted."}


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_owned_doc(
    document_id: str, user_id: str, db: AsyncSession
) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError(f"Document {document_id} not found.")
    if doc.user_id != user_id:
        raise AuthorizationError("You do not own this document.")
    return doc
