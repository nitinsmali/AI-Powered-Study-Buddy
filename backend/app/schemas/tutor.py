from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class TutorChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    mode: str = Field(
        default="explain",
        description=(
            "Tutor mode: explain | quiz_me | summarize | deep_dive | "
            "exam_prep | socratic"
        ),
    )
    document_id: Optional[str] = Field(
        default=None,
        description="If provided, the tutor will use the document's extracted text as context.",
    )
    conversation_history: List[ConversationMessage] = Field(
        default_factory=list,
        max_length=50,
        description="Previous turns in the conversation (oldest first).",
    )


class TutorChatResponse(BaseModel):
    success: bool = True
    data: dict  # {"reply": str, "mode": str, "document_context_used": bool}
