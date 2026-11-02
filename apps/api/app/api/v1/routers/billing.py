"""Billing routes."""
from fastapi import APIRouter, Depends, HTTPException
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


@router.post("/checkout")
async def create_checkout_session(
    payload: dict,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a checkout session for agent usage or subscription."""
    import uuid
    from app.services.payment_service import get_payment_provider
    provider = get_payment_provider()
    
    amount_minor = int(payload.get("amount_minor", 500))  # $5.00 default
    currency = payload.get("currency", "USD")
    description = payload.get("description", "AgentHub Credits")
    agent_id = payload.get("agent_id")

    session = await provider.create_checkout_session(
        amount_minor=amount_minor,
        currency=currency,
        description=description,
        metadata={"user_id": user.id, "agent_id": agent_id},
    )
    return session


@router.post("/verify")
async def verify_payment(
    payload: dict,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify payment and credit creator if applicable."""
    import uuid
    from app.services.payment_service import get_payment_provider
    from app.services.billing_service import BillingService
    from app.models.billing import PaymentTransaction, TransactionStatus, Purchase
    from app.models.agent import Agent

    payment_id = payload.get("payment_id")
    provider = get_payment_provider()
    verified = await provider.verify_payment(payment_id)

    if not verified:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    amount_minor = int(payload.get("amount_minor", 500))
    agent_id = payload.get("agent_id")

    # Record payment transaction
    tx = PaymentTransaction(
        user_id=user.id,
        amount_minor=amount_minor,
        currency="USD",
        provider=provider.provider_name,
        provider_transaction_id=payment_id,
        status=TransactionStatus.COMPLETED,
        event_type="charge.succeeded",
        payment_metadata=payload,
        idempotency_key=str(uuid.uuid4()),
    )
    db.add(tx)

    # If this was for an agent, record purchase & calculate creator revenue
    if agent_id:
        purchase = Purchase(
            user_id=user.id,
            agent_id=agent_id,
            amount_minor=amount_minor,
            currency="USD",
            status=TransactionStatus.COMPLETED,
            idempotency_key=str(uuid.uuid4()),
        )
        db.add(purchase)

        # Credit creator via billing service
        agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_res.scalar_one_or_none()
        if agent and agent.creator_id:
            billing_svc = BillingService(db)
            split = await billing_svc.calculate_commission(amount_minor, agent_id=agent_id)
            await billing_svc.credit_creator(
                creator_id=agent.creator_id,
                amount_minor=split["creator_minor"],
                entry_type="agent_purchase",
                description=f"Purchase of agent '{agent.name}'",
                reference_id=purchase.id,
            )

    await db.commit()
    return {"status": "success", "message": "Payment verified and settled"}
