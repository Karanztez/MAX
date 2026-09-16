"""Central MCPManager coordinating built-in tools and connected external MCP servers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from .builtins import get_all_builtin_tools
    from .connection import MCPServerConnection
    from .types import MCPTool
    from .workspace_context import get_workspace_root, set_workspace_root
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.builtins import get_all_builtin_tools  # type: ignore[no-redef]
    from src.core.mcp.connection import MCPServerConnection  # type: ignore[no-redef]
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]
    from src.core.mcp.workspace_context import get_workspace_root, set_workspace_root  # type: ignore[no-redef]


class MCPManager:
    """Central manager for MCP servers, built-in tools, and function calling integration."""

    DEFAULT_CONFIG_NAME = "mcp_servers.json"

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if config_path:
            self.config_path = config_path
        else:
            appdata = os.environ.get("APPDATA")
            if appdata:
                base = Path(appdata) / "MaxPlusAI"
                base.mkdir(parents=True, exist_ok=True)
                self.config_path = base / self.DEFAULT_CONFIG_NAME
            else:
                self.config_path = Path(self.DEFAULT_CONFIG_NAME)

        self.servers: dict[str, MCPServerConnection] = {}
        self.server_configs: dict[str, dict[str, Any]] = {}
        self.builtin_tools: dict[str, tuple[MCPTool, Callable[..., str]]] = {}
        self.enabled = True

        self._register_builtins()
        self.load_config()

    def _register_builtins(self) -> None:
        """Register all modular built-in tools."""
        self.builtin_tools = get_all_builtin_tools()

    def set_workspace_root(self, path: str | Path) -> Path:
        """Point all relative built-in tool paths at the selected project."""
        return set_workspace_root(path)

    @property
    def workspace_root(self) -> Path:
        return get_workspace_root()

    def load_config(self) -> None:
        """Load server configurations from JSON file."""
        if not self.config_path.exists():
            self.server_configs = {
                "servers": {}
            }
            self.save_config()
            return
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.server_configs = data if isinstance(data, dict) else {"servers": {}}
        except Exception:
            self.server_configs = {"servers": {}}

    def save_config(self) -> None:
        """Persist server configurations to JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(self.server_configs, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def add_server(self, name: str, command: str, args: list[str],
                   env: Optional[dict[str, str]] = None, enabled: bool = True) -> None:
        """Add or update an MCP server configuration."""
        if "servers" not in self.server_configs:
            self.server_configs["servers"] = {}
        self.server_configs["servers"][name] = {
            "command": command,
            "args": args,
            "env": env or {},
            "enabled": enabled,
        }
        self.save_config()

    def remove_server(self, name: str) -> None:
        """Remove an MCP server from configuration and stop connection."""
        if name in self.servers:
            self.servers[name].stop()
            del self.servers[name]
        if "servers" in self.server_configs and name in self.server_configs["servers"]:
            del self.server_configs["servers"][name]
            self.save_config()

    def connect_server(self, name: str) -> bool:
        """Connect to a specific configured MCP server."""
        servers_cfg = self.server_configs.get("servers", {})
        if name not in servers_cfg:
            return False
        cfg = servers_cfg[name]
        conn = MCPServerConnection(
            name=name,
            command=cfg.get("command", ""),
            args=cfg.get("args", []),
            env=cfg.get("env", {}),
        )
        ok = conn.start()
        self.servers[name] = conn
        return ok

    def disconnect_server(self, name: str) -> None:
        """Disconnect an MCP server."""
        if name in self.servers:
            self.servers[name].stop()

    def connect_all_enabled(self) -> dict[str, bool]:
        """Connect all enabled configured servers."""
        results: dict[str, bool] = {}
        for name, cfg in self.server_configs.get("servers", {}).items():
            if cfg.get("enabled", True):
                results[name] = self.connect_server(name)
        return results

    def disconnect_all(self) -> None:
        """Disconnect all active MCP servers."""
        for server in self.servers.values():
            server.stop()
        self.servers.clear()

    def get_all_tools(self) -> list[MCPTool]:
        """Return list of all available tools across builtins and active servers."""
        if not self.enabled:
            return []
        tools: list[MCPTool] = [tool for tool, _func in self.builtin_tools.values()]
        for server in self.servers.values():
            if server.is_connected:
                tools.extend(server.tools)
        return tools

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Return tools formatted for OpenAI / Gemini function calling payload."""
        return [t.to_openai_tool() for t in self.get_all_tools()]

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute tool by name and return string result."""
        if name in self.builtin_tools:
            _tool, func = self.builtin_tools[name]
            try:
                return func(arguments)
            except Exception as ex:
                return f"Error executing builtin tool '{name}': {ex}"

        for server in self.servers.values():
            if server.is_connected:
                for tool in server.tools:
                    if tool.name == name:
                        return server.call_tool(name, arguments)

        return f"Error: Tool '{name}' not found or its server is not connected."
