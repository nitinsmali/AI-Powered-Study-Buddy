"""
Learning progress service.

Updates topic mastery scores when users complete quizzes or review flashcards.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.learning_progress import LearningProgress
from app.models.topic import Topic

logger = get_logger(__name__)


async def get_or_create_topic(
    db: AsyncSession, user_id: str, topic_name: str, document_id: Optional[str] = None
) -> Topic:
    """Find an existing topic by name for this user, or create one."""
    result = await db.execute(
        select(Topic).where(
            Topic.user_id == user_id,
            Topic.name == topic_name,
        )
    )
    topic = result.scalar_one_or_none()
    if topic is None:
        topic = Topic(
            user_id=user_id,
            name=topic_name,
            document_id=document_id,
        )
        db.add(topic)
        await db.flush()
    return topic


async def get_or_create_progress(
    db: AsyncSession, user_id: str, topic_id: str
) -> LearningProgress:
    """Find existing progress record or create one."""
    result = await db.execute(
        select(LearningProgress).where(
            LearningProgress.user_id == user_id,
            LearningProgress.topic_id == topic_id,
        )
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = LearningProgress(
            user_id=user_id,
            topic_id=topic_id,
        )
        db.add(progress)
        await db.flush()
    return progress


async def record_quiz_result(
    db: AsyncSession,
    user_id: str,
    topic_name: str,
    correct: int,
    total: int,
    document_id: Optional[str] = None,
) -> LearningProgress:
    """
    Update learning progress after a quiz attempt.

    Mastery is a weighted moving average that nudges towards the quiz score:
      new_mastery = 0.7 * old_mastery + 0.3 * quiz_score
    """
    if total == 0:
        raise ValueError("total must be > 0")

    topic = await get_or_create_topic(db, user_id, topic_name, document_id)
    progress = await get_or_create_progress(db, user_id, topic.id)

    quiz_score = (correct / total) * 100

    if progress.total_answers == 0:
        # First attempt — set mastery directly
        new_mastery = quiz_score
    else:
        new_mastery = 0.7 * progress.mastery_score + 0.3 * quiz_score

    progress.mastery_score = round(new_mastery, 2)
    progress.quizzes_taken += 1
    progress.correct_answers += correct
    progress.total_answers += total
    progress.last_activity_at = datetime.now(timezone.utc)

    await db.flush()
    logger.debug(
        "Learning progress updated: user=%s topic=%s mastery=%.1f%%",
        user_id,
        topic_name,
        progress.mastery_score,
    )
    return progress


async def record_flashcard_review(
    db: AsyncSession,
    user_id: str,
    topic_name: str,
    quality: int,
    document_id: Optional[str] = None,
) -> LearningProgress:
    """
    Update learning progress after a flashcard review.
    quality: 0–5 (SM-2 scale). 3+ = correct recall.
    """
    topic = await get_or_create_topic(db, user_id, topic_name, document_id)
    progress = await get_or_create_progress(db, user_id, topic.id)

    progress.flashcards_reviewed += 1

    is_correct = quality >= 3
    if is_correct:
        progress.correct_answers += 1
    progress.total_answers += 1

    # Light mastery bump from flashcard review
    if is_correct:
        progress.mastery_score = min(100, progress.mastery_score + 1.0)
    else:
        progress.mastery_score = max(0, progress.mastery_score - 0.5)

    progress.mastery_score = round(progress.mastery_score, 2)
    progress.last_activity_at = datetime.now(timezone.utc)

    await db.flush()
    return progress


def calculate_mastery_label(score: float) -> str:
    """Return a human-readable mastery level label."""
    if score >= 85:
        return "Strong"
    elif score >= 65:
        return "Good"
    elif score >= 45:
        return "Developing"
    elif score >= 25:
        return "Weak"
    else:
        return "Not started"
