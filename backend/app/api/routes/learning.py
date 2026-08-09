"""Learning progress and recommendations routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AIServiceError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.learning_progress import LearningProgress
from app.models.topic import Topic
from app.models.user import User
from app.schemas.learning import (
    LearningProgressResponse,
    RecommendationItem,
    RecommendationResponse,
    RecommendationsListResponse,
)

router = APIRouter(prefix="/learning", tags=["learning"])
logger = get_logger(__name__)


@router.get(
    "/progress",
    response_model=dict,
    summary="Get learning progress across all topics",
)
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LearningProgress, Topic)
        .join(Topic, LearningProgress.topic_id == Topic.id)
        .where(LearningProgress.user_id == current_user.id)
        .order_by(LearningProgress.mastery_score.desc())
    )
    rows = result.all()

    data = []
    for progress, topic in rows:
        item = LearningProgressResponse.model_validate(progress)
        item.topic_name = topic.name
        data.append(item.model_dump())

    return {"success": True, "data": data}


@router.get(
    "/recommendations",
    response_model=dict,
    summary="Get personalized study recommendations",
)
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns rule-based recommendations without calling the LLM
    (Phase 1 stub — Phase 3 will add AI-powered recommendations).
    """
    # Find weak topics (mastery < 50)
    progress_result = await db.execute(
        select(LearningProgress, Topic)
        .join(Topic, LearningProgress.topic_id == Topic.id)
        .where(LearningProgress.user_id == current_user.id)
        .order_by(LearningProgress.mastery_score.asc())
        .limit(5)
    )
    rows = progress_result.all()

    recommendations = []
    for progress, topic in rows:
        if progress.mastery_score < 80:
            recommendations.append(
                RecommendationResponse(
                    item=RecommendationItem(
                        type="quiz",
                        title=f"Practice quiz on {topic.name}",
                        description=(
                            f"Your mastery score for {topic.name} is "
                            f"{progress.mastery_score:.0f}%. A focused quiz will help."
                        ),
                        action_url=f"/quizzes?topic={topic.id}",
                        priority=1 if progress.mastery_score < 40 else 2,
                    ),
                    reason=f"Low mastery score ({progress.mastery_score:.0f}%) on {topic.name}.",
                )
            )

    return {
        "success": True,
        "data": [r.model_dump() for r in recommendations],
    }
