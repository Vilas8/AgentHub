"""Authentication routes with refresh token rotation and CSRF security."""
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog

from app.database.base import get_db
from app.models.user import User, UserRole, UserProfile, RefreshToken
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    generate_csrf_token,
)
from app.core.config import settings
from app.schemas.auth import RegisterRequest, LoginRequest, UserResponse
from app.schemas.common import SuccessResponse
from app.api.deps import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()

# Rate limiting for auth endpoints: IP -> [timestamps]
_auth_attempts: dict[str, list[float]] = defaultdict(list)
AUTH_WINDOW_SEC = 60
AUTH_MAX_ATTEMPTS = 15


def check_auth_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    recent = [t for t in _auth_attempts[client_ip] if now - t < AUTH_WINDOW_SEC]
    _auth_attempts[client_ip] = recent
    if len(recent) >= AUTH_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please wait a minute.",
        )
    _auth_attempts[client_ip].append(now)


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    # Access Token (HTTP-Only)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    # Refresh Token (HTTP-Only)
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    # CSRF Token (Readable by frontend client to pass in X-CSRF-Token header)
    response.set_cookie(
        "csrf_token",
        csrf_token,
        httponly=False,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    check_auth_rate_limit(request)

    # Email uniqueness check
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=UserRole.CUSTOMER,
        is_active=True,
        is_verified=False,
        verification_token=str(uuid.uuid4()),
    )
    db.add(user)
    await db.flush()

    profile = UserProfile(user_id=user.id)
    db.add(profile)

    # Issue tokens
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    csrf_token = generate_csrf_token()

    # Record refresh token in DB for tracking/revocation
    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(token_record)

    await db.commit()
    await db.refresh(user)

    _set_auth_cookies(response, access_token, refresh_token, csrf_token)
    logger.info("User registered successfully", user_id=user.id, email=user.email)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
    )


@router.post("/login", response_model=UserResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    check_auth_rate_limit(request)

    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    csrf_token = generate_csrf_token()

    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(token_record)
    await db.commit()

    _set_auth_cookies(response, access_token, refresh_token, csrf_token)
    logger.info("User logged in successfully", user_id=user.id)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
    )


@router.post("/refresh", response_model=SuccessResponse)
async def refresh_session(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Validate and rotate refresh token. Revokes previous token immediately."""
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    # Check database record
    current_hash = hash_token(refresh_token)
    res = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == current_hash,
            RefreshToken.user_id == user_id,
        )
    )
    token_rec = res.scalar_one_or_none()
    now_utc = datetime.now(timezone.utc)

    if not token_rec or token_rec.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    
    # Check expiry with timezone awareness
    exp = token_rec.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now_utc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    # Invalidate old token (Rotation)
    token_rec.revoked = True

    # Check user active status
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user or not user.is_active:
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    # Issue new pair
    new_access_token = create_access_token({"sub": user.id})
    new_refresh_token = create_refresh_token({"sub": user.id})
    new_csrf_token = generate_csrf_token()

    new_token_rec = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_token),
        expires_at=now_utc + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(new_token_rec)
    await db.commit()

    _set_auth_cookies(response, new_access_token, new_refresh_token, new_csrf_token)
    return SuccessResponse(message="Session refreshed successfully")


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token in database and clear client authentication cookies."""
    if refresh_token:
        current_hash = hash_token(refresh_token)
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == current_hash)
            .values(revoked=True)
        )
        await db.commit()

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("csrf_token")
    return SuccessResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
    )
