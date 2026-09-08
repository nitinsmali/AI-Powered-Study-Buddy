"""Quiz generation and attempt routes."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import (
    AIServiceError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.document import Document, ProcessingStatus
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAnswer, QuizAttempt
from app.models.quiz_question import QuizQuestion
from app.models.study_session import ActivityType
from app.models.user import User
from app.schemas.quiz import (
    QuizAttemptRequest,
    QuizAttemptResponse,
    QuizGenerateRequest,
    QuizQuestionResponse,
    QuizResponse,
)
from app.services.learning_service import record_quiz_result
from app.services.session_service import log_activity

router = APIRouter(prefix="/quizzes", tags=["quizzes"])
logger = get_logger(__name__)


@router.post(
    "/generate",
    response_model=dict,
    summary="Generate a new quiz from a document",
)
async def generate_quiz(
    request: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_ready_doc(request.document_id, current_user.id, db)

    raw_questions = await _call_llm_quiz(
        doc.extracted_text or "",
        request.question_count,
        request.difficulty.value,
        request.topic_focus,
    )

    quiz = Quiz(
        user_id=current_user.id,
        document_id=doc.id,
        title=request.title or f"Quiz on {doc.title}",
        difficulty=request.difficulty,
        question_count=len(raw_questions),
    )
    db.add(quiz)
    await db.flush()

    for idx, q in enumerate(raw_questions):
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text=q["question"],
            options=json.dumps(q["options"]),
            correct_answer=q["correct_answer"],
            explanation=q.get("explanation"),
            order_index=idx,
        )
        db.add(question)

    await db.flush()

    # Reload with questions
    result = await db.execute(
        select(Quiz).where(Quiz.id == quiz.id)
    )
    quiz = result.scalar_one()

    q_result = await db.execute(
        select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.order_index)
    )
    questions = q_result.scalars().all()

    return {
        "success": True,
        "data": {
            **QuizResponse.model_validate(quiz).model_dump(exclude={"questions"}),
            "questions": [QuizQuestionResponse.model_validate(q).model_dump() for q in questions],
        },
    }


@router.get(
    "",
    response_model=dict,
    summary="List all quizzes for the current user",
)
async def list_quizzes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Quiz)
        .where(Quiz.user_id == current_user.id)
        .order_by(Quiz.created_at.desc())
    )
    quizzes = result.scalars().all()
    return {
        "success": True,
        "data": [QuizResponse.model_validate(q).model_dump(exclude={"questions"}) for q in quizzes],
    }


@router.get(
    "/{quiz_id}",
    response_model=dict,
    summary="Get a quiz with all questions",
)
async def get_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quiz, questions = await _get_owned_quiz_with_questions(quiz_id, current_user.id, db)
    return {
        "success": True,
        "data": {
            **QuizResponse.model_validate(quiz).model_dump(exclude={"questions"}),
            "questions": [QuizQuestionResponse.model_validate(q).model_dump() for q in questions],
        },
    }


@router.post(
    "/{quiz_id}/attempt",
    response_model=dict,
    summary="Submit a quiz attempt",
)
async def submit_attempt(
    quiz_id: str,
    request: QuizAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quiz, questions = await _get_owned_quiz_with_questions(quiz_id, current_user.id, db)

    question_map = {q.id: q for q in questions}

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        total_questions=len(questions),
        time_taken_seconds=request.time_taken_seconds,
    )
    db.add(attempt)
    await db.flush()

    correct = 0
    for answer_item in request.answers:
        q = question_map.get(answer_item.question_id)
        if q is None:
            continue
        is_correct = answer_item.selected_answer.strip() == q.correct_answer.strip()
        if is_correct:
            correct += 1
        answer = QuizAnswer(
            attempt_id=attempt.id,
            question_id=answer_item.question_id,
            selected_answer=answer_item.selected_answer,
            is_correct=is_correct,
        )
        db.add(answer)

    attempt.correct_answers = correct
    attempt.score = round((correct / len(questions)) * 100, 2) if questions else 0.0
    attempt.completed = True
    attempt.completed_at = datetime.now(timezone.utc)

    await db.flush()

    # Update learning progress for this topic
    topic_name = quiz.title or "General"
    try:
        await record_quiz_result(
            db,
            user_id=current_user.id,
            topic_name=topic_name,
            correct=correct,
            total=len(questions),
            document_id=quiz.document_id,
        )
    except Exception as exc:
        logger.warning("Could not update learning progress: %s", exc)

    # Log study session
    try:
        await log_activity(
            db,
            user_id=current_user.id,
            activity_type=ActivityType.quiz,
            duration_seconds=request.time_taken_seconds or 0,
            document_id=quiz.document_id,
            notes=f"Completed quiz: {quiz.title} — score {attempt.score:.0f}%",
        )
    except Exception as exc:
        logger.warning("Could not log study session: %s", exc)

    return {
        "success": True,
        "data": QuizAttemptResponse.model_validate(attempt).model_dump(),
    }


@router.delete("/{quiz_id}", summary="Delete a quiz")
async def delete_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise NotFoundError(f"Quiz {quiz_id} not found.")
    if quiz.user_id != current_user.id:
        raise AuthorizationError("You do not own this quiz.")
    await db.delete(quiz)
    return {"success": True, "message": "Quiz deleted."}


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_owned_quiz_with_questions(
    quiz_id: str, user_id: str, db: AsyncSession
):
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise NotFoundError(f"Quiz {quiz_id} not found.")
    if quiz.user_id != user_id:
        raise AuthorizationError("You do not own this quiz.")
    q_result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz.id)
        .order_by(QuizQuestion.order_index)
    )
    questions = q_result.scalars().all()
    return quiz, questions


async def _get_ready_doc(doc_id: str, user_id: str, db: AsyncSession) -> Document:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError(f"Document {doc_id} not found.")
    if doc.user_id != user_id:
        raise AuthorizationError("You do not own this document.")
    if doc.processing_status != ProcessingStatus.ready:
        from app.core.exceptions import DocumentProcessingError
        raise DocumentProcessingError("Document is not yet ready. Please wait.")
    return doc


async def _call_llm_quiz(
    text: str, count: int, difficulty: str, topic_focus: str | None
) -> list[dict]:
    import pathlib

    from openai import AsyncOpenAI

    from app.core.config import settings

    prompt_path = (
        pathlib.Path(__file__).parent.parent.parent / "prompts" / "quiz_generation.txt"
    )
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = "You are an expert quiz generator. Return JSON only."

    client_kwargs: dict = {"api_key": settings.LLM_API_KEY}
    if settings.LLM_BASE_URL:
        client_kwargs["base_url"] = settings.LLM_BASE_URL
    client = AsyncOpenAI(**client_kwargs)

    topic_line = f"\nFocus on topic: {topic_focus}" if topic_focus else ""
    user_message = (
        f"Generate exactly {count} questions at {difficulty} difficulty.{topic_line}\n\n"
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
        questions = parsed.get("questions", []) if isinstance(parsed, dict) else parsed
        if not isinstance(questions, list) or not questions:
            raise ValueError("The AI returned no quiz questions.")

        validated: list[dict] = []
        for question in questions:
            if not isinstance(question, dict):
                raise ValueError("The AI returned an invalid quiz question.")
            text = question.get("question")
            options = question.get("options")
            answer = question.get("correct_answer")
            if (
                not isinstance(text, str)
                or not text.strip()
                or not isinstance(options, list)
                or len(options) < 2
                or not all(isinstance(option, str) and option.strip() for option in options)
                or not isinstance(answer, str)
                or not answer.strip()
            ):
                raise ValueError("The AI returned an incomplete quiz question.")
            validated.append(
                {
                    "question": text.strip(),
                    "options": [option.strip() for option in options],
                    "correct_answer": answer.strip(),
                    "explanation": question.get("explanation"),
                }
            )
        return validated
    except Exception as exc:
        logger.error("Quiz LLM error: %s", exc)
        raise AIServiceError(f"Failed to generate quiz: {exc}") from exc
