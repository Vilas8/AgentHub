"""
Entitlement Service — evaluates whether a user is authorized and paid to run an agent.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentStatus, AgentVisibility
from app.models.billing import Purchase, Subscription, SubscriptionStatus, TransactionStatus
from app.models.user import User


class EntitlementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def verify_and_consume_entitlement(self, user: User, agent: Agent) -> Purchase | None:
        """
        Verify that the user is entitled to execute the given agent.
        If the agent is paid per execution, atomically reserve/consume an unattached Purchase record.
        Raises HTTPException(402/403) if unauthorized or unpaid.
        """
        # Admin or agent creator has unrestricted internal execution privileges
        if user.is_admin or agent.creator_id == user.id:
            return None

        # Agent must be publicly accessible and approved for ordinary users
        if agent.status != AgentStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent is not available for execution (status: {agent.status.value})",
            )

        if agent.visibility != AgentVisibility.PUBLIC:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agent is private and not accessible to the public",
            )

        # Free agents can be executed by any authenticated user
        if agent.pricing_type == "free" or agent.price_per_execution == 0:
            return None

        # Per-execution pricing: user must have a completed, unconsumed purchase
        if agent.pricing_type == "per_execution":
            stmt = (
                select(Purchase)
                .where(
                    Purchase.user_id == user.id,
                    Purchase.agent_id == agent.id,
                    Purchase.status == TransactionStatus.COMPLETED,
                    Purchase.execution_id.is_(None),
                )
                .order_by(Purchase.created_at.asc())
            )
            result = await self.db.execute(stmt)
            purchase = result.scalars().first()

            if not purchase:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "Payment required",
                        "message": f"This agent requires payment of {agent.price_per_execution} minor units per run.",
                        "agent_id": agent.id,
                        "price_per_execution": agent.price_per_execution,
                        "pricing_type": agent.pricing_type,
                    },
                )
            return purchase

        # Subscription pricing: check active subscription to agent or platform plan
        if agent.pricing_type == "subscription":
            sub_stmt = select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                (Subscription.agent_id == agent.id) | (Subscription.agent_id.is_(None)),
            )
            sub_res = await self.db.execute(sub_stmt)
            subscription = sub_res.scalars().first()
            if not subscription:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "Subscription required",
                        "message": "This agent requires an active subscription.",
                        "agent_id": agent.id,
                        "pricing_type": "subscription",
                    },
                )
            return None

        return None
