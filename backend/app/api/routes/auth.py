"""Auth routes — sync Clerk user to local DB."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/sync",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Sync Clerk user to the local database",
)
async def sync_user(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the frontend immediately after sign-in / sign-up.
    Creates the user record if it does not yet exist, otherwise returns the
    existing record.  The Clerk JWT must be provided as a Bearer token.
    """
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()

    created = False
    if user is None:
        # We don't have profile info here beyond the clerk_user_id;
        # the frontend should call this with the full profile or update later.
        user = User(
            clerk_user_id=clerk_user_id,
            email=f"{clerk_user_id}@placeholder.local",
            name="Study Buddy User",
        )
        db.add(user)
        await db.flush()
        created = True

    return {
        "success": True,
        "data": {
            "id": user.id,
            "clerk_user_id": user.clerk_user_id,
            "email": user.email,
            "name": user.name,
            "created": created,
        },
    }


@router.post(
    "/sync/profile",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Sync full Clerk profile (email, name, avatar) to local DB",
)
async def sync_user_profile(
    payload: dict,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upserts user profile data from Clerk into the local database.
    Payload: { email, name, avatar_url? }
    """
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()

    email = payload.get("email", "")
    name = payload.get("name", "Study Buddy User")
    avatar_url = payload.get("avatar_url")

    if user is None:
        user = User(
            clerk_user_id=clerk_user_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
        db.add(user)
    else:
        if email:
            user.email = email
        user.name = name
        user.avatar_url = avatar_url

    await db.flush()

    return {
        "success": True,
        "data": UserResponse.model_validate(user).model_dump(),
    }
