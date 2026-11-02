"""Billing and financial models. All amounts in minor currency units (integer)."""
import enum
from sqlalchemy import Boolean, Enum, Integer, JSON, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class PlanInterval(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    EXPIRED = "expired"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class CheckoutSessionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


class CheckoutSession(Base, UUIDMixin, TimestampMixin):
    """Server-side checkout session record linking user, item, and payment."""
    __tablename__ = "checkout_sessions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    plan_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("plans.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[CheckoutSessionStatus] = mapped_column(
        Enum(CheckoutSessionStatus),
        nullable=False,
        default=CheckoutSessionStatus.PENDING,
    )
    expires_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)



class Plan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False, comment="Price in minor currency units")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    interval: Mapped[PlanInterval] = mapped_column(Enum(PlanInterval), nullable=False)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("plans.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="simulator")
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_period_end: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cancelled_at: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Purchase(Base, UUIDMixin, TimestampMixin):
    """One-time purchase of a per-execution agent."""
    __tablename__ = "purchases"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    execution_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("executions.id"), nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class PaymentTransaction(Base, UUIDMixin, TimestampMixin):
    """Immutable payment event record."""
    __tablename__ = "payment_transactions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class CreatorBalance(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "creator_balances"

    creator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    available_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_earned_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)


class CreatorLedgerEntry(Base, UUIDMixin, TimestampMixin):
    """Immutable ledger. Never update or delete rows."""
    __tablename__ = "creator_ledger_entries"

    creator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, comment="Positive=credit, negative=debit")
    entry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    balance_after_minor: Mapped[int] = mapped_column(Integer, nullable=False)


class CommissionRule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "commission_rules"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    creator_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=80, comment="Creator percentage 0-100")
    platform_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=20, comment="Platform percentage 0-100")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
