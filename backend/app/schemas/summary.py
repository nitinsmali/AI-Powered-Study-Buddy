from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.summary import SummaryType


class SummaryRequest(BaseModel):
    document_id: str
    summary_type: SummaryType = SummaryType.quick


class SummaryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    document_id: str
    user_id: str
    summary_type: SummaryType
    content: str
    word_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
