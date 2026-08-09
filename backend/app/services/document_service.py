"""
Document processing service.

Handles text extraction from uploaded files as a background task.
The processing is invoked via FastAPI BackgroundTasks so it does not
block the upload response.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.document import Document, ProcessingStatus
from app.utils.pdf_parser import extract_text_from_file

logger = get_logger(__name__)


async def process_document(document_id: str) -> None:
    """
    Background task: extract text from an uploaded document and update its status.

    This function creates its own DB session because it runs outside the
    request/response lifecycle.
    """
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if doc is None:
                logger.error("process_document: document %s not found", document_id)
                return

            # Mark as processing
            doc.processing_status = ProcessingStatus.processing
            await db.commit()

            # Extract text
            text, page_count = extract_text_from_file(doc.file_path, doc.mime_type)

            # Update document
            doc.extracted_text = text
            doc.page_count = page_count
            doc.processing_status = ProcessingStatus.ready
            await db.commit()

            logger.info(
                "Document %s processed: %d pages, %d chars",
                document_id,
                page_count,
                len(text),
            )

        except ValueError as exc:
            logger.error("Document %s processing failed: %s", document_id, exc)
            async with AsyncSessionLocal() as err_db:
                result = await err_db.execute(
                    select(Document).where(Document.id == document_id)
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.processing_status = ProcessingStatus.failed
                    await err_db.commit()
        except Exception as exc:
            logger.error(
                "Unexpected error processing document %s: %s", document_id, exc
            )
            async with AsyncSessionLocal() as err_db:
                result = await err_db.execute(
                    select(Document).where(Document.id == document_id)
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.processing_status = ProcessingStatus.failed
                    await err_db.commit()
