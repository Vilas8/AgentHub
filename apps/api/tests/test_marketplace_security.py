"""Marketplace, Review, and Bookmark security tests."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.agent import Agent, AgentStatus, AgentVisibility
from app.core.security import create_access_token, hash_password


@pytest.mark.asyncio
async def test_review_security_and_one_review_per_user(client: AsyncClient, db: AsyncSession):
    # Setup creator and customers
    creator = User(email="cr1@example.com", full_name="Creator One", hashed_password=hash_password("Pass123"), role=UserRole.CREATOR, is_active=True)
    cust1 = User(email="cust1@example.com", full_name="Customer One", hashed_password=hash_password("Pass123"), role=UserRole.CUSTOMER, is_active=True)
    cust2 = User(email="cust2@example.com", full_name="Customer Two", hashed_password=hash_password("Pass123"), role=UserRole.CUSTOMER, is_active=True)
    db.add_all([creator, cust1, cust2])
    await db.commit()

    agent = Agent(
        creator_id=creator.id,
        name="Security Verified Agent",
        slug="security-verified-agent",
        description="A public agent for testing reviews",
        status=AgentStatus.APPROVED,
        visibility=AgentVisibility.PUBLIC,
        pricing_type="free",
    )
    db.add(agent)
    await db.commit()

    cust1_token = create_access_token({"sub": cust1.id})
    cust2_token = create_access_token({"sub": cust2.id})

    # 1. Anonymous review rejected
    anon_res = await client.post(f"/api/v1/marketplace/agents/{agent.id}/reviews", json={"rating": 5, "comment": "Great"})
    assert anon_res.status_code == 401

    # 2. Invalid rating rejected (out of bounds)
    client.headers["Authorization"] = f"Bearer {cust1_token}"
    bad_rating = await client.post(f"/api/v1/marketplace/agents/{agent.id}/reviews", json={"rating": 6})
    assert bad_rating.status_code == 400

    bad_rating_low = await client.post(f"/api/v1/marketplace/agents/{agent.id}/reviews", json={"rating": 0})
    assert bad_rating_low.status_code == 400

    # 3. Customer 1 submits valid review
    rev1 = await client.post(f"/api/v1/marketplace/agents/{agent.id}/reviews", json={"rating": 4, "comment": "Nice work"})
    assert rev1.status_code == 201
    assert rev1.json()["average_rating"] == 4.0
    assert rev1.json()["review_count"] == 1

    # 4. Duplicate review from Customer 1 rejected with 409 Conflict
    dup_res = await client.post(f"/api/v1/marketplace/agents/{agent.id}/reviews", json={"rating": 5, "comment": "Trying again"})
    assert dup_res.status_code == 409

    # 5. Customer 2 can review independently
    client.headers["Authorization"] = f"Bearer {cust2_token}"
    rev2 = await client.post(f"/api/v1/marketplace/agents/{agent.id}/reviews", json={"rating": 5, "comment": "Loved it"})
    assert rev2.status_code == 201
    assert rev2.json()["average_rating"] == 4.5
    assert rev2.json()["review_count"] == 2


@pytest.mark.asyncio
async def test_bookmark_isolation_per_user(client: AsyncClient, db: AsyncSession):
    u1 = User(email="bm1@example.com", full_name="User BM 1", hashed_password=hash_password("Pass123"), role=UserRole.CUSTOMER, is_active=True)
    u2 = User(email="bm2@example.com", full_name="User BM 2", hashed_password=hash_password("Pass123"), role=UserRole.CUSTOMER, is_active=True)
    db.add_all([u1, u2])
    await db.commit()

    agent = Agent(
        creator_id=u1.id,
        name="Bookmark Agent",
        slug="bm-agent",
        description="Agent for testing bookmarks",
        status=AgentStatus.APPROVED,
        visibility=AgentVisibility.PUBLIC,
        pricing_type="free",
    )
    db.add(agent)
    await db.commit()

    u1_token = create_access_token({"sub": u1.id})
    u2_token = create_access_token({"sub": u2.id})

    # User 1 bookmarks
    client.headers["Authorization"] = f"Bearer {u1_token}"
    bm_res = await client.post(f"/api/v1/marketplace/agents/{agent.id}/bookmark")
    assert bm_res.status_code == 200
    assert bm_res.json()["bookmarked"] is True

    # User 1 bookmarks list contains agent
    list_u1 = await client.get("/api/v1/marketplace/bookmarks")
    assert list_u1.status_code == 200
    assert len(list_u1.json()) == 1
    assert list_u1.json()[0]["id"] == agent.id

    # User 2 bookmarks list is empty (isolated!)
    client.headers["Authorization"] = f"Bearer {u2_token}"
    list_u2 = await client.get("/api/v1/marketplace/bookmarks")
    assert list_u2.status_code == 200
    assert len(list_u2.json()) == 0


@pytest.mark.asyncio
async def test_agent_ownership_protection(client: AsyncClient, db: AsyncSession):
    creator_owner = User(email="owner@example.com", full_name="Owner Creator", hashed_password=hash_password("Pass123"), role=UserRole.CREATOR, is_active=True)
    creator_intruder = User(email="intruder@example.com", full_name="Intruder Creator", hashed_password=hash_password("Pass123"), role=UserRole.CREATOR, is_active=True)
    db.add_all([creator_owner, creator_intruder])
    await db.commit()

    agent = Agent(
        creator_id=creator_owner.id,
        name="Owner's Agent",
        slug="owners-agent",
        description="Proprietary code",
        status=AgentStatus.DRAFT,
        visibility=AgentVisibility.PRIVATE,
        pricing_type="free",
    )
    db.add(agent)
    await db.commit()

    intruder_token = create_access_token({"sub": creator_intruder.id})
    client.headers["Authorization"] = f"Bearer {intruder_token}"

    # Intruder cannot update owner's agent
    update_res = await client.patch(f"/api/v1/agents/{agent.id}", json={"name": "Hacked Name"})
    assert update_res.status_code == 403

    # Intruder cannot add versions to owner's agent
    ver_res = await client.post(f"/api/v1/agents/{agent.id}/versions", json={
        "system_prompt": "Hacked prompt",
    })
    assert ver_res.status_code == 403
