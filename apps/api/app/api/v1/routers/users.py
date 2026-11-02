"""User management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import get_db
from app.models.user import User, UserProfile
from app.schemas.user import UserDetailResponse, UserProfileResponse, UpdateProfileRequest
from app.schemas.common import SuccessResponse
from app.api.deps import get_current_active_user

router = APIRouter()


@router.get("/me", response_model=UserDetailResponse)
async def get_my_profile(user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    profile_resp = UserProfileResponse.model_validate(profile) if profile else None
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        profile=profile_resp,
    )


@router.patch("/me", response_model=SuccessResponse)
async def update_my_profile(
    data: UpdateProfileRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name:
        user.full_name = data.full_name

    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)

    for field in ["bio", "avatar_url", "website", "location", "creator_name"]:
        val = getattr(data, field)
        if val is not None:
            setattr(profile, field, val)

    await db.commit()
    return SuccessResponse(message="Profile updated")
