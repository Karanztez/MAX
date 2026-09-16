"""Data types and schemas for Model Context Protocol (MCP)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class MCPTool:
    """Represents an individual tool definition compatible with MCP and AI function calling."""
    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str = "builtin"

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert tool schema to standard OpenAI / Gemini function definition."""
        schema = self.input_schema or {}
        if "type" not in schema:
            schema["type"] = "object"
        if "properties" not in schema:
            schema["properties"] = {}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            }
        }
