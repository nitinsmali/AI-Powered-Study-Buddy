"""Flashcard generation and review routes."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AIServiceError, AuthorizationError, NotFoundError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.document import Document, ProcessingStatus
from app.models.flashcard import Flashcard
from app.models.study_session import ActivityType
from app.models.user import User
from app.schemas.flashcard import (
    FlashcardBatchResponse,
    FlashcardGenerateRequest,
    FlashcardResponse,
    FlashcardUpdateRequest,
)
from app.services.learning_service import record_flashcard_review
from app.services.session_service import log_activity

router = APIRouter(prefix="/flashcards", tags=["flashcards"])
logger = get_logger(__name__)


@router.post(
    "/generate",
    response_model=dict,
    summary="Generate flashcards from a document",
)
async def generate_flashcards(
    request: FlashcardGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_ready_doc(request.document_id, current_user.id, db)
    raw_cards = await _call_llm_flashcards(
        doc.extracted_text or "", request.card_count, request.topic_focus
    )

    cards = []
    for raw in raw_cards:
        card = Flashcard(
            user_id=current_user.id,
            document_id=doc.id,
            front=raw.get("front", ""),
            back=raw.get("back", ""),
            next_review_at=datetime.now(timezone.utc),
        )
        db.add(card)
        cards.append(card)

    await db.flush()

    return {
        "success": True,
        "data": [FlashcardResponse.model_validate(c).model_dump() for c in cards],
        "total": len(cards),
    }


@router.get(
    "",
    response_model=dict,
    summary="List flashcards for the current user",
)
async def list_flashcards(
    document_id: str | None = Query(default=None),
    due_only: bool = Query(default=False, description="Return only cards due for review"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Flashcard).where(Flashcard.user_id == current_user.id)
    if document_id:
        q = q.where(Flashcard.document_id == document_id)
    if due_only:
        now = datetime.now(timezone.utc)
        q = q.where((Flashcard.next_review_at == None) | (Flashcard.next_review_at <= now))  # noqa: E711
    q = q.order_by(Flashcard.next_review_at.asc().nullsfirst()).offset(skip).limit(limit)

    result = await db.execute(q)
    cards = result.scalars().all()
    return {
        "success": True,
        "data": [FlashcardResponse.model_validate(c).model_dump() for c in cards],
        "total": len(cards),
    }


@router.post(
    "/{flashcard_id}/review",
    response_model=dict,
    summary="Record a flashcard review (spaced repetition SM-2)",
)
async def review_flashcard(
    flashcard_id: str,
    update: FlashcardUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Flashcard).where(Flashcard.id == flashcard_id))
    card = result.scalar_one_or_none()
    if card is None:
        raise NotFoundError(f"Flashcard {flashcard_id} not found.")
    if card.user_id != current_user.id:
        raise AuthorizationError("You do not own this flashcard.")

    _apply_sm2(card, update.quality)
    await db.flush()

    # Update learning progress
    try:
        # Use topic name from card or fall back to "Flashcards"
        topic_name = "Flashcards"
        await record_flashcard_review(
            db,
            user_id=current_user.id,
            topic_name=topic_name,
            quality=update.quality,
            document_id=card.document_id,
        )
    except Exception as exc:
        logger.warning("Could not update flashcard learning progress: %s", exc)

    # Log study session activity
    try:
        await log_activity(
            db,
            user_id=current_user.id,
            activity_type=ActivityType.flashcard_review,
            duration_seconds=0,
            document_id=card.document_id,
            notes=f"Reviewed flashcard (quality: {update.quality}/5)",
        )
    except Exception as exc:
        logger.warning("Could not log flashcard session: %s", exc)

    return {"success": True, "data": FlashcardResponse.model_validate(card).model_dump()}


@router.delete("/{flashcard_id}", summary="Delete a flashcard")
async def delete_flashcard(
    flashcard_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Flashcard).where(Flashcard.id == flashcard_id))
    card = result.scalar_one_or_none()
    if card is None:
        raise NotFoundError(f"Flashcard {flashcard_id} not found.")
    if card.user_id != current_user.id:
        raise AuthorizationError("You do not own this flashcard.")
    await db.delete(card)
    return {"success": True, "message": "Flashcard deleted."}


# ── SM-2 algorithm ────────────────────────────────────────────────────────────

def _apply_sm2(card: Flashcard, quality: int) -> None:
    """Apply the SM-2 spaced repetition algorithm in-place."""
    q = max(0, min(5, quality))

    if q >= 3:
        if card.repetitions == 0:
            card.interval_days = 1
        elif card.repetitions == 1:
            card.interval_days = 6
        else:
            card.interval_days = round(card.interval_days * card.ease_factor)
        card.repetitions += 1
    else:
        card.repetitions = 0
        card.interval_days = 1

    card.ease_factor = max(
        1.3, card.ease_factor + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
    )
    card.next_review_at = datetime.now(timezone.utc) + timedelta(days=card.interval_days)


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
        raise DocumentProcessingError("Document is not yet ready.")
    return doc


async def _call_llm_flashcards(
    text: str, count: int, topic_focus: str | None
) -> list[dict]:
    import pathlib

    from openai import AsyncOpenAI

    from app.core.config import settings

    prompt_path = (
        pathlib.Path(__file__).parent.parent.parent / "prompts" / "flashcards.txt"
    )
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = 'Generate flashcards. Return JSON: {"cards":[{"front":"...","back":"..."}]}'

    client_kwargs: dict = {"api_key": settings.LLM_API_KEY}
    if settings.LLM_BASE_URL:
        client_kwargs["base_url"] = settings.LLM_BASE_URL
    client = AsyncOpenAI(**client_kwargs)

    topic_line = f"\nFocus on topic: {topic_focus}" if topic_focus else ""
    user_message = (
        f"Generate exactly {count} flashcards.{topic_line}\n\n"
        f"Document text:\n{text[:14_000]}"
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=4096,
            temperature=0.6,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        return parsed.get("cards", parsed) if isinstance(parsed, dict) else parsed
    except Exception as exc:
        logger.error("Flashcard LLM error: %s", exc)
        raise AIServiceError(f"Failed to generate flashcards: {exc}") from exc
