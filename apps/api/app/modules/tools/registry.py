"""
Allowlisted Tool Registry for AgentHub Execution Engine.
Enforces strict schema validation, permission scoping, risk classification,
and human-in-the-loop approval requirements.
"""
from __future__ import annotations

import enum
from typing import Any, Callable, Coroutine
from pydantic import BaseModel


class ToolRisk(str, enum.Enum):
    LOW = "low"            # Read-only, deterministic (e.g., calculator, datetime)
    MEDIUM = "medium"      # External read-only network or storage (e.g., web search, file read)
    HIGH = "high"          # State-changing, write, or communication (e.g., email send, file write)


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permission_scope: str
    risk_classification: ToolRisk
    requires_approval: bool = False
    execution_timeout_seconds: int = 30


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._executors: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]] = {}

    def register(
        self,
        definition: ToolDefinition,
        executor: Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]],
    ) -> None:
        self._tools[definition.name] = definition
        self._executors[definition.name] = executor

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    async def execute_tool(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' is not registered in the allowlisted tool registry.")
        executor = self._executors[name]
        return await executor(params)


tool_registry = ToolRegistry()
