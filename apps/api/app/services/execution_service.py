"""Core execution service — orchestrates agent runs with persistent events and cancellation."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker
from sqlalchemy import select

from app.models.agent import Agent, AgentVersion
from app.models.billing import Purchase
from app.models.execution import Execution, ExecutionEvent, ExecutionStatus, ExecutionStep
from app.services.ai_adapters import get_model_adapter

logger = structlog.get_logger(__name__)

# Broadcast subscribers keyed by execution_id: set of asyncio.Queue instances
_execution_subscribers: dict[str, set[asyncio.Queue]] = {}
# Cooperative cancellation flags keyed by execution_id
_cancellation_events: dict[str, asyncio.Event] = {}
# Monotonic sequence counter for execution events
_event_sequences: dict[str, int] = {}


class ExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_execution(
        self,
        user_id: str,
        agent: Agent,
        input_data: dict,
        purchase: Purchase | None = None,
    ) -> Execution:
        execution = Execution(
            user_id=user_id,
            agent_id=agent.id,
            agent_version_id=agent.current_version_id,
            status=ExecutionStatus.QUEUED,
            input_data=input_data,
            correlation_id=str(uuid.uuid4()),
        )
        self.db.add(execution)
        await self.db.flush()

        # If this execution required a per-run purchase, consume it atomically
        if purchase:
            purchase.execution_id = execution.id

        # Initialize event sequence and cancellation flag
        _cancellation_events[execution.id] = asyncio.Event()
        _event_sequences[execution.id] = 0

        # Record initial creation event
        await self._record_and_broadcast_event(
            self.db,
            execution.id,
            "created",
            {"status": ExecutionStatus.QUEUED.value, "agent_id": agent.id},
        )

        await self.db.commit()
        await self.db.refresh(execution)

        logger.info("Execution created", execution_id=execution.id, agent_id=agent.id)
        return execution

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cooperatively cancel a running or queued execution."""
        if execution_id in _cancellation_events:
            _cancellation_events[execution_id].set()

        result = await self.db.execute(select(Execution).where(Execution.id == execution_id))
        execution = result.scalar_one_or_none()
        if not execution:
            return False

        if execution.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMED_OUT,
        ):
            return False

        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc).isoformat()

        await self._record_and_broadcast_event(
            self.db,
            execution_id,
            "cancelled",
            {"message": "Execution cancelled by user", "status": ExecutionStatus.CANCELLED.value},
        )
        await self.db.commit()
        return True

    async def run_execution(self, execution_id: str) -> None:
        """Background task that runs the actual agent execution."""
        bind = self.db.get_bind()
        if not isinstance(bind, AsyncEngine):
            bind = AsyncEngine(bind)
        session_factory = async_sessionmaker(bind, class_=AsyncSession, expire_on_commit=False)

        cancel_ev = _cancellation_events.get(execution_id)

        async with session_factory() as db:
            try:
                result = await db.execute(select(Execution).where(Execution.id == execution_id))
                execution = result.scalar_one_or_none()
                if not execution:
                    logger.error("Execution not found", execution_id=execution_id)
                    return

                # Check if cancelled before initialization
                if cancel_ev and cancel_ev.is_set():
                    return

                await self._update_status(db, execution, ExecutionStatus.INITIALIZING)

                # Load agent and version
                version = None
                if execution.agent_version_id:
                    v_result = await db.execute(select(AgentVersion).where(AgentVersion.id == execution.agent_version_id))
                    version = v_result.scalar_one_or_none()

                a_result = await db.execute(select(Agent).where(Agent.id == execution.agent_id))
                agent = a_result.scalar_one_or_none()
                if not agent:
                    raise ValueError("Agent not found")

                if cancel_ev and cancel_ev.is_set():
                    return

                await self._update_status(db, execution, ExecutionStatus.RUNNING)
                start_time = time.time()
                execution.started_at = datetime.now(timezone.utc).isoformat()

                # Run the agent
                output = await self._execute_agent(db, execution, agent, version, cancel_ev)

                # Final cancellation check
                if cancel_ev and cancel_ev.is_set():
                    return

                execution.status = ExecutionStatus.COMPLETED
                execution.output_data = output
                execution.completed_at = datetime.now(timezone.utc).isoformat()
                execution.duration_seconds = round(time.time() - start_time, 3)

                # Update agent execution count
                agent.total_executions = (agent.total_executions or 0) + 1

                await self._record_and_broadcast_event(
                    db,
                    execution_id,
                    "completed",
                    {"output": output, "status": ExecutionStatus.COMPLETED.value},
                )
                await db.commit()
                logger.info("Execution completed successfully", execution_id=execution_id)

            except asyncio.CancelledError:
                logger.info("Execution cancelled asynchronously", execution_id=execution_id)
                await self._handle_failure(db, execution_id, ExecutionStatus.CANCELLED, "Execution cancelled")
            except asyncio.TimeoutError:
                logger.warning("Execution timed out", execution_id=execution_id)
                await self._handle_failure(db, execution_id, ExecutionStatus.TIMED_OUT, "Execution timed out")
            except Exception as exc:
                logger.exception("Execution failed", execution_id=execution_id, error=str(exc))
                await self._handle_failure(db, execution_id, ExecutionStatus.FAILED, str(exc))
            finally:
                _cancellation_events.pop(execution_id, None)

    async def _execute_agent(
        self,
        db: AsyncSession,
        execution: Execution,
        agent: Agent,
        version: AgentVersion | None,
        cancel_ev: asyncio.Event | None,
    ) -> dict:
        """Execute agent using AI model adapter with cooperative cancellation."""
        provider = "gemini"
        model_name = "gemini-1.5-flash"
        system_prompt = f"You are {agent.name}, an AI assistant."

        if version:
            provider = version.model_provider
            model_name = version.model_name
            system_prompt = version.system_prompt or system_prompt

        adapter = get_model_adapter(provider)

        input_text = ""
        if isinstance(execution.input_data, dict):
            input_text = execution.input_data.get("text", "") or execution.input_data.get("query", "") or json.dumps(execution.input_data)
        else:
            input_text = str(execution.input_data or "")

        step = ExecutionStep(
            execution_id=execution.id,
            step_number=1,
            step_type="llm_call",
            status="running",
            model_name=model_name,
        )
        db.add(step)
        await db.flush()

        await self._record_and_broadcast_event(
            db,
            execution.id,
            "step_started",
            {"step": 1, "type": "llm_call", "model": model_name},
        )
        await db.commit()

        if cancel_ev and cancel_ev.is_set():
            step.status = "cancelled"
            await db.commit()
            raise asyncio.CancelledError()

        try:
            timeout_sec = version.max_duration_seconds if (version and version.max_duration_seconds) else 300
            response = await asyncio.wait_for(
                adapter.complete(
                    system_prompt=system_prompt,
                    user_message=input_text,
                    model=model_name,
                    max_tokens=version.max_tokens if version else 4096,
                    temperature=float(version.temperature) if version else 0.7,
                ),
                timeout=timeout_sec,
            )

            step.status = "completed"
            step.output_data = {"text": response.content}
            step.input_tokens = response.input_tokens
            step.output_tokens = response.output_tokens

            execution.input_tokens = response.input_tokens
            execution.output_tokens = response.output_tokens
            execution.model_provider = provider
            execution.model_name = model_name

            await self._record_and_broadcast_event(
                db,
                execution.id,
                "step_completed",
                {
                    "step": 1,
                    "tokens": response.input_tokens + response.output_tokens,
                    "preview": response.content[:160],
                },
            )
            await db.commit()

            return {
                "text": response.content,
                "model": model_name,
                "provider": provider,
                "tokens": {"input": response.input_tokens, "output": response.output_tokens},
            }

        except Exception as e:
            step.status = "failed"
            step.error_message = str(e)
            await db.commit()
            raise

    async def _update_status(self, db: AsyncSession, execution: Execution, status: ExecutionStatus):
        execution.status = status
        await db.flush()
        await self._record_and_broadcast_event(db, execution.id, "status_change", {"status": status.value})
        await db.commit()

    async def _handle_failure(self, db: AsyncSession, execution_id: str, status: ExecutionStatus, error: str):
        try:
            result = await db.execute(select(Execution).where(Execution.id == execution_id))
            execution = result.scalar_one_or_none()
            if execution:
                execution.status = status
                execution.error_message = error
                execution.completed_at = datetime.now(timezone.utc).isoformat()
                await self._record_and_broadcast_event(
                    db,
                    execution_id,
                    "failed",
                    {"error": error, "status": status.value},
                )
                await db.commit()
        except Exception as e:
            logger.error("Failed to record execution failure state", error=str(e))

    async def _record_and_broadcast_event(
        self,
        db: AsyncSession,
        execution_id: str,
        event_type: str,
        data: dict,
    ):
        seq = _event_sequences.get(execution_id, 0) + 1
        _event_sequences[execution_id] = seq

        # Persist event to DB
        evt = ExecutionEvent(
            execution_id=execution_id,
            sequence=seq,
            event_type=event_type,
            data=data,
        )
        db.add(evt)

        # Broadcast to active SSE listeners
        payload = {
            "id": seq,
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        subscribers = _execution_subscribers.get(execution_id, set())
        for q in list(subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    async def stream_execution_events(
        self,
        execution_id: str,
        last_event_id: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Yield SSE-formatted events for an execution.
        Supports replay from last_event_id and real-time subscription.
        """
        # 1. Replay historical events from DB if any
        history_query = (
            select(ExecutionEvent)
            .where(ExecutionEvent.execution_id == execution_id)
            .order_by(ExecutionEvent.sequence.asc())
        )
        if last_event_id is not None:
            history_query = history_query.where(ExecutionEvent.sequence > last_event_id)

        hist_res = await self.db.execute(history_query)
        historical_events = hist_res.scalars().all()

        last_yielded_seq = last_event_id or 0
        for ev in historical_events:
            last_yielded_seq = max(last_yielded_seq, ev.sequence)
            yield f"id: {ev.sequence}\nevent: {ev.event_type}\ndata: {json.dumps(ev.data or {})}\n\n"
            if ev.event_type in ("completed", "failed", "cancelled", "timed_out"):
                return

        # 2. Check if execution is already terminated
        exec_res = await self.db.execute(select(Execution).where(Execution.id == execution_id))
        execution = exec_res.scalar_one_or_none()
        if not execution or execution.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMED_OUT,
        ):
            yield f"event: final\ndata: {json.dumps({'status': execution.status.value if execution else 'unknown'})}\n\n"
            return

        # 3. Subscribe to real-time events
        queue = asyncio.Queue()
        if execution_id not in _execution_subscribers:
            _execution_subscribers[execution_id] = set()
        _execution_subscribers[execution_id].add(queue)

        timeout = 300
        start = time.time()

        try:
            while time.time() - start < timeout:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    seq = event.get("id", 0)
                    if seq <= last_yielded_seq:
                        continue
                    last_yielded_seq = seq
                    yield f"id: {seq}\nevent: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
                    if event["type"] in ("completed", "failed", "cancelled", "timed_out"):
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            subs = _execution_subscribers.get(execution_id)
            if subs and queue in subs:
                subs.remove(queue)
                if not subs:
                    _execution_subscribers.pop(execution_id, None)
