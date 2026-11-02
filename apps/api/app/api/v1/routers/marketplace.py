"""Public marketplace routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database.base import get_db
from app.models.agent import Agent, AgentStatus, AgentVisibility
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

    import math
    return PaginatedResponse(
        items=[AgentResponse.model_validate(a) for a in agents],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_marketplace_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.status == AgentStatus.APPROVED,
            Agent.visibility == AgentVisibility.PUBLIC,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.get("/agents/{agent_id}/reviews")
async def list_agent_reviews(agent_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.agent import AgentReview
    result = await db.execute(
        select(AgentReview).where(AgentReview.agent_id == agent_id).order_by(AgentReview.created_at.desc()).limit(50)
    )
    reviews = result.scalars().all()
    return [
        {
            "id": r.id,
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]


@router.post("/agents/{agent_id}/reviews")
async def create_agent_review(
    agent_id: str,
    payload: dict,
    user=Depends(lambda: None),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    from app.models.agent import AgentReview
    from app.api.deps import get_current_active_user
    
    # Authenticate user
    current_user = await get_current_active_user(user) if user else None
    user_id = current_user.id if current_user else "anonymous"

    rating = int(payload.get("rating", 5))
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    review = AgentReview(
        agent_id=agent_id,
        user_id=user_id,
        rating=rating,
        comment=payload.get("comment", ""),
    )
    db.add(review)

    # Recalculate average rating
    all_revs = await db.execute(select(AgentReview.rating).where(AgentReview.agent_id == agent_id))
    ratings = all_revs.scalars().all()
    ratings.append(rating)
    new_avg = sum(ratings) / len(ratings)

    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()
    if agent:
        agent.average_rating = round(new_avg, 2)
        agent.review_count = len(ratings)

    await db.commit()
    return {"message": "Review submitted successfully", "average_rating": agent.average_rating if agent else rating}


@router.post("/agents/{agent_id}/bookmark")
async def toggle_bookmark(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    from app.models.agent import AgentBookmark
    # Toggle bookmark
    result = await db.execute(select(AgentBookmark).where(AgentBookmark.agent_id == agent_id))
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
        return {"bookmarked": False, "message": "Bookmark removed"}
    else:
        bm = AgentBookmark(agent_id=agent_id, user_id="guest-or-user")
        db.add(bm)
        await db.commit()
        return {"bookmarked": True, "message": "Agent saved to bookmarks"}
