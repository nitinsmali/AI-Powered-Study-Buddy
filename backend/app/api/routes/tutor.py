"""AI Tutor routes — chat with streaming SSE and regular JSON."""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AIServiceError, AuthorizationError, NotFoundError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.document import Document, ProcessingStatus
from app.models.study_session import ActivityType
from app.models.user import User
from app.schemas.tutor import TutorChatRequest
from app.services.session_service import log_activity

router = APIRouter(prefix="/tutor", tags=["tutor"])
logger = get_logger(__name__)

VALID_MODES = {"explain", "quiz_me", "summarize", "deep_dive", "exam_prep", "socratic"}


@router.post(
    "/chat",
    summary="Send a message to the AI tutor (streaming SSE)",
)
async def tutor_chat(
    request: TutorChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream an AI tutor response using Server-Sent Events.
    The client should read `data:` lines and accumulate them.
    A final `data: [DONE]` line signals completion.
    """
    if request.mode not in VALID_MODES:
        from app.core.exceptions import ValidationError
        raise ValidationError(
            f"Invalid mode '{request.mode}'. Choose from: {', '.join(sorted(VALID_MODES))}"
        )

    document_text: str | None = None
    doc_id: str | None = None
    if request.document_id:
        result = await db.execute(
            select(Document).where(Document.id == request.document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundError(f"Document {request.document_id} not found.")
        if doc.user_id != current_user.id:
            raise AuthorizationError("You do not own this document.")
        doc_id = doc.id
        if doc.processing_status == ProcessingStatus.ready:
            document_text = doc.extracted_text

    # Log tutor chat as a study session (background so it doesn't delay SSE)
    background_tasks.add_task(
        _log_tutor_session,
        current_user.id,
        doc_id,
        request.mode,
    )

    return StreamingResponse(
        _stream_tutor_response(request, document_text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _log_tutor_session(
    user_id: str, document_id: str | None, mode: str
) -> None:
    """Log a tutor chat as a study session in a new DB session."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            await log_activity(
                db,
                user_id=user_id,
                activity_type=ActivityType.tutor_chat,
                duration_seconds=0,
                document_id=document_id,
                notes=f"AI Tutor chat — mode: {mode}",
            )
            await db.commit()
        except Exception as exc:
            logger.warning("Could not log tutor session: %s", exc)


async def _stream_tutor_response(
    request: TutorChatRequest, document_text: str | None
) -> AsyncGenerator[str, None]:
    """Call the LLM and yield SSE-formatted chunks."""
    from app.core.config import settings
    from openai import AsyncOpenAI

    client_kwargs: dict = {"api_key": settings.LLM_API_KEY}
    if settings.LLM_BASE_URL:
        client_kwargs["base_url"] = settings.LLM_BASE_URL

    client = AsyncOpenAI(**client_kwargs)

    system_prompt = _build_system_prompt(request.mode, document_text)

    messages = [{"role": "system", "content": system_prompt}]
    for turn in request.conversation_history:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": request.message})

    try:
        stream = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            stream=True,
            max_tokens=2048,
            temperature=0.7,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield f"data: {delta}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        logger.error("LLM streaming error: %s", exc)
        yield f"data: [ERROR] {str(exc)}\n\n"


def _build_system_prompt(mode: str, document_text: str | None) -> str:
    """Read the base tutor prompt and inject mode + document context."""
    import pathlib

    prompt_path = pathlib.Path(__file__).parent.parent.parent / "prompts" / "tutor.txt"
    try:
        base_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        base_prompt = "You are a helpful AI study tutor."

    parts = [base_prompt, f"\n\nCurrent mode: {mode.upper()}"]
    if document_text:
        # Truncate to avoid exceeding context window
        truncated = document_text[:12_000]
        parts.append(
            f"\n\n--- DOCUMENT CONTEXT ---\n{truncated}\n--- END DOCUMENT CONTEXT ---"
        )
    return "\n".join(parts)
