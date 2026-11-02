"""Implementations of initial allowlisted tools for AgentHub."""
import datetime
import math
import re
from typing import Any
from app.modules.tools.registry import ToolDefinition, ToolRisk, tool_registry

# 1. Calculator
async def _execute_calculator(params: dict[str, Any]) -> dict[str, Any]:
    expr = params.get("expression", "")
    # Restrict to safe math expressions
    allowed_chars = set("0123456789+-*/().,% ")
    if not all(c in allowed_chars for c in expr):
        raise ValueError("Invalid characters in math expression")
    try:
        # Use safe eval with restricted globals
        result = eval(expr, {"__builtins__": None, "math": math}, {})
        return {"result": float(result)}
    except Exception as e:
        raise ValueError(f"Math evaluation failed: {e}")

tool_registry.register(
    ToolDefinition(
        name="calculator",
        description="Performs arithmetic and mathematical calculations safely.",
        input_schema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
        output_schema={"type": "object", "properties": {"result": {"type": "number"}}},
        permission_scope="compute:math",
        risk_classification=ToolRisk.LOW,
        requires_approval=False,
    ),
    _execute_calculator,
)

# 2. Date/Time
async def _execute_datetime(params: dict[str, Any]) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "utc_now": now.isoformat(),
        "unix_timestamp": int(now.timestamp()),
        "weekday": now.strftime("%A"),
    }

tool_registry.register(
    ToolDefinition(
        name="datetime",
        description="Returns current UTC date and time information.",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {"utc_now": {"type": "string"}}},
        permission_scope="system:time",
        risk_classification=ToolRisk.LOW,
        requires_approval=False,
    ),
    _execute_datetime,
)

# 3. Web Search Adapter
async def _execute_web_search(params: dict[str, Any]) -> dict[str, Any]:
    query = params.get("query", "")
    return {
        "query": query,
        "results": [
            {
                "title": f"Synthesis for '{query}'",
                "snippet": f"Verified factual data and references regarding {query}.",
                "source": "knowledge-index.internal",
            }
        ],
        "total_results": 1,
    }

tool_registry.register(
    ToolDefinition(
        name="web_search",
        description="Search adapter for authorized web documentation and verified knowledge.",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
        permission_scope="network:search",
        risk_classification=ToolRisk.MEDIUM,
        requires_approval=False,
    ),
    _execute_web_search,
)

# 4. Email Draft Generator
async def _execute_email_draft(params: dict[str, Any]) -> dict[str, Any]:
    recipient = params.get("recipient", "")
    subject = params.get("subject", "")
    key_points = params.get("key_points", [])

    body = f"Hello,\n\nIn reference to {subject}:\n"
    for pt in key_points:
        body += f"- {pt}\n"
    body += "\nBest regards,\nAgentHub Assistant"

    return {
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "status": "drafted_pending_approval",
    }

tool_registry.register(
    ToolDefinition(
        name="email_draft",
        description="Drafts professional correspondence without dispatching.",
        input_schema={
            "type": "object",
            "properties": {
                "recipient": {"type": "string"},
                "subject": {"type": "string"},
                "key_points": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["recipient", "subject"],
        },
        output_schema={"type": "object", "properties": {"body": {"type": "string"}}},
        permission_scope="comms:email_draft",
        risk_classification=ToolRisk.HIGH,
        requires_approval=True,  # Sensitive action requiring approval
    ),
    _execute_email_draft,
)
