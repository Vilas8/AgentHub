"""Billing and payment routes."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import get_db
from app.models.user import User
from app.models.agent import Agent, AgentStatus
from app.models.billing import (
    CheckoutSession,
    CheckoutSessionStatus,
    CreatorBalance,
    CreatorLedgerEntry,
    PaymentTransaction,
    Plan,
    Purchase,
    TransactionStatus,
)
from app.schemas.common import SuccessResponse
from app.api.deps import get_current_active_user, get_current_creator
from app.services.payment_service import get_payment_provider
from app.services.billing_service import BillingService

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
        select(CreatorLedgerEntry)
        .where(CreatorLedgerEntry.creator_id == user.id)
        .order_by(CreatorLedgerEntry.created_at.desc())
        .limit(50)
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


CREDIT_TIERS = {
    "credits_10": {"amount_minor": 1000, "name": "1,000 Credits Pack ($10)"},
    "credits_25": {"amount_minor": 2500, "name": "2,500 Credits Pack ($25)"},
    "credits_50": {"amount_minor": 5000, "name": "5,000 Credits Pack ($50)"},
}


@router.post("/checkout")
async def create_checkout_session(
    payload: dict,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a server-side checkout session for agent execution, subscription, or credits.
    Amount and currency are derived strictly from server records, NEVER trusted blindly.
    """
    provider = get_payment_provider()

    agent_id = payload.get("agent_id")
    plan_id = payload.get("plan_id")
    credit_tier = payload.get("credit_tier")

    description = "AgentHub Service"
    amount_minor = 0
    currency = "USD"

    if agent_id:
        agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_res.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        if agent.pricing_type == "free":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Free agents do not require checkout")
        amount_minor = agent.price_per_execution
        description = f"Execution access for agent: {agent.name}"
    elif plan_id:
        plan_res = await db.execute(select(Plan).where(Plan.id == plan_id, Plan.is_active == True))
        plan = plan_res.scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or inactive")
        amount_minor = plan.price_minor
        currency = plan.currency
        description = f"Subscription: {plan.name}"
    elif credit_tier:
        if credit_tier not in CREDIT_TIERS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid credit tier. Choose from {list(CREDIT_TIERS.keys())}")
        tier_data = CREDIT_TIERS[credit_tier]
        amount_minor = tier_data["amount_minor"]
        description = tier_data["name"]
    else:
        # Client must provide a valid target
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify agent_id, plan_id, or valid credit_tier",
        )

    if amount_minor <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid checkout amount")

    # Call payment gateway provider to initiate external session
    provider_res = await provider.create_checkout_session(
        amount_minor=amount_minor,
        currency=currency,
        description=description,
        metadata={"user_id": user.id, "agent_id": agent_id, "plan_id": plan_id},
    )

    provider_session_id = provider_res.get("session_id")

    # Persist immutable server-side checkout session
    checkout = CheckoutSession(
        user_id=user.id,
        agent_id=agent_id,
        plan_id=plan_id,
        provider=provider.provider_name,
        provider_session_id=provider_session_id,
        amount_minor=amount_minor,
        currency=currency,
        status=CheckoutSessionStatus.PENDING,
        payment_metadata=provider_res,
    )
    db.add(checkout)
    await db.commit()
    await db.refresh(checkout)

    return {
        "session_id": checkout.id,
        "provider_session_id": provider_session_id,
        "provider": provider.provider_name,
        "amount_minor": amount_minor,
        "currency": currency,
        "checkout_url": provider_res.get("checkout_url"),
    }


@router.post("/verify")
async def verify_payment(
    payload: dict,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify payment settlement using server-stored checkout session.
    Prevents replay attacks, verifies ownership and amount against DB session.
    """
    session_id = payload.get("session_id")
    provider_session_id = payload.get("order_id") or payload.get("payment_id")

    if not session_id and not provider_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide session_id or order_id",
        )

    # Look up server checkout session
    query = select(CheckoutSession)
    if session_id:
        query = query.where(CheckoutSession.id == session_id)
    else:
        query = query.where(CheckoutSession.provider_session_id == provider_session_id)

    res = await db.execute(query)
    checkout = res.scalar_one_or_none()

    if not checkout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout session not found")

    # Ensure checkout belongs to the calling user
    if checkout.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session does not belong to user")

    # Idempotent response if already verified
    if checkout.status == CheckoutSessionStatus.COMPLETED:
        return {"status": "success", "message": "Payment already verified", "session_id": checkout.id}

    provider = get_payment_provider()
    payment_id = payload.get("payment_id") or checkout.provider_session_id
    order_id = payload.get("order_id") or checkout.provider_session_id
    signature = payload.get("signature")

    verified = await provider.verify_payment(
        payment_id=payment_id,
        order_id=order_id,
        signature=signature,
        session_id=checkout.provider_session_id,
    )

    if not verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment signature or status verification failed")

    # Transactional settlement
    checkout.status = CheckoutSessionStatus.COMPLETED

    tx = PaymentTransaction(
        user_id=checkout.user_id,
        amount_minor=checkout.amount_minor,
        currency=checkout.currency,
        provider=checkout.provider,
        provider_transaction_id=payment_id,
        status=TransactionStatus.COMPLETED,
        event_type="charge.succeeded",
        payment_metadata={"checkout_session_id": checkout.id, "verified_at": "now"},
        idempotency_key=f"tx_{checkout.id}",
    )
    db.add(tx)

    # If this was for an agent, grant a Purchase record and credit creator
    if checkout.agent_id:
        purchase = Purchase(
            user_id=checkout.user_id,
            agent_id=checkout.agent_id,
            amount_minor=checkout.amount_minor,
            currency=checkout.currency,
            status=TransactionStatus.COMPLETED,
            idempotency_key=f"purchase_{checkout.id}",
        )
        db.add(purchase)

        # Calculate commission & credit creator balance
        agent_res = await db.execute(select(Agent).where(Agent.id == checkout.agent_id))
        agent = agent_res.scalar_one_or_none()
        if agent and agent.creator_id:
            billing_svc = BillingService(db)
            split = await billing_svc.calculate_commission(checkout.amount_minor, agent_id=agent.id)
            await billing_svc.credit_creator(
                creator_id=agent.creator_id,
                amount_minor=split["creator_minor"],
                entry_type="agent_purchase",
                description=f"Purchase of agent '{agent.name}'",
                reference_id=purchase.id,
            )

    await db.commit()
    return {"status": "success", "message": "Payment verified and settled", "session_id": checkout.id}


@router.post("/webhook")
async def payment_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Process incoming payment gateway webhooks with cryptographic signature verification."""
    provider = get_payment_provider()
    body = await request.body()
    signature = (
        request.headers.get("x-razorpay-signature")
        or request.headers.get("stripe-signature")
        or ""
    )

    try:
        event = await provider.handle_webhook(body, signature)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {"status": "received", "event": event.get("event", "processed")}

