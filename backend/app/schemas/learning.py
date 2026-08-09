from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LearningProgressResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    topic_id: str
    topic_name: Optional[str] = None  # populated via join
    mastery_score: float
    quizzes_taken: int
    flashcards_reviewed: int
    correct_answers: int
    total_answers: int
    last_activity_at: Optional[datetime] = None
    updated_at: datetime


class RecommendationItem(BaseModel):
    type: str  # "quiz" | "flashcard_review" | "document" | "topic"
    title: str
    description: str
    action_url: str
    priority: int  # 1 = highest


class RecommendationResponse(BaseModel):
    item: RecommendationItem
    reason: str


class RecommendationsListResponse(BaseModel):
    success: bool = True
    data: List[RecommendationResponse]
