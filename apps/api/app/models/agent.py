"""Agent registry models."""
import enum
from sqlalchemy import Boolean, Enum, Integer, JSON, String, Text, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class AgentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class AgentVisibility(str, enum.Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class PricingType(str, enum.Enum):
    FREE = "free"
    SUBSCRIPTION = "subscription"
    PER_EXECUTION = "per_execution"


class Agent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agents"

    creator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.DRAFT, nullable=False, index=True)
    visibility: Mapped[AgentVisibility] = mapped_column(Enum(AgentVisibility), default=AgentVisibility.PRIVATE, nullable=False)
    is_platform_owned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pricing_type: Mapped[PricingType] = mapped_column(Enum(PricingType), default=PricingType.FREE, nullable=False)
    price_per_execution: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Minor currency units")
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    total_executions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    versions: Mapped[list["AgentVersion"]] = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan")


class AgentVersion(Base, UUIDMixin, TimestampMixin):
    """Immutable snapshot of agent configuration at a point in time."""
    __tablename__ = "agent_versions"

    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="gemini")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="gemini-1.5-flash")
    temperature: Mapped[float] = mapped_column(Numeric(3, 2), default=0.7, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    max_steps: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_duration_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    tools_config: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    input_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="versions")
