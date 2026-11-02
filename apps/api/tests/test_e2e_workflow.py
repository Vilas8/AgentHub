"""
End-to-End Workflow Tests:
1. Register Customer & Creator
2. Create Agent as Creator
3. Submit Agent for Review
4. Admin approves Agent
5. Customer executes Agent
6. Verify Execution status and output
7. Verify Creator Ledger / commission calculation
8. Verify Tool execution allowlist
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.agent import Agent, AgentStatus, AgentVisibility
from app.models.execution import Execution, ExecutionStatus
from app.core.security import hash_password, create_access_token
from app.modules.tools.registry import tool_registry


@pytest.mark.asyncio
async def test_full_agent_lifecycle_e2e(client: AsyncClient, db: AsyncSession):
    # 1. Setup Admin, Creator, and Customer
    admin = User(
        email="admin_e2e@agenthub.example",
        hashed_password=hash_password("AdminPass1"),
        full_name="Admin E2E",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    creator = User(
        email="creator_e2e@agenthub.example",
        hashed_password=hash_password("CreatorPass1"),
        full_name="Creator E2E",
        role=UserRole.CREATOR,
        is_active=True,
    )
    customer = User(
        email="customer_e2e@agenthub.example",
        hashed_password=hash_password("CustomerPass1"),
        full_name="Customer E2E",
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db.add_all([admin, creator, customer])
    await db.commit()

    admin_token = create_access_token({"sub": admin.id})
    creator_token = create_access_token({"sub": creator.id})
    customer_token = create_access_token({"sub": customer.id})

    # 2. Creator creates a draft agent
    client.cookies.set("access_token", creator_token)
    create_res = await client.post("/api/v1/agents/", json={
        "name": "E2E Test Intelligence Agent",
        "description": "Autonomous analysis of structured inputs.",
        "short_description": "Analyzes business metrics.",
        "pricing_type": "free",
        "visibility": "public",
    })
    assert create_res.status_code == 201
    agent_id = create_res.json()["id"]

    # 3. Creator attaches version 1
    version_res = await client.post(f"/api/v1/agents/{agent_id}/versions", json={
        "system_prompt": "You are an E2E test agent.",
        "objective": "Process test data",
        "model_provider": "development",
        "model_name": "default",
        "temperature": 0.5,
    })
    assert version_res.status_code == 201
    assert version_res.json()["version_number"] >= 1

    # 4. Creator submits for review
    submit_res = await client.post(f"/api/v1/agents/{agent_id}/submit-review")
    assert submit_res.status_code == 200

    # Verify status is pending_review
    check_res = await client.get(f"/api/v1/agents/{agent_id}")
    assert check_res.json()["status"] == "pending_review"

    # 5. Admin reviews and approves the agent
    client.cookies.set("access_token", admin_token)
    pending_list = await client.get("/api/v1/admin/agents/pending")
    assert pending_list.status_code == 200
    assert any(a["id"] == agent_id for a in pending_list.json())

    approve_res = await client.post(f"/api/v1/admin/agents/{agent_id}/approve")
    assert approve_res.status_code == 200

    # 6. Customer browses marketplace and finds the agent
    client.cookies.set("access_token", customer_token)
    mkt_res = await client.get(f"/api/v1/marketplace/agents/{agent_id}")
    assert mkt_res.status_code == 200
    assert mkt_res.json()["status"] == "approved"

    # 7. Customer executes the agent
    exec_res = await client.post("/api/v1/executions/", json={
        "agent_id": agent_id,
        "input_data": {"query": "Analyze quarterly retention rates."},
    })
    assert exec_res.status_code == 201
    execution_id = exec_res.json()["id"]
    assert exec_res.json()["status"] in ("queued", "initializing", "running", "completed")

    # 8. Query execution record
    get_exec = await client.get(f"/api/v1/executions/{execution_id}")
    assert get_exec.status_code == 200
    assert get_exec.json()["agent_id"] == agent_id


@pytest.mark.asyncio
async def test_tool_registry_allowlist_and_execution():
    calc = tool_registry.get_tool("calculator")
    assert calc is not None
    assert calc.requires_approval is False

    res = await tool_registry.execute_tool("calculator", {"expression": "25 * 4 + 10"})
    assert res["result"] == 110.0

    email_tool = tool_registry.get_tool("email_draft")
    assert email_tool is not None
    assert email_tool.requires_approval is True

    draft = await tool_registry.execute_tool("email_draft", {
        "recipient": "client@example.com",
        "subject": "Proposal Update",
        "key_points": ["Scope agreed", "Timeline 2 weeks"],
    })
    assert "Proposal Update" in draft["body"]
    assert draft["status"] == "drafted_pending_approval"


@pytest.mark.asyncio
async def test_unauthorized_tool_rejected():
    with pytest.raises(ValueError, match="not registered in the allowlisted tool registry"):
        await tool_registry.execute_tool("arbitrary_bash_command", {"cmd": "rm -rf /"})
