"""Agent schemas."""
from typing import Any
from pydantic import field_validator
from app.schemas.common import BaseSchema


class AgentResponse(BaseSchema):
    id: str
    name: str
    slug: str
    description: str
    short_description: str | None = None
    icon: str | None = None
    tags: list[str] | None = None
    status: str
    visibility: str
    pricing_type: str
    price_per_execution: int = 0
    total_executions: int = 0
    average_rating: float = 0.0
    review_count: int = 0
    is_platform_owned: bool = False
    creator_id: str
    category_id: str | None = None


class CreateAgentRequest(BaseSchema):
    name: str
    description: str
    short_description: str | None = None
    category_id: str | None = None
    icon: str | None = None
    tags: list[str] | None = None
    pricing_type: str = "free"
    price_per_execution: int = 0
    visibility: str = "private"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Agent name must be at least 3 characters")
        return v


class UpdateAgentRequest(BaseSchema):
    name: str | None = None
    description: str | None = None
    short_description: str | None = None
    category_id: str | None = None
    icon: str | None = None
    tags: list[str] | None = None
    pricing_type: str | None = None
    price_per_execution: int | None = None
    visibility: str | None = None


class AgentVersionRequest(BaseSchema):
    system_prompt: str
    objective: str | None = None
    model_provider: str = "gemini"
    model_name: str = "gemini-1.5-flash"
    temperature: float = 0.7
    max_tokens: int = 4096
    max_steps: int = 10
    max_duration_seconds: int = 300
    tools_config: dict[str, Any] | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    change_notes: str | None = None


class CategoryResponse(BaseSchema):
    id: str
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
