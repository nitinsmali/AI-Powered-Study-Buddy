"""Summary generation routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AIServiceError, AuthorizationError, NotFoundError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.document import Document, ProcessingStatus
from app.models.summary import Summary
from app.models.user import User
from app.schemas.summary import SummaryRequest, SummaryResponse

router = APIRouter(prefix="/summaries", tags=["summaries"])
logger = get_logger(__name__)


@router.post(
    "",
    response_model=dict,
    summary="Generate a summary for a document",
)
async def generate_summary(
    request: SummaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_ready_doc(request.document_id, current_user.id, db)

    content = await _call_llm_summarize(doc.extracted_text or "", request.summary_type)
    word_count = len(content.split())

    summary = Summary(
        user_id=current_user.id,
        document_id=doc.id,
        summary_type=request.summary_type,
        content=content,
        word_count=word_count,
    )
    db.add(summary)
    await db.flush()

    return {
        "success": True,
        "data": SummaryResponse.model_validate(summary).model_dump(),
    }


@router.get(
    "",
    response_model=dict,
    summary="List all summaries for the current user",
)
async def list_summaries(
    document_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Summary).where(Summary.user_id == current_user.id)
    if document_id:
        q = q.where(Summary.document_id == document_id)
    q = q.order_by(Summary.created_at.desc())
    result = await db.execute(q)
    summaries = result.scalars().all()
    return {
        "success": True,
        "data": [SummaryResponse.model_validate(s).model_dump() for s in summaries],
    }


@router.get(
    "/{summary_id}",
    response_model=dict,
    summary="Get a single summary",
)
async def get_summary(
    summary_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Summary).where(Summary.id == summary_id)
    )
    summary = result.scalar_one_or_none()
    if summary is None:
        raise NotFoundError(f"Summary {summary_id} not found.")
    if summary.user_id != current_user.id:
        raise AuthorizationError("You do not own this summary.")
    return {"success": True, "data": SummaryResponse.model_validate(summary).model_dump()}


@router.delete("/{summary_id}", summary="Delete a summary")
async def delete_summary(
    summary_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Summary).where(Summary.id == summary_id)
    )
    summary = result.scalar_one_or_none()
    if summary is None:
        raise NotFoundError(f"Summary {summary_id} not found.")
    if summary.user_id != current_user.id:
        raise AuthorizationError("You do not own this summary.")
    await db.delete(summary)
    return {"success": True, "message": "Summary deleted."}


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_ready_doc(doc_id: str, user_id: str, db: AsyncSession) -> Document:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError(f"Document {doc_id} not found.")
    if doc.user_id != user_id:
        raise AuthorizationError("You do not own this document.")
    if doc.processing_status != ProcessingStatus.ready:
        from app.core.exceptions import DocumentProcessingError
        raise DocumentProcessingError(
            "Document is not yet processed. Please wait until status is 'ready'."
        )
    return doc


async def _call_llm_summarize(text: str, summary_type) -> str:
    import pathlib

    from openai import AsyncOpenAI

    from app.core.config import settings

    prompt_path = (
        pathlib.Path(__file__).parent.parent.parent / "prompts" / "summarization.txt"
    )
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = "You are an expert summarizer."

    client_kwargs: dict = {"api_key": settings.LLM_API_KEY}
    if settings.LLM_BASE_URL:
        client_kwargs["base_url"] = settings.LLM_BASE_URL
    client = AsyncOpenAI(**client_kwargs)

    truncated_text = text[:14_000]
    user_message = (
        f"Summary type: {summary_type.value}\n\n"
        f"Document text:\n{truncated_text}"
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=2048,
            temperature=0.5,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        logger.error("Summary LLM error: %s", exc)
        raise AIServiceError(f"Failed to generate summary: {exc}") from exc
