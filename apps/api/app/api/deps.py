"""FastAPI dependency injection utilities."""
from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError
import structlog

from app.database.base import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

logger = structlog.get_logger(__name__)


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not access_token:
        raise credentials_exception
    try:
        payload = decode_token(access_token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exception
    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_creator(user: User = Depends(get_current_active_user)) -> User:
    if not user.is_creator:
        raise HTTPException(status_code=403, detail="Creator access required")
    return user


async def get_current_admin(user: User = Depends(get_current_active_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
