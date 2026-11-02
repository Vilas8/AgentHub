"""Core execution service — orchestrates agent runs."""
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentVersion
from app.models.execution import Execution, ExecutionStatus, ExecutionStep
from app.services.ai_adapters import get_model_adapter

logger = structlog.get_logger(__name__)

# In-memory SSE event queues keyed by execution_id
_event_queues: dict[str, asyncio.Queue] = {}


class ExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_execution(self, user_id: str, agent: Agent, input_data: dict) -> Execution:
        execution = Execution(
            user_id=user_id,
            agent_id=agent.id,
            agent_version_id=agent.current_version_id,
            status=ExecutionStatus.QUEUED,
            input_data=input_data,
            correlation_id=str(uuid.uuid4()),
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)

        # Create SSE queue
        _event_queues[execution.id] = asyncio.Queue()
        logger.info("Execution created", execution_id=execution.id, agent_id=agent.id)
        return execution

    async def run_execution(self, execution_id: str) -> None:
        """Background task that runs the actual agent execution."""
        from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
        bind = self.db.get_bind()
        if not isinstance(bind, AsyncEngine):
            bind = AsyncEngine(bind)
        session_factory = async_sessionmaker(bind, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as db:
            try:
                result = await db.execute(select(Execution).where(Execution.id == execution_id))
                execution = result.scalar_one_or_none()
                if not execution:
                    logger.error("Execution not found", execution_id=execution_id)
                    return

                await self._update_status(db, execution, ExecutionStatus.INITIALIZING)

                # Load agent version
                version = None
                if execution.agent_version_id:
                    v_result = await db.execute(select(AgentVersion).where(AgentVersion.id == execution.agent_version_id))
                    version = v_result.scalar_one_or_none()

                a_result = await db.execute(select(Agent).where(Agent.id == execution.agent_id))
                agent = a_result.scalar_one_or_none()
                if not agent:
                    raise ValueError("Agent not found")

                await self._update_status(db, execution, ExecutionStatus.RUNNING)
                start_time = time.time()
                execution.started_at = datetime.now(timezone.utc).isoformat()

                # Run the agent
                output = await self._execute_agent(db, execution, agent, version)

                execution.status = ExecutionStatus.COMPLETED
                execution.output_data = output
                execution.completed_at = datetime.now(timezone.utc).isoformat()
                execution.duration_seconds = round(time.time() - start_time, 3)

                # Update agent execution count
                agent.total_executions = (agent.total_executions or 0) + 1

                await db.commit()
                await self._emit_event(execution_id, "completed", {"output": output})
                logger.info("Execution completed", execution_id=execution_id)

            except asyncio.TimeoutError:
                await self._handle_failure(db, execution_id, ExecutionStatus.TIMED_OUT, "Execution timed out")
            except Exception as exc:
                logger.exception("Execution failed", execution_id=execution_id, error=str(exc))
                await self._handle_failure(db, execution_id, ExecutionStatus.FAILED, str(exc))
            finally:
                _event_queues.pop(execution_id, None)

    async def _execute_agent(self, db: AsyncSession, execution: Execution, agent: Agent, version: AgentVersion | None) -> dict:
        """Execute agent using AI model adapter."""
        provider = "gemini"
        model_name = "gemini-1.5-flash"
        system_prompt = "You are a helpful AI assistant."

        if version:
            provider = version.model_provider
            model_name = version.model_name
            system_prompt = version.system_prompt or system_prompt

        adapter = get_model_adapter(provider)

        input_text = ""
        if isinstance(execution.input_data, dict):
            input_text = execution.input_data.get("text", "") or execution.input_data.get("query", "") or json.dumps(execution.input_data)
        else:
            input_text = str(execution.input_data)

        step = ExecutionStep(
            execution_id=execution.id,
            step_number=1,
            step_type="llm_call",
            status="running",
            model_name=model_name,
        )
        db.add(step)
        await db.flush()

        await self._emit_event(execution.id, "step_started", {"step": 1, "type": "llm_call"})

        try:
            response = await asyncio.wait_for(
                adapter.complete(
                    system_prompt=system_prompt,
                    user_message=input_text,
                    model=model_name,
                    max_tokens=version.max_tokens if version else 4096,
                    temperature=float(version.temperature) if version else 0.7,
                ),
                timeout=version.max_duration_seconds if version else 300,
            )

            step.status = "completed"
            step.output_data = {"text": response.content}
            step.input_tokens = response.input_tokens
            step.output_tokens = response.output_tokens

            execution.input_tokens = response.input_tokens
            execution.output_tokens = response.output_tokens
            execution.model_provider = provider
            execution.model_name = model_name

            await db.flush()
            await self._emit_event(execution.id, "step_completed", {"step": 1, "output": response.content[:200]})

            return {"text": response.content, "model": model_name, "provider": provider}

        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            await db.flush()
            raise

    async def _update_status(self, db: AsyncSession, execution: Execution, status: ExecutionStatus):
        execution.status = status
        await db.flush()
        await self._emit_event(execution.id, "status_change", {"status": status.value})

    async def _handle_failure(self, db: AsyncSession, execution_id: str, status: ExecutionStatus, error: str):
        async with db.begin_nested():
            result = await db.execute(select(Execution).where(Execution.id == execution_id))
            execution = result.scalar_one_or_none()
            if execution:
                execution.status = status
                execution.error_message = error
                execution.completed_at = datetime.now(timezone.utc).isoformat()
        await db.commit()
        await self._emit_event(execution_id, "failed", {"error": error, "status": status.value})

    async def _emit_event(self, execution_id: str, event_type: str, data: dict):
        queue = _event_queues.get(execution_id)
        if queue:
            event = {"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}
            await queue.put(event)

    async def stream_execution_events(self, execution_id: str) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted events for an execution."""
        queue = _event_queues.get(execution_id)
        if not queue:
            # Execution may already be done — send final state
            result = await self.db.execute(select(Execution).where(Execution.id == execution_id))
            execution = result.scalar_one_or_none()
            if execution:
                yield f"data: {json.dumps({'type': 'status', 'data': {'status': execution.status.value}})}\n\n"
            return

        timeout = 300  # 5 minutes max
        start = time.time()

        while time.time() - start < timeout:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event["type"] in ("completed", "failed", "cancelled", "timed_out"):
                    break
            except asyncio.TimeoutError:
                # Send keepalive
                yield ": keepalive\n\n"
