"""
Study session logging service.

Creates and closes study sessions when users perform learning activities.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study_session import ActivityType, StudySession
from app.core.logging import get_logger

logger = get_logger(__name__)


async def start_session(
    db: AsyncSession,
    user_id: str,
    activity_type: ActivityType,
    document_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> StudySession:
    """Create a new study session record."""
    session = StudySession(
        user_id=user_id,
        activity_type=activity_type,
        document_id=document_id,
        topic_id=topic_id,
        notes=notes,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()
    logger.debug(
        "Study session started: user=%s type=%s", user_id, activity_type.value
    )
    return session


async def end_session(
    db: AsyncSession, session_id: str, duration_seconds: Optional[int] = None
) -> None:
    """Mark a study session as ended."""
    from sqlalchemy import select

    result = await db.execute(
        select(StudySession).where(StudySession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session:
        session.ended_at = datetime.now(timezone.utc)
        if duration_seconds is not None:
            session.duration_seconds = duration_seconds
        elif session.started_at:
            delta = session.ended_at - session.started_at
            session.duration_seconds = int(delta.total_seconds())
        await db.flush()


async def log_activity(
    db: AsyncSession,
    user_id: str,
    activity_type: ActivityType,
    duration_seconds: int = 0,
    document_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> StudySession:
    """Log a completed activity in one call (start + immediate end)."""
    now = datetime.now(timezone.utc)
    session = StudySession(
        user_id=user_id,
        activity_type=activity_type,
        document_id=document_id,
        topic_id=topic_id,
        notes=notes,
        duration_seconds=duration_seconds,
        started_at=now,
        ended_at=now,
    )
    db.add(session)
    await db.flush()
    return session
