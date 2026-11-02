"""Admin dashboard routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database.base import get_db
from app.models.user import User
from app.models.agent import Agent, AgentStatus, AgentVisibility
from app.models.execution import Execution, ExecutionStatus
from app.schemas.agent import AgentResponse
from app.schemas.common import SuccessResponse
from app.api.deps import get_current_admin

router = APIRouter()


@router.get("/overview")
async def admin_overview(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    agent_count = (await db.execute(select(func.count(Agent.id)))).scalar() or 0
    pending_count = (await db.execute(select(func.count(Agent.id)).where(Agent.status == AgentStatus.PENDING_REVIEW))).scalar() or 0
    execution_count = (await db.execute(select(func.count(Execution.id)))).scalar() or 0
    failed_count = (await db.execute(select(func.count(Execution.id)).where(Execution.status == ExecutionStatus.FAILED))).scalar() or 0

    return {
        "total_users": user_count,
        "total_agents": agent_count,
        "pending_review": pending_count,
        "total_executions": execution_count,
        "failed_executions": failed_count,
    }


@router.get("/agents/pending", response_model=list[AgentResponse])
async def list_pending_agents(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Agent).where(Agent.status == AgentStatus.PENDING_REVIEW).order_by(Agent.created_at.asc())
    )
    agents = result.scalars().all()
    return [AgentResponse.model_validate(a) for a in agents]


@router.post("/agents/{agent_id}/approve", response_model=SuccessResponse)
async def approve_agent(agent_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = AgentStatus.APPROVED
    agent.visibility = AgentVisibility.PUBLIC if agent.visibility == "private" else agent.visibility
    await db.commit()
    return SuccessResponse(message="Agent approved")


@router.post("/agents/{agent_id}/reject", response_model=SuccessResponse)
async def reject_agent(agent_id: str, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.status != AgentStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="Agent is not pending review")
    agent.status = AgentStatus.REJECTED
    await db.commit()
    return SuccessResponse(message="Agent rejected")


@router.get("/users", response_model=list)
async def list_users(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(100))
    users = result.scalars().all()
    return [
        {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role.value, "is_active": u.is_active, "created_at": u.created_at.isoformat()}
        for u in users
    ]
