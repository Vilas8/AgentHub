"""Agent schemas."""
from typing import Any
from pydantic import field_validator, model_validator
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

    # Optional initial version configuration
    system_prompt: str | None = None
    model_provider: str = "gemini"
    model_name: str = "gemini-1.5-flash"
    tools_config: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Agent name must be at least 3 characters")
        return v

    @field_validator("pricing_type")
    @classmethod
    def validate_pricing_type(cls, v: str) -> str:
        valid = {"free", "per_execution", "subscription"}
        if v not in valid:
            raise ValueError(f"pricing_type must be one of {valid}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        valid = {"public", "unlisted", "private"}
        if v not in valid:
            raise ValueError(f"visibility must be one of {valid}")
        return v

    @field_validator("price_per_execution")
    @classmethod
    def validate_price(cls, v: int) -> int:
        if v < 0:
            raise ValueError("price_per_execution cannot be negative")
        if v > 100_000_000:
            raise ValueError("price_per_execution exceeds maximum allowed value")
        return v

    @model_validator(mode="after")
    def validate_free_price(self):
        if self.pricing_type == "free" and self.price_per_execution > 0:
            raise ValueError("Free agents cannot have a price_per_execution greater than 0")
        if self.pricing_type == "per_execution" and self.price_per_execution <= 0:
            raise ValueError("per_execution agents must specify a price_per_execution greater than 0")
        return self


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

    @field_validator("pricing_type")
    @classmethod
    def validate_pricing_type(cls, v: str | None) -> str | None:
        if v is not None:
            valid = {"free", "per_execution", "subscription"}
            if v not in valid:
                raise ValueError(f"pricing_type must be one of {valid}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str | None) -> str | None:
        if v is not None:
            valid = {"public", "unlisted", "private"}
            if v not in valid:
                raise ValueError(f"visibility must be one of {valid}")
        return v

    @field_validator("price_per_execution")
    @classmethod
    def validate_price(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("price_per_execution cannot be negative")
        return v


class AgentVersionResponse(BaseSchema):
    id: str
    agent_id: str
    version_number: int
    system_prompt: str
    objective: str | None = None
    model_provider: str
    model_name: str
    temperature: float
    max_tokens: int
    max_steps: int
    max_duration_seconds: int
    tools_config: dict[str, Any] | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    change_notes: str | None = None
    created_at: Any


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

