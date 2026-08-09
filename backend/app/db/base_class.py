"""
SQLAlchemy DeclarativeBase — imported by all model files.
Keep this module import-free of model classes to avoid circular imports.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
