"""Aggregates all built-in tools for MCPManager."""

from __future__ import annotations

from typing import Any

from .file_tools import get_file_tools
from .git_tools import get_git_tools
from .media_tools import get_media_tools
from .skill_tools import get_skill_tools
from .system_tools import get_system_tools
from .web_tools import get_web_tools


def get_all_builtin_tools() -> dict[str, tuple[Any, Any]]:
    """Aggregate and return all built-in tools across all categories."""
    tools: dict[str, tuple[Any, Any]] = {}
    tools.update(get_web_tools())
    tools.update(get_file_tools())
    tools.update(get_system_tools())
    tools.update(get_media_tools())
    tools.update(get_git_tools())
    tools.update(get_skill_tools())
    return tools
