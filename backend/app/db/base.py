"""
SQLAlchemy declarative base + model imports for Alembic autogenerate.

All model modules are imported here so Alembic can discover every table.
Import order respects FK dependencies:
  users → documents → summaries / quizzes / flashcards / topics →
  learning_progress / study_sessions.
"""
from __future__ import annotations

# Re-export Base so other code can still do: from app.db.base import Base
from app.db.base_class import Base  # noqa: F401

# ── Import all models (order matters for FK resolution) ──────────────────────
from app.models.user import User  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.topic import Topic  # noqa: F401
from app.models.summary import Summary  # noqa: F401
from app.models.flashcard import Flashcard  # noqa: F401
from app.models.quiz import Quiz  # noqa: F401
from app.models.quiz_question import QuizQuestion  # noqa: F401
from app.models.quiz_attempt import QuizAttempt, QuizAnswer  # noqa: F401
from app.models.learning_progress import LearningProgress  # noqa: F401
from app.models.study_session import StudySession  # noqa: F401

__all__ = [
    "Base",
    "User",
    "Document",
    "Topic",
    "Summary",
    "Flashcard",
    "Quiz",
    "QuizQuestion",
    "QuizAttempt",
    "QuizAnswer",
    "LearningProgress",
    "StudySession",
]
