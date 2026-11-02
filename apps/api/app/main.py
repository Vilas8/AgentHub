"""AgentHub FastAPI application entry point."""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging
from app.database.base import engine, Base
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.api.v1.router import api_router

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("AgentHub API starting", env=settings.APP_ENV)

    # Create tables (idempotent for SQLite dev; Alembic handles Postgres)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial data
    from app.database.base import AsyncSessionLocal
    from app.database.init_db import init_db
    async with AsyncSessionLocal() as db:
        await init_db(db)

    logger.info("AgentHub API ready")
    yield

    logger.info("AgentHub API shutting down")
    await engine.dispose()


app = FastAPI(
    title="AgentHub API",
    description="Production-grade AI Agent Marketplace API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.APP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred."},
    )


from app.api.v1.routers.health import router as health_router

app.include_router(health_router, tags=["health"])
app.include_router(api_router)
