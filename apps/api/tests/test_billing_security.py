"""Billing Security & Payment Tampering Protection Tests."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.agent import Agent, AgentStatus, AgentVisibility
from app.core.security import create_access_token, hash_password


@pytest.mark.asyncio
async def test_checkout_amount_derived_server_side_cannot_be_tampered(client: AsyncClient, db: AsyncSession):
    creator = User(email="pay_cr@example.com", full_name="Payment Creator", hashed_password=hash_password("Pass123"), role=UserRole.CREATOR, is_active=True)
    customer = User(email="pay_cust@example.com", full_name="Payment Customer", hashed_password=hash_password("Pass123"), role=UserRole.CUSTOMER, is_active=True)
    db.add_all([creator, customer])
    await db.commit()

    agent = Agent(
        creator_id=creator.id,
        name="Premium Agent",
        slug="premium-agent",
        description="Premium agent priced at $5.00 (500 minor units)",
        status=AgentStatus.APPROVED,
        visibility=AgentVisibility.PUBLIC,
        pricing_type="per_execution",
        price_per_execution=500,
    )
    db.add(agent)
    await db.commit()

    cust_token = create_access_token({"sub": customer.id})
    client.headers["Authorization"] = f"Bearer {cust_token}"

    # Attacker attempts to pass amount_minor: 1 ($0.01 instead of $5.00)
    checkout_res = await client.post("/api/v1/billing/checkout", json={
        "agent_id": agent.id,
        "amount_minor": 1,
    })
    assert checkout_res.status_code == 200
    data = checkout_res.json()

    # The server strictly sets the amount based on the agent's verified DB price (500), ignoring the payload 1!
    assert data["amount_minor"] == 500
    session_id = data["session_id"]

    # Verify payment using the valid session
    verify_res = await client.post("/api/v1/billing/verify", json={
        "session_id": session_id,
        "payment_id": data["provider_session_id"],
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "success"

    # Replay attack: calling verify again returns idempotent response without crashing or re-crediting
    replay_res = await client.post("/api/v1/billing/verify", json={
        "session_id": session_id,
        "payment_id": data["provider_session_id"],
    })
    assert replay_res.status_code == 200
    assert "already verified" in replay_res.json()["message"]


@pytest.mark.asyncio
async def test_cannot_verify_another_users_checkout_session(client: AsyncClient, db: AsyncSession):
    user_a = User(email="user_a@example.com", full_name="User Alpha", hashed_password=hash_password("Pass123"), role=UserRole.CUSTOMER, is_active=True)
    user_b = User(email="user_b@example.com", full_name="User Beta", hashed_password=hash_password("Pass123"), role=UserRole.CUSTOMER, is_active=True)
    creator = User(email="cr_b@example.com", full_name="Creator Beta", hashed_password=hash_password("Pass123"), role=UserRole.CREATOR, is_active=True)
    db.add_all([user_a, user_b, creator])
    await db.commit()

    agent = Agent(
        creator_id=creator.id,
        name="Per Run Agent",
        slug="per-run-agent",
        description="Priced per run",
        status=AgentStatus.APPROVED,
        visibility=AgentVisibility.PUBLIC,
        pricing_type="per_execution",
        price_per_execution=200,
    )
    db.add(agent)
    await db.commit()

    token_a = create_access_token({"sub": user_a.id})
    token_b = create_access_token({"sub": user_b.id})

    # User A initiates checkout
    client.headers["Authorization"] = f"Bearer {token_a}"
    checkout_res = await client.post("/api/v1/billing/checkout", json={"agent_id": agent.id})
    assert checkout_res.status_code == 200
    session_id = checkout_res.json()["session_id"]
    provider_session_id = checkout_res.json()["provider_session_id"]

    # User B attempts to verify User A's session -> 403 Forbidden!
    client.headers["Authorization"] = f"Bearer {token_b}"
    hack_res = await client.post("/api/v1/billing/verify", json={
        "session_id": session_id,
        "payment_id": provider_session_id,
    })
    assert hack_res.status_code == 403
