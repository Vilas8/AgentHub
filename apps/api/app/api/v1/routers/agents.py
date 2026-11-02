"""Agent registry routes — creator facing."""
import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import get_db
from app.models.user import User
from app.models.agent import Agent, AgentVersion, AgentStatus, AgentVisibility
from app.schemas.agent import CreateAgentRequest, UpdateAgentRequest, AgentVersionRequest, AgentResponse
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.api.deps import get_current_active_user, get_current_creator

router = APIRouter()


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug + "-" + str(uuid.uuid4())[:8]


@router.get("/my", response_model=list[AgentResponse])
async def list_my_agents(
    user: User = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent).where(Agent.creator_id == user.id).order_by(Agent.created_at.desc())
    )
    agents = result.scalars().all()
    return [AgentResponse.model_validate(a) for a in agents]


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    data: CreateAgentRequest,
    user: User = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    agent = Agent(
        creator_id=user.id,
        name=data.name,
        slug=slugify(data.name),
        description=data.description,
        short_description=data.short_description,
        category_id=data.category_id,
        icon=data.icon,
        tags=data.tags,
        pricing_type=data.pricing_type,
        price_per_execution=data.price_per_execution or 0,
        visibility=AgentVisibility(data.visibility),
        status=AgentStatus.DRAFT,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    # Only creator or admin can see non-public agents
    if agent.creator_id != user.id and not user.is_admin:
        if agent.visibility != AgentVisibility.PUBLIC or agent.status != AgentStatus.APPROVED:
            raise HTTPException(status_code=403, detail="Access denied")
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: UpdateAgentRequest,
    user: User = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.creator_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.post("/{agent_id}/versions", status_code=201)
async def create_agent_version(
    agent_id: str,
    data: AgentVersionRequest,
    user: User = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.creator_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get next version number
    existing = await db.execute(
        select(AgentVersion).where(AgentVersion.agent_id == agent_id).order_by(AgentVersion.version_number.desc())
    )
    last = existing.scalars().first()
    next_version = (last.version_number + 1) if last else 1

    version = AgentVersion(
        agent_id=agent_id,
        version_number=next_version,
        **data.model_dump(exclude_none=False),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return {"id": version.id, "version_number": version.version_number}


@router.post("/{agent_id}/submit-review", response_model=SuccessResponse)
async def submit_for_review(
    agent_id: str,
    user: User = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.creator_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if agent.status not in (AgentStatus.DRAFT, AgentStatus.REJECTED):
        raise HTTPException(status_code=400, detail=f"Cannot submit agent in '{agent.status}' status")

    agent.status = AgentStatus.PENDING_REVIEW
    await db.commit()
    return SuccessResponse(message="Agent submitted for review")
