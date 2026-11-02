"""Agent registry routes — creator facing."""
import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import get_db
from app.models.user import User
from app.models.agent import Agent, AgentVersion, AgentStatus, AgentVisibility
from app.schemas.agent import (
    CreateAgentRequest,
    UpdateAgentRequest,
    AgentVersionRequest,
    AgentVersionResponse,
    AgentResponse,
)
from app.schemas.common import SuccessResponse
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


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: CreateAgentRequest,
    user: User = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    try:
        vis = AgentVisibility(data.visibility)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid visibility: {data.visibility}")

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
        visibility=vis,
        status=AgentStatus.DRAFT,
    )
    db.add(agent)
    await db.flush()  # assign agent.id

    # Transactional initial version creation
    initial_prompt = data.system_prompt or f"You are {data.name}, an expert AI assistant."
    version = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        system_prompt=initial_prompt,
        objective=data.short_description or data.description,
        model_provider=data.model_provider,
        model_name=data.model_name,
        tools_config=data.tools_config or {},
    )
    db.add(version)

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    
    # Non-admin non-creator can only view approved public agents
    if agent.creator_id != user.id and not user.is_admin:
        if agent.visibility != AgentVisibility.PUBLIC or agent.status != AgentStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.creator_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this agent")

    updates = data.model_dump(exclude_none=True)
    if not updates:
        return AgentResponse.model_validate(agent)

    # Protect status transitions and visibility rules
    if "visibility" in updates:
        try:
            updates["visibility"] = AgentVisibility(updates["visibility"])
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid visibility")

    for field, value in updates.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}/versions", response_model=list[AgentVersionResponse])
async def list_agent_versions(
    agent_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.creator_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    v_result = await db.execute(
        select(AgentVersion).where(AgentVersion.agent_id == agent_id).order_by(AgentVersion.version_number.desc())
    )
    versions = v_result.scalars().all()
    return [AgentVersionResponse.model_validate(v) for v in versions]


@router.post("/{agent_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_agent_version(
    agent_id: str,
    data: AgentVersionRequest,
    user: User = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.creator_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this agent")

    # Immutable versions: each new version gets next sequence number
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.creator_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this agent")
    if agent.status not in (AgentStatus.DRAFT, AgentStatus.REJECTED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot submit agent in '{agent.status}' status")

    agent.status = AgentStatus.PENDING_REVIEW
    await db.commit()
    return SuccessResponse(message="Agent submitted for review")

