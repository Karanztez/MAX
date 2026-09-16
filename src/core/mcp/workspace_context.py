"""Shared working-directory context for project-aware MCP tools."""

from __future__ import annotations

from pathlib import Path


_workspace_root = Path.cwd().resolve()


def set_workspace_root(path: str | Path) -> Path:
    """Set and return the directory used by relative project tool paths."""
    global _workspace_root
    candidate = Path(path).expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Workspace directory does not exist: {candidate}")
    if not candidate.is_dir():
        raise NotADirectoryError(f"Workspace path is not a directory: {candidate}")
    _workspace_root = candidate
    return _workspace_root


def get_workspace_root() -> Path:
    """Return the active project directory."""
    return _workspace_root


def resolve_workspace_path(path: str | Path) -> Path:
    """Resolve relative paths from the active project directory."""
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = _workspace_root / candidate
    return candidate.resolve()
