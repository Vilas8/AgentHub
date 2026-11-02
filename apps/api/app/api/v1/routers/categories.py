"""Category routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import get_db
from app.models.category import Category
from app.schemas.agent import CategoryResponse

router = APIRouter()


@router.get("/", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
    )
    cats = result.scalars().all()
    return [CategoryResponse.model_validate(c) for c in cats]
