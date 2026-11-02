"""Execution routes."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import get_db
from app.models.user import User
from app.models.agent import Agent, AgentStatus, AgentVisibility
from app.models.execution import Execution, ExecutionStatus
from app.schemas.execution import CreateExecutionRequest, ExecutionResponse
from app.schemas.common import SuccessResponse
from app.api.deps import get_current_active_user
from app.services.execution_service import ExecutionService

router = APIRouter()


@router.post("/", response_model=ExecutionResponse, status_code=201)
async def create_execution(
    data: CreateExecutionRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify agent exists and is accessible
    result = await db.execute(select(Agent).where(Agent.id == data.agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status != AgentStatus.APPROVED and agent.creator_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Agent is not available")

    service = ExecutionService(db)
    execution = await service.create_execution(user_id=user.id, agent=agent, input_data=data.input_data)
    background_tasks.add_task(service.run_execution, execution.id)

    return ExecutionResponse.model_validate(execution)


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Execution).where(Execution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return ExecutionResponse.model_validate(execution)


@router.get("/", response_model=list[ExecutionResponse])
async def list_executions(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Execution).where(Execution.user_id == user.id).order_by(Execution.created_at.desc()).limit(50)
    )
    executions = result.scalars().all()
    return [ExecutionResponse.model_validate(e) for e in executions]


@router.get("/{execution_id}/stream")
async def stream_execution(
    execution_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events stream for live execution updates."""
    result = await db.execute(select(Execution).where(Execution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.services.execution_service import ExecutionService
    service = ExecutionService(db)

    async def event_generator():
        async for event in service.stream_execution_events(execution_id):
            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{execution_id}/cancel", response_model=SuccessResponse)
async def cancel_execution(
    execution_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Execution).where(Execution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    if execution.status not in (ExecutionStatus.QUEUED, ExecutionStatus.RUNNING, ExecutionStatus.AWAITING_APPROVAL):
        raise HTTPException(status_code=400, detail="Execution cannot be cancelled in current state")

    execution.status = ExecutionStatus.CANCELLED
    await db.commit()
    return SuccessResponse(message="Execution cancelled")
