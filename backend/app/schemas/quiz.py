from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.quiz import DifficultyLevel


class QuizGenerateRequest(BaseModel):
    document_id: str
    title: Optional[str] = None
    question_count: int = Field(default=10, ge=3, le=30)
    difficulty: DifficultyLevel = DifficultyLevel.mixed
    topic_focus: Optional[str] = Field(
        default=None, description="Optional topic to focus questions on."
    )


class QuizQuestionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    question_text: str
    options: str  # JSON string of list
    correct_answer: str
    explanation: Optional[str] = None
    order_index: int


class QuizResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    document_id: Optional[str] = None
    title: str
    difficulty: DifficultyLevel
    question_count: int
    questions: List[QuizQuestionResponse] = []
    created_at: datetime
    updated_at: datetime


class QuizAnswerItem(BaseModel):
    question_id: str
    selected_answer: str


class QuizAttemptRequest(BaseModel):
    answers: List[QuizAnswerItem]
    time_taken_seconds: Optional[int] = None


class QuizAttemptResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    quiz_id: str
    user_id: str
    score: Optional[float] = None
    total_questions: int
    correct_answers: Optional[int] = None
    time_taken_seconds: Optional[int] = None
    completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
