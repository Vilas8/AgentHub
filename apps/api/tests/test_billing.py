"""Billing service tests."""
import pytest
from app.services.billing_service import BillingService


@pytest.mark.asyncio
async def test_commission_calculation_default_80_20(db):
    service = BillingService(db)
    result = await service.calculate_commission(10000)  # $100.00
    assert result["creator_minor"] == 8000  # 80%
    assert result["platform_minor"] == 2000  # 20%
    assert result["gross_minor"] == 10000
    assert result["creator_pct"] == 80
    assert result["platform_pct"] == 20


@pytest.mark.asyncio
async def test_commission_no_rounding_error(db):
    service = BillingService(db)
    # $99 -> integer division should not lose money
    result = await service.calculate_commission(99)
    assert result["creator_minor"] + result["platform_minor"] == 99


@pytest.mark.asyncio
async def test_creator_credit(db):
    service = BillingService(db)
    import uuid
    creator_id = str(uuid.uuid4())
    entry = await service.credit_creator(
        creator_id=creator_id,
        amount_minor=5000,
        entry_type="execution_earning",
        description="Test credit",
    )
    await db.commit()
    assert entry.amount_minor == 5000
    assert entry.balance_after_minor == 5000


@pytest.mark.asyncio
async def test_payment_simulator():
    from app.services.payment_service import SimulatorPaymentProvider
    provider = SimulatorPaymentProvider()
    session = await provider.create_checkout_session(1000, "USD", "Test", {})
    assert session["provider"] == "simulator"
    assert session["session_id"].startswith("sim_")
    verified = await provider.verify_payment(session["session_id"])
    assert verified is True
