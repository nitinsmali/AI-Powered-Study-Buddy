"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.user import User


async def get_current_user(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return the DB User record for the authenticated Clerk user."""
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError(
            "User account not found. Please call POST /api/auth/sync first."
        )
    return user
