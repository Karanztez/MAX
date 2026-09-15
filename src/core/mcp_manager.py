"""
mcp_manager.py — Model Context Protocol (MCP) Client & Tool Manager for MaxPlus AI

รองรับ:
- การเชื่อมต่อ MCP Server ผ่าน JSON-RPC 2.0 (stdio)
- ค้นหาเครื่องมือ (tools/list) และแปลงเป็น OpenAI/Gemini function calling schema
- เรียกใช้งานเครื่องมือ (tools/call) พร้อม timeout ป้องกันค้างบน Windows
- Built-in toolset เพื่อให้ทดสอบระบบ Tool Calling ได้ทันทีโดยไม่ต้องติดตั้ง Server เพิ่ม
- จัดเก็บและโหลดคอนฟิกจาก mcp_servers.json
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str = "builtin"

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert MCP tool schema to OpenAI / Gemini compatible function definition."""
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


class MCPServerConnection:
    """Manages an individual MCP server process over stdio using JSON-RPC 2.0."""

    def __init__(self, name: str, command: str, args: list[str], env: Optional[dict[str, str]] = None,
                 timeout: float = 15.0):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.timeout = timeout
        self.process: Optional[subprocess.Popen[str]] = None
        self._msg_id = 0
        self._lock = threading.Lock()
        self._response_queues: dict[int, queue.Queue[dict[str, Any]]] = {}
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self.tools: list[MCPTool] = []
        self.is_connected = False
        self.error_message = ""

    def start(self) -> bool:
        """Start subprocess and perform MCP initialize handshake."""
        with self._lock:
            if self.is_connected and self.process and self.process.poll() is None:
                return True
            self.stop()
            self.error_message = ""
            full_env = os.environ.copy()
            full_env.update(self.env)
            full_cmd = [self.command] + self.args
            try:
                self.process = subprocess.Popen(
                    full_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    bufsize=1,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                self._running = True
                self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
                self._reader_thread.start()

                # Step 1: initialize handshake
                init_res = self._send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "MaxPlusAI", "version": "1.0.0"},
                })
                if "error" in init_res:
                    raise RuntimeError(f"Handshake error: {init_res['error']}")

                # Step 2: notifications/initialized
                self._send_notification("notifications/initialized", {})

                # Step 3: discover tools
                self.refresh_tools()
                self.is_connected = True
                return True
            except Exception as ex:
                self.error_message = str(ex)
                self.stop()
                return False

    def stop(self) -> None:
        """Gracefully terminate MCP server subprocess."""
        self._running = False
        self.is_connected = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1.5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def _read_stdout(self) -> None:
        """Background thread reading JSON-RPC responses from server stdout."""
        assert self.process is not None and self.process.stdout is not None
        while self._running and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    req_id = data.get("id")
                    if req_id in self._response_queues:
                        self._response_queues[req_id].put(data)
                except json.JSONDecodeError:
                    continue
            except Exception:
                break
        self.is_connected = False

    def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send JSON-RPC request and wait synchronously with timeout."""
        if not self.process or self.process.poll() is not None or not self.process.stdin:
            raise RuntimeError(f"MCP server '{self.name}' is not running")

        with self._lock:
            self._msg_id += 1
            req_id = self._msg_id
            resp_q: queue.Queue[dict[str, Any]] = queue.Queue()
            self._response_queues[req_id] = resp_q

        msg = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        try:
            self.process.stdin.write(msg + "\n")
            self.process.stdin.flush()
        except Exception as ex:
            with self._lock:
                self._response_queues.pop(req_id, None)
            raise RuntimeError(f"Failed to write to MCP server '{self.name}': {ex}") from ex

        try:
            resp = resp_q.get(timeout=self.timeout)
            return resp
        except queue.Empty:
            raise TimeoutError(f"MCP request '{method}' to '{self.name}' timed out after {self.timeout}s")
        finally:
            with self._lock:
                self._response_queues.pop(req_id, None)

    def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send JSON-RPC notification (no response expected)."""
        if not self.process or self.process.poll() is not None or not self.process.stdin:
            return
        msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params})
        try:
            self.process.stdin.write(msg + "\n")
            self.process.stdin.flush()
        except Exception:
            pass

    def refresh_tools(self) -> list[MCPTool]:
        """Call tools/list to fetch all tools from this MCP server."""
        resp = self._send_request("tools/list", {})
        if "error" in resp:
            raise RuntimeError(f"tools/list error: {resp['error']}")
        result = resp.get("result", {})
        tool_items = result.get("tools", [])
        self.tools = [
            MCPTool(
                name=item.get("name", "unnamed"),
                description=item.get("description", ""),
                input_schema=item.get("inputSchema", {}),
                server_name=self.name,
            )
            for item in tool_items if isinstance(item, dict)
        ]
        return self.tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute tool via tools/call and return text representation."""
        resp = self._send_request("tools/call", {"name": name, "arguments": arguments})
        if "error" in resp:
            return f"Error: {resp['error']}"
        result = resp.get("result", {})
        content_items = result.get("content", [])
        outputs = []
        for item in content_items:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    outputs.append(str(item.get("text", "")))
                elif item.get("type") == "image":
                    outputs.append("[Image data returned]")
                else:
                    outputs.append(json.dumps(item, ensure_ascii=False))
            else:
                outputs.append(str(item))
        return "\n".join(outputs) if outputs else json.dumps(result, ensure_ascii=False)


# ─── Built-in Default Tools ───────────────────────────────────────────────────

def _builtin_calc(expression: str) -> str:
    """Safe basic math evaluator."""
    allowed = set("0123456789+-*/().,% eE")
    if not all(ch in allowed for ch in expression):
        return "Error: Expression contains invalid characters"
    try:
        # safe eval of basic math expressions
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as ex:
        return f"Calculation error: {ex}"


def _builtin_datetime() -> str:
    """Get current local date and time."""
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S (%Z)")


def _builtin_sysinfo() -> str:
    """Get basic OS and Python information."""
    import platform
    return f"OS: {platform.system()} {platform.release()} ({platform.architecture()[0]})\nPython: {sys.version}"


class MCPManager:
    """Central manager for MCP servers, built-in tools, and function calling integration."""

    DEFAULT_CONFIG_NAME = "mcp_servers.json"

    def __init__(self, config_path: Optional[Path] = None):
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
        """Register safe built-in tools ready for immediate usage."""
        self.builtin_tools["calculate"] = (
            MCPTool(
                name="calculate",
                description="คำนวณนิพจน์ทางคณิตศาสตร์อย่างปลอดภัย เช่น 25 * 40 หรือ (120 - 45) / 5",
                input_schema={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "นิพจน์คณิตศาสตร์ที่ต้องการคำนวณ"}
                    },
                    "required": ["expression"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_calc(str(args.get("expression", ""))),
        )
        self.builtin_tools["get_current_time"] = (
            MCPTool(
                name="get_current_time",
                description="ดึงวันและเวลาปัจจุบันของระบบท้องถิ่น",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin",
            ),
            lambda _args: _builtin_datetime(),
        )
        self.builtin_tools["get_system_info"] = (
            MCPTool(
                name="get_system_info",
                description="ดึงข้อมูลระบบปฏิบัติการและเวอร์ชัน Python ของเครื่องที่รันอยู่",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin",
            ),
            lambda _args: _builtin_sysinfo(),
        )

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
