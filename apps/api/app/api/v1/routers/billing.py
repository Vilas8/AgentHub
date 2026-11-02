"""Billing routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import get_db
from app.models.user import User
from app.models.billing import CreatorBalance, CreatorLedgerEntry
from app.schemas.common import SuccessResponse
from app.api.deps import get_current_active_user, get_current_creator

router = APIRouter()


@router.get("/creator/balance")
async def get_creator_balance(user: User = Depends(get_current_creator), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CreatorBalance).where(CreatorBalance.creator_id == user.id))
    balance = result.scalar_one_or_none()
    if not balance:
        return {"available_minor": 0, "pending_minor": 0, "total_earned_minor": 0, "currency": "USD"}
    return {
        "available_minor": balance.available_minor,
        "pending_minor": balance.pending_minor,
        "total_earned_minor": balance.total_earned_minor,
        "currency": balance.currency,
    }


@router.get("/creator/ledger")
async def get_creator_ledger(user: User = Depends(get_current_creator), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CreatorLedgerEntry).where(CreatorLedgerEntry.creator_id == user.id).order_by(CreatorLedgerEntry.created_at.desc()).limit(50)
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "amount_minor": e.amount_minor,
            "entry_type": e.entry_type,
            "description": e.description,
            "balance_after_minor": e.balance_after_minor,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]
