from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TopicPerformanceResponse(BaseModel):
    topic_id: str
    topic_name: str
    mastery_score: float
    quizzes_taken: int
    flashcards_reviewed: int
    correct_rate: float  # 0.0 – 1.0


class StudyStreakResponse(BaseModel):
    current_streak_days: int
    longest_streak_days: int
    last_study_date: Optional[datetime] = None


class AnalyticsSummaryResponse(BaseModel):
    total_documents: int
    total_quizzes_taken: int
    total_flashcards_reviewed: int
    total_study_time_seconds: int
    average_quiz_score: float
    topics_covered: int
    weak_topics: List[TopicPerformanceResponse]
    strong_topics: List[TopicPerformanceResponse]
    study_streak: StudyStreakResponse
    recent_activity: List[dict]
