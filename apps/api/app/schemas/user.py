"""User schemas."""
from app.schemas.common import BaseSchema


class UserProfileResponse(BaseSchema):
    id: str
    bio: str | None = None
    avatar_url: str | None = None
    website: str | None = None
    location: str | None = None
    creator_name: str | None = None


class UserDetailResponse(BaseSchema):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    profile: UserProfileResponse | None = None


class UpdateProfileRequest(BaseSchema):
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    website: str | None = None
    location: str | None = None
    creator_name: str | None = None
