"""Public marketplace routes."""
import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.api.deps import get_current_active_user
from app.database.base import get_db
from app.models.agent import Agent, AgentBookmark, AgentReview, AgentStatus, AgentVisibility
from app.models.user import User
from app.schemas.agent import AgentResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/agents", response_model=PaginatedResponse)
async def list_marketplace_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    category_id: str | None = None,
    pricing_type: str | None = None,
    sort: str = Query("newest", pattern="^(newest|popular|rating)$"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Agent).where(
        Agent.status == AgentStatus.APPROVED,
        Agent.visibility == AgentVisibility.PUBLIC,
    )

    if search:
        query = query.where(
            or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%"),
            )
        )
    if category_id:
        query = query.where(Agent.category_id == category_id)
    if pricing_type:
        query = query.where(Agent.pricing_type == pricing_type)

    if sort == "popular":
        query = query.order_by(Agent.total_executions.desc())
    elif sort == "rating":
        query = query.order_by(Agent.average_rating.desc())
    else:
        query = query.order_by(Agent.created_at.desc())

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    agents = result.scalars().all()

    return PaginatedResponse(
        items=[AgentResponse.model_validate(a) for a in agents],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_marketplace_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.status == AgentStatus.APPROVED,
            Agent.visibility == AgentVisibility.PUBLIC,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.get("/agents/{agent_id}/reviews")
async def list_agent_reviews(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentReview).where(AgentReview.agent_id == agent_id).order_by(AgentReview.created_at.desc()).limit(50)
    )
    reviews = result.scalars().all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]


@router.post("/agents/{agent_id}/reviews", status_code=status.HTTP_201_CREATED)
async def create_agent_review(
    agent_id: str,
    payload: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify agent exists and is publicly accessible
    agent_res = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.status == AgentStatus.APPROVED,
            Agent.visibility == AgentVisibility.PUBLIC,
        )
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not available for review",
        )

    # Enforce one review per user per agent
    existing_rev = await db.execute(
        select(AgentReview).where(
            AgentReview.agent_id == agent_id,
            AgentReview.user_id == current_user.id,
        )
    )
    if existing_rev.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a review for this agent",
        )

    try:
        rating = int(payload.get("rating", 5))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be an integer between 1 and 5")

    if not 1 <= rating <= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 1 and 5")

    comment = str(payload.get("comment", "")).strip()[:1000]

    review = AgentReview(
        agent_id=agent_id,
        user_id=current_user.id,
        rating=rating,
        comment=comment,
    )
    db.add(review)
    await db.flush()

    # Recalculate average rating & review count using DB aggregates
    stats_query = select(
        func.count(AgentReview.id),
        func.avg(AgentReview.rating),
    ).where(AgentReview.agent_id == agent_id)
    count, avg_rating = (await db.execute(stats_query)).one()

    agent.review_count = count or 0
    agent.average_rating = round(float(avg_rating), 2) if avg_rating is not None else 0.0

    await db.commit()
    await db.refresh(review)

    return {
        "id": review.id,
        "agent_id": agent.id,
        "rating": review.rating,
        "comment": review.comment,
        "average_rating": agent.average_rating,
        "review_count": agent.review_count,
        "message": "Review submitted successfully",
    }


@router.post("/agents/{agent_id}/bookmark")
async def toggle_bookmark(
    agent_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify agent exists
    agent_res = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.status == AgentStatus.APPROVED,
            Agent.visibility == AgentVisibility.PUBLIC,
        )
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    result = await db.execute(
        select(AgentBookmark).where(
            AgentBookmark.agent_id == agent_id,
            AgentBookmark.user_id == current_user.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
        return {"bookmarked": False, "message": "Bookmark removed"}

    bm = AgentBookmark(agent_id=agent_id, user_id=current_user.id)
    db.add(bm)
    await db.commit()
    return {"bookmarked": True, "message": "Agent saved to bookmarks"}


@router.get("/bookmarks")
async def list_user_bookmarks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Agent)
        .join(AgentBookmark, AgentBookmark.agent_id == Agent.id)
        .where(AgentBookmark.user_id == current_user.id)
        .order_by(AgentBookmark.created_at.desc())
    )
    result = await db.execute(stmt)
    agents = result.scalars().all()
    return [AgentResponse.model_validate(a) for a in agents]

