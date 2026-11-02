"""
Billing service — commission calculation and ledger management.
All amounts in integer minor currency units (e.g. cents/paise).
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.billing import CommissionRule, CreatorBalance, CreatorLedgerEntry

logger = structlog.get_logger(__name__)


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_commission_rule(self, agent_id: str | None = None) -> CommissionRule:
        """Get the applicable commission rule. Returns default if no agent-specific rule."""
        result = await self.db.execute(
            select(CommissionRule).where(CommissionRule.is_default.is_(True), CommissionRule.is_active.is_(True))
        )
        rule = result.scalar_one_or_none()
        if not rule:
            # Bootstrap default rule
            rule = CommissionRule(
                name="Default",
                creator_pct=80,
                platform_pct=20,
                is_default=True,
                is_active=True,
            )
            self.db.add(rule)
            await self.db.flush()
        return rule

    async def calculate_commission(self, gross_amount_minor: int, agent_id: str | None = None) -> dict:
        """Calculate creator and platform shares from a gross amount."""
        rule = await self.get_commission_rule(agent_id)
        creator_share = (gross_amount_minor * rule.creator_pct) // 100
        platform_share = gross_amount_minor - creator_share  # Remainder goes to platform to avoid rounding loss
        return {
            "gross_minor": gross_amount_minor,
            "creator_minor": creator_share,
            "platform_minor": platform_share,
            "creator_pct": rule.creator_pct,
            "platform_pct": rule.platform_pct,
            "rule_id": rule.id,
        }

    async def credit_creator(self, creator_id: str, amount_minor: int, entry_type: str, description: str, reference_id: str | None = None) -> CreatorLedgerEntry:
        """Credit creator earnings. Immutable ledger — never updates existing entries."""
        # Get or create balance record
        result = await self.db.execute(select(CreatorBalance).where(CreatorBalance.creator_id == creator_id))
        balance = result.scalar_one_or_none()
        if not balance:
            balance = CreatorBalance(creator_id=creator_id, available_minor=0, pending_minor=0, total_earned_minor=0)
            self.db.add(balance)
            await self.db.flush()

        balance.pending_minor += amount_minor
        balance.total_earned_minor += amount_minor

        entry = CreatorLedgerEntry(
            creator_id=creator_id,
            amount_minor=amount_minor,
            entry_type=entry_type,
            description=description,
            reference_id=reference_id,
            balance_after_minor=balance.available_minor + balance.pending_minor,
        )
        self.db.add(entry)
        await self.db.flush()
        logger.info("Creator credited", creator_id=creator_id, amount_minor=amount_minor, entry_type=entry_type)
        return entry
