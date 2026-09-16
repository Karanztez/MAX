"""Data types and schemas for Model Context Protocol (MCP)."""

from __future__ import annotations

import copy
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
        schema: dict[str, Any] = copy.deepcopy(self.input_schema or {})
        if "type" not in schema:
            schema["type"] = "object"
        if "properties" not in schema or not isinstance(schema["properties"], dict):
            schema["properties"] = {}

        def _sanitize(node: Any) -> None:
            if not isinstance(node, dict):
                return
            if node.get("type") == "object":
                if "properties" not in node and "additionalProperties" not in node:
                    node["additionalProperties"] = True
                elif "properties" in node and isinstance(node["properties"], dict):
                    for _pk, pv in node["properties"].items():
                        _sanitize(pv)
            elif node.get("type") == "array":
                if "items" in node:
                    _sanitize(node["items"])
            for _k, v in list(node.items()):
                if isinstance(v, dict):
                    _sanitize(v)

        _sanitize(schema)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            }
        }

