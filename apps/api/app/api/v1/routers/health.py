"""Health check endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database.base import get_db

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "agenthub-api"}


@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ready" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
    }
