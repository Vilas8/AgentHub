"""Human-in-the-loop Execution Approvals Router."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import get_db
from app.models.user import User
from app.models.execution import Execution, ExecutionStatus, ExecutionApproval, ApprovalStatus
from app.schemas.common import SuccessResponse
from app.api.deps import get_current_active_user

router = APIRouter()


@router.get("/pending", response_model=list)
async def list_pending_approvals(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExecutionApproval)
        .where(
            ExecutionApproval.user_id == user.id,
            ExecutionApproval.status == ApprovalStatus.PENDING,
        )
        .order_by(ExecutionApproval.created_at.desc())
    )
    approvals = result.scalars().all()
    return [
        {
            "id": a.id,
            "execution_id": a.execution_id,
            "tool_name": a.tool_name,
            "action_description": a.action_description,
            "payload": a.payload,
            "status": a.status.value,
            "created_at": a.created_at.isoformat(),
        }
        for a in approvals
    ]


@router.post("/{approval_id}/approve", response_model=SuccessResponse)
async def approve_action(
    approval_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ExecutionApproval).where(ExecutionApproval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Approval is no longer pending")

    approval.status = ApprovalStatus.APPROVED
    approval.decision_at = datetime.now(timezone.utc).isoformat()

    # Resume execution if awaiting approval
    exec_res = await db.execute(select(Execution).where(Execution.id == approval.execution_id))
    execution = exec_res.scalar_one_or_none()
    if execution and execution.status == ExecutionStatus.AWAITING_APPROVAL:
        execution.status = ExecutionStatus.RUNNING

    await db.commit()
    return SuccessResponse(message="Action approved. Execution resuming.")


@router.post("/{approval_id}/reject", response_model=SuccessResponse)
async def reject_action(
    approval_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ExecutionApproval).where(ExecutionApproval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Approval is no longer pending")

    approval.status = ApprovalStatus.REJECTED
    approval.decision_at = datetime.now(timezone.utc).isoformat()

    exec_res = await db.execute(select(Execution).where(Execution.id == approval.execution_id))
    execution = exec_res.scalar_one_or_none()
    if execution and execution.status == ExecutionStatus.AWAITING_APPROVAL:
        execution.status = ExecutionStatus.FAILED
        execution.error_message = f"User rejected sensitive action: {approval.tool_name}"

    await db.commit()
    return SuccessResponse(message="Action rejected.")
