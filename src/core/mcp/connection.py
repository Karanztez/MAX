"""MCPServerConnection — Manages JSON-RPC 2.0 communication over stdio with an MCP Server."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from typing import Any, Optional

try:
    from .types import MCPTool
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]


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
                    "clientInfo": {"name": "MaxPlusAI", "version": "1.0.8"},
                })
                if not init_res or "error" in init_res:
                    err = init_res.get("error", {}).get("message", "Handshake failed") if init_res else "Timeout"
                    self.error_message = f"MCP Initialize failed: {err}"
                    self.stop()
                    return False

                # Step 2: send initialized notification
                self._send_notification("notifications/initialized", {})

                # Step 3: discover available tools
                self.refresh_tools()
                self.is_connected = True
                return True
            except FileNotFoundError:
                self.error_message = f"Executable '{self.command}' not found on system."
                self.stop()
                return False
            except Exception as ex:
                self.error_message = f"Failed to start server '{self.name}': {ex}"
                self.stop()
                return False

    def stop(self) -> None:
        """Terminate subprocess cleanly."""
        self._running = False
        self.is_connected = False
        self.tools = []
        if self.process:
            try:
                self.process.stdin.close()  # type: ignore[union-attr]
            except Exception:
                pass
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def refresh_tools(self) -> list[MCPTool]:
        """Fetch list of tools exported by this server."""
        res = self._send_request("tools/list", {})
        if not res or "result" not in res:
            return []
        raw_tools = res["result"].get("tools", [])
        self.tools = [
            MCPTool(
                name=t.get("name", "unnamed"),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
                server_name=self.name,
            )
            for t in raw_tools
        ]
        return self.tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call a specific tool on the server and return text content result."""
        res = self._send_request("tools/call", {"name": name, "arguments": arguments})
        if not res:
            return f"Error: Tool '{name}' timed out after {self.timeout}s on server '{self.name}'."
        if "error" in res:
            err = res["error"]
            return f"Error ({err.get('code')}): {err.get('message', 'Unknown error')}"

        result = res.get("result", {})
        content = result.get("content", [])
        if isinstance(content, list):
            texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            if texts:
                return "\n".join(texts)
        if isinstance(result, dict) and "text" in result:
            return str(result["text"])
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _send_request(self, method: str, params: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not self.process or not self.process.stdin or self.process.poll() is not None:
            return None
        with self._lock:
            self._msg_id += 1
            req_id = self._msg_id
            q: queue.Queue[dict[str, Any]] = queue.Queue()
            self._response_queues[req_id] = q

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        try:
            line = json.dumps(payload) + "\n"
            self.process.stdin.write(line)
            self.process.stdin.flush()
        except Exception:
            with self._lock:
                self._response_queues.pop(req_id, None)
            return None

        try:
            return q.get(timeout=self.timeout)
        except queue.Empty:
            return None
        finally:
            with self._lock:
                self._response_queues.pop(req_id, None)

    def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin or self.process.poll() is not None:
            return
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        try:
            line = json.dumps(payload) + "\n"
            self.process.stdin.write(line)
            self.process.stdin.flush()
        except Exception:
            pass

    def _read_stdout(self) -> None:
        """Background thread reading stdio lines from MCP subprocess."""
        if not self.process or not self.process.stdout:
            return
        while self._running and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if isinstance(data, dict) and "id" in data:
                    req_id = data["id"]
                    with self._lock:
                        q = self._response_queues.get(req_id)
                    if q:
                        q.put(data)
            except Exception:
                break
        self.is_connected = False
