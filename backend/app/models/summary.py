from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class SummaryType(str, enum.Enum):
    quick = "quick"
    detailed = "detailed"
    bullet_points = "bullet_points"
    exam_revision = "exam_revision"
    simple_explanation = "simple_explanation"


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary_type: Mapped[SummaryType] = mapped_column(
        Enum(SummaryType), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="summaries")  # noqa: F821
    document: Mapped["Document"] = relationship("Document", back_populates="summaries")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Summary id={self.id!r} type={self.summary_type} doc={self.document_id!r}>"
