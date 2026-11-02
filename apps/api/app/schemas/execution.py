"""Execution schemas."""
from typing import Any
from app.schemas.common import BaseSchema


class CreateExecutionRequest(BaseSchema):
    agent_id: str
    input_data: dict[str, Any]
    idempotency_key: str | None = None


class ExecutionResponse(BaseSchema):
    id: str
    user_id: str
    agent_id: str
    agent_version_id: str | None = None
    status: str
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost_minor: int = 0
    model_provider: str | None = None
    model_name: str | None = None


class ExecutionStepResponse(BaseSchema):
    id: str
    step_number: int
    step_type: str
    status: str
    tool_name: str | None = None
    model_name: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    error_message: str | None = None
    requires_approval: bool = False
