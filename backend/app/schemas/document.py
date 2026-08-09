from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.document import ProcessingStatus


class DocumentCreate(BaseModel):
    title: str
    original_filename: str
    file_path: str
    mime_type: str
    file_size: int
    page_count: Optional[int] = None


class DocumentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    title: str
    original_filename: str
    mime_type: str
    file_size: int
    page_count: Optional[int] = None
    processing_status: ProcessingStatus
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    success: bool = True
    data: List[DocumentResponse]
    total: int
