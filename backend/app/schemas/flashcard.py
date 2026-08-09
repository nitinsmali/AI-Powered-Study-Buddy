from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FlashcardGenerateRequest(BaseModel):
    document_id: str
    card_count: int = Field(default=15, ge=5, le=50)
    topic_focus: Optional[str] = Field(
        default=None,
        description="Optional topic area to focus the flashcard generation on.",
    )


class FlashcardResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    document_id: Optional[str] = None
    topic_id: Optional[str] = None
    front: str
    back: str
    ease_factor: float
    interval_days: int
    repetitions: int
    next_review_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class FlashcardBatchResponse(BaseModel):
    success: bool = True
    data: List[FlashcardResponse]
    total: int


class FlashcardUpdateRequest(BaseModel):
    """Used when a user rates a flashcard after review (spaced repetition)."""

    quality: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "SM-2 quality rating: 0=complete blackout, 5=perfect response."
        ),
    )
