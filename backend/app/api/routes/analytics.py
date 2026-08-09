"""Analytics routes — study stats and performance overview."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.document import Document
from app.models.flashcard import Flashcard
from app.models.learning_progress import LearningProgress
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.study_session import StudySession
from app.models.topic import Topic
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    StudyStreakResponse,
    TopicPerformanceResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = get_logger(__name__)


@router.get(
    "/summary",
    response_model=dict,
    summary="Get overall analytics summary for the current user",
)
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id

    # ── Aggregate counts ───────────────────────────────────────────────────────
    doc_count = await _count(db, Document, Document.user_id == user_id)
    quiz_count = await _count(db, QuizAttempt, QuizAttempt.user_id == user_id, QuizAttempt.completed == True)  # noqa: E712
    flashcard_count = await _scalar(
        db,
        select(func.sum(LearningProgress.flashcards_reviewed)).where(
            LearningProgress.user_id == user_id
        ),
    ) or 0

    study_time = await _scalar(
        db,
        select(func.sum(StudySession.duration_seconds)).where(
            StudySession.user_id == user_id
        ),
    ) or 0

    avg_score = await _scalar(
        db,
        select(func.avg(QuizAttempt.score)).where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.completed == True,  # noqa: E712
        ),
    ) or 0.0

    # ── Topic performance ─────────────────────────────────────────────────────
    progress_result = await db.execute(
        select(LearningProgress, Topic)
        .join(Topic, LearningProgress.topic_id == Topic.id)
        .where(LearningProgress.user_id == user_id)
        .order_by(LearningProgress.mastery_score.asc())
    )
    rows = progress_result.all()

    all_topic_perf = [
        TopicPerformanceResponse(
            topic_id=lp.topic_id,
            topic_name=t.name,
            mastery_score=lp.mastery_score,
            quizzes_taken=lp.quizzes_taken,
            flashcards_reviewed=lp.flashcards_reviewed,
            correct_rate=(lp.correct_answers / lp.total_answers) if lp.total_answers > 0 else 0.0,
        )
        for lp, t in rows
    ]

    weak_topics = all_topic_perf[:3]
    strong_topics = list(reversed(all_topic_perf))[:3]

    # ── Study streak ─────────────────────────────────────────────────────────
    streak = await _compute_streak(db, user_id)

    # ── Recent activity ───────────────────────────────────────────────────────
    session_result = await db.execute(
        select(StudySession)
        .where(StudySession.user_id == user_id)
        .order_by(StudySession.started_at.desc())
        .limit(10)
    )
    recent_sessions = session_result.scalars().all()
    recent_activity = [
        {
            "id": s.id,
            "activity_type": s.activity_type.value,
            "started_at": s.started_at.isoformat(),
            "duration_seconds": s.duration_seconds,
        }
        for s in recent_sessions
    ]

    response = AnalyticsSummaryResponse(
        total_documents=doc_count,
        total_quizzes_taken=quiz_count,
        total_flashcards_reviewed=flashcard_count,
        total_study_time_seconds=int(study_time),
        average_quiz_score=round(float(avg_score), 2),
        topics_covered=len(rows),
        weak_topics=weak_topics,
        strong_topics=strong_topics,
        study_streak=streak,
        recent_activity=recent_activity,
    )

    return {"success": True, "data": response.model_dump()}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _count(db: AsyncSession, model, *conditions) -> int:
    result = await db.execute(
        select(func.count()).select_from(model).where(*conditions)
    )
    return result.scalar_one() or 0


async def _scalar(db: AsyncSession, stmt):
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _compute_streak(db: AsyncSession, user_id: str) -> StudyStreakResponse:
    result = await db.execute(
        select(func.date(StudySession.started_at).label("day"))
        .where(StudySession.user_id == user_id)
        .group_by(func.date(StudySession.started_at))
        .order_by(func.date(StudySession.started_at).desc())
    )
    days = [row[0] for row in result.all()]

    if not days:
        return StudyStreakResponse(current_streak_days=0, longest_streak_days=0)

    today = datetime.now(timezone.utc).date()
    current = 0
    longest = 0
    prev = None

    for day in days:
        if prev is None:
            # Must be today or yesterday to count
            if (today - day).days <= 1:
                current = 1
            prev = day
            longest = current
            continue
        if (prev - day).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            # Streak broken; keep counting longest
            if current > longest:
                longest = current
            current = 1
        prev = day

    return StudyStreakResponse(
        current_streak_days=current,
        longest_streak_days=longest,
        last_study_date=datetime.combine(days[0], datetime.min.time(), tzinfo=timezone.utc),
    )
