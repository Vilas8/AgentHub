"""
Standalone AgentHub Execution Worker.
Polls for queued executions and processes them safely in background processes.
"""
from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path

# Add apps/api to sys.path so worker can share models and services
api_path = Path(__file__).resolve().parent.parent.parent / "apps" / "api"
if str(api_path) not in sys.path:
    sys.path.insert(0, str(api_path))

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.execution import Execution, ExecutionStatus
from app.services.execution_service import ExecutionService

logger = structlog.get_logger("execution_worker")

shutdown_event = asyncio.Event()


def handle_shutdown(signum, frame):
    logger.info("Shutdown signal received", signal=signum)
    shutdown_event.set()


async def process_queued_executions(session_factory: async_sessionmaker[AsyncSession]):
    """Poll and run pending executions."""
    async with session_factory() as db:
        stmt = (
            select(Execution.id)
            .where(Execution.status == ExecutionStatus.QUEUED)
            .order_by(Execution.created_at.asc())
            .limit(5)
        )
        res = await db.execute(stmt)
        execution_ids = res.scalars().all()

    if not execution_ids:
        return 0

    logger.info("Found queued executions", count=len(execution_ids))
    for exec_id in execution_ids:
        if shutdown_event.is_set():
            break
        async with session_factory() as db:
            service = ExecutionService(db)
            try:
                await service.run_execution(exec_id)
            except Exception as e:
                logger.exception("Worker failed processing execution", execution_id=exec_id, error=str(e))

    return len(execution_ids)


async def main():
    logger.info("Starting AgentHub Standalone Execution Worker...", poll_interval=2.0)
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        while not shutdown_event.is_set():
            processed = await process_queued_executions(session_factory)
            if processed == 0:
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    pass
    finally:
        logger.info("Execution Worker shutting down cleanly.")
        await engine.dispose()


if __name__ == "__main__":
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_shutdown)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, handle_shutdown)

    asyncio.run(main())
