from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    quizzes: Mapped[list["Quiz"]] = relationship("Quiz", back_populates="topic")  # noqa: F821
    flashcards: Mapped[list["Flashcard"]] = relationship("Flashcard", back_populates="topic")  # noqa: F821
    learning_progress: Mapped[list["LearningProgress"]] = relationship(  # noqa: F821
        "LearningProgress", back_populates="topic"
    )

    def __repr__(self) -> str:
        return f"<Topic id={self.id!r} name={self.name!r}>"
