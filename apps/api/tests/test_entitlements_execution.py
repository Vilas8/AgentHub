"""Entitlement enforcement and execution lifecycle tests."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.agent import Agent, AgentStatus, AgentVisibility
from app.core.security import create_access_token, hash_password


@pytest.mark.asyncio
async def test_entitlement_blocks_unpaid_execution(client: AsyncClient, db: AsyncSession):
    creator = User(email="ent_cr@example.com", full_name="Ent Creator", hashed_password=hash_password("Pass123"), role=UserRole.CREATOR, is_active=True)
    customer = User(email="ent_cust@example.com", full_name="Ent Customer", hashed_password=hash_password("Pass123"), role=UserRole.CUSTOMER, is_active=True)
    db.add_all([creator, customer])
    await db.commit()

    agent = Agent(
        creator_id=creator.id,
        name="Paid Execution Agent",
        slug="paid-exec-agent",
        description="Must be purchased before running",
        status=AgentStatus.APPROVED,
        visibility=AgentVisibility.PUBLIC,
        pricing_type="per_execution",
        price_per_execution=300,
    )
    db.add(agent)
    await db.commit()

    cust_token = create_access_token({"sub": customer.id})
    client.headers["Authorization"] = f"Bearer {cust_token}"

    # 1. Customer tries to execute without purchasing -> 402 Payment Required!
    exec_res = await client.post("/api/v1/executions/", json={
        "agent_id": agent.id,
        "input_data": {"query": "Analyze financial report"},
    })
    assert exec_res.status_code == 402
    assert "Payment required" in str(exec_res.json())

    # 2. Customer buys 1 execution via checkout and verification
    checkout = await client.post("/api/v1/billing/checkout", json={"agent_id": agent.id})
    assert checkout.status_code == 200
    session_id = checkout.json()["session_id"]
    provider_id = checkout.json()["provider_session_id"]

    verify = await client.post("/api/v1/billing/verify", json={
        "session_id": session_id,
        "payment_id": provider_id,
    })
    assert verify.status_code == 200

    # 3. Customer runs agent -> succeeds now!
    exec_res2 = await client.post("/api/v1/executions/", json={
        "agent_id": agent.id,
        "input_data": {"query": "Analyze financial report"},
    })
    assert exec_res2.status_code == 201
    assert "id" in exec_res2.json()

    # 4. Immediate second run without buying again -> 402 Payment Required (purchase was consumed)!
    exec_res3 = await client.post("/api/v1/executions/", json={
        "agent_id": agent.id,
        "input_data": {"query": "Second query"},
    })
    assert exec_res3.status_code == 402


@pytest.mark.asyncio
async def test_execution_cancellation(client: AsyncClient, db: AsyncSession):
    customer = User(email="cancel_u@example.com", full_name="Cancel Customer", hashed_password=hash_password("Pass123"), role=UserRole.CUSTOMER, is_active=True)
    db.add(customer)
    await db.commit()

    agent = Agent(
        creator_id=customer.id,
        name="Free Cancellation Agent",
        slug="free-cancel-agent",
        description="Free test agent",
        status=AgentStatus.APPROVED,
        visibility=AgentVisibility.PUBLIC,
        pricing_type="free",
    )
    db.add(agent)
    await db.commit()

    token = create_access_token({"sub": customer.id})
    client.headers["Authorization"] = f"Bearer {token}"

    # Start execution
    res = await client.post("/api/v1/executions/", json={
        "agent_id": agent.id,
        "input_data": {"query": "Long running task"},
    })
    assert res.status_code == 201
    exec_id = res.json()["id"]

    # Cancel execution
    cancel_res = await client.post(f"/api/v1/executions/{exec_id}/cancel")
    assert cancel_res.status_code in (200, 400)  # 200 if still running, 400 if already finished
