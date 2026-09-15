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
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as ex:
        return f"Calculation error: {ex}"


def _builtin_datetime() -> str:
    """Get current local date and time."""
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S (%Z)")


def _builtin_sysinfo() -> str:
    """Get basic OS, CPU architecture, and Python information."""
    import platform
    return f"OS: {platform.system()} {platform.release()} ({platform.architecture()[0]})\nPython: {sys.version}\nCWD: {os.getcwd()}"


def _builtin_search_web(query: str, count: int = 5) -> str:
    """Search the web via DuckDuckGo and return search results with title, link, and summary."""
    import urllib.parse
    import urllib.request
    import re

    query = query.strip()
    if not query:
        return "Error: Query is empty"
    count = max(1, min(int(count or 5), 10))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
    }

    # Attempt 1: DuckDuckGo HTML Search
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Parse results from HTML
        results = []
        # Pattern for result snippets in DDG HTML
        # <a class="result__snippet" ...>...</a>
        # <a class="result__url" href="...">...</a>
        # <a class="result__a" ...>...</a>
        snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
        links = re.findall(r'<a[^>]+class="[^"]*result__url[^"]*"[^>]+href="([^"]+)"', html)
        titles = re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)

        for i in range(min(count, len(titles))):
            title = re.sub(r"<[^>]+>", "", titles[i]).strip()
            link = links[i].strip() if i < len(links) else ""
            if link.startswith("//duckduckgo.com/l/?uddg="):
                link = urllib.parse.unquote(link.split("uddg=")[-1].split("&")[0])
            elif not link.startswith("http") and link:
                link = "https://" + link.lstrip("/")
            snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
            results.append(f"{i+1}. {title}\n   URL: {link}\n   Snippet: {snippet}")

        if results:
            return f"ผลการค้นหาเว็บสำหรับ '{query}':\n\n" + "\n\n".join(results)
    except Exception as ex:
        pass

    # Attempt 2: DuckDuckGo Instant Answer API Fallback
    try:
        api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(api_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        results = []
        abstract = data.get("AbstractText")
        abstract_url = data.get("AbstractURL")
        if abstract:
            results.append(f"1. {data.get('Heading', query)}\n   URL: {abstract_url}\n   Summary: {abstract}")

        related = data.get("RelatedTopics", [])
        for topic in related[:count]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append(f"• {topic.get('Text')}\n   URL: {topic.get('FirstURL', '')}")

        if results:
            return f"ผลการค้นหาสำหรับ '{query}':\n\n" + "\n\n".join(results)
    except Exception as ex:
        return f"เกิดข้อผิดพลาดในการค้นหาเว็บ: {ex}"

    return f"ไม่พบผลการค้นหาสำหรับ '{query}'"


def _builtin_fetch_web(url: str, max_length: int = 8000) -> str:
    """Fetch content of a webpage, parse and extract clean readable text."""
    import urllib.request
    import urllib.parse
    import html
    import re

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,text/plain,application/json;q=0.9,*/*;q=0.8",
    }
    max_length = max(500, min(int(max_length or 8000), 30000))

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw_bytes = resp.read()

        # Handle charset
        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].split(";")[0].strip()

        try:
            text = raw_bytes.decode(charset, errors="replace")
        except Exception:
            text = raw_bytes.decode("utf-8", errors="replace")

        # Strip styles, scripts, head, nav, svg
        text = re.sub(r"<(script|style|head|svg|noscript|iframe|nav|footer|header)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Convert links to markdown
        text = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)
        # Convert headers and formatting
        text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n### \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
        # Remove remaining tags
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text).strip()

        if len(text) > max_length:
            text = text[:max_length] + f"\n\n... [เนื้อหาถูกตัดทอน แสดง {max_length} ตัวอักษรแรก]"

        return f"=== เนื้อหาจาก {url} ===\n\n{text}" if text else f"ไม่พบเนื้อหาข้อความบนหน้าเว็บ {url}"
    except Exception as ex:
        return f"ไม่สามารถเปิดหน้าเว็บ {url} ได้: {ex}"


def _builtin_list_dir(path: str = ".", max_depth: int = 2) -> str:
    """List directory contents up to a specified depth."""
    target = Path(path).resolve()
    if not target.exists():
        return f"Error: Path '{path}' does not exist"
    if not target.is_dir():
        return f"Error: '{path}' is a file, not a directory"

    lines = [f"Directory: {target}"]
    base_depth = len(target.parts)

    try:
        items_count = 0
        for root, dirs, files in os.walk(target):
            depth = len(Path(root).parts) - base_depth
            if depth > max_depth:
                dirs.clear()
                continue
            # Skip common heavy/hidden folders
            dirs[:] = [d for d in dirs if not d.startswith((".", "__pycache__", "node_modules", "venv", ".git"))]
            indent = "  " * depth
            rel_root = os.path.relpath(root, target)
            if rel_root != ".":
                lines.append(f"{indent}📁 {os.path.basename(root)}/")
            for f in sorted(files):
                if items_count > 200:
                    lines.append(f"{indent}  ... (แสดงผลสูงสุด 200 รายการ)")
                    return "\n".join(lines)
                f_path = Path(root) / f
                try:
                    size = f_path.stat().st_size
                    size_str = f"{size} B" if size < 1024 else f"{size/1024:.1f} KB"
                except Exception:
                    size_str = "?"
                lines.append(f"{indent}  📄 {f} ({size_str})")
                items_count += 1
        return "\n".join(lines)
    except Exception as ex:
        return f"Error listing directory '{path}': {ex}"


def _builtin_read_file(path: str, start_line: int = 1, line_count: int = 200) -> str:
    """Read lines of a file with line numbers."""
    target = Path(path).resolve()
    if not target.exists():
        return f"Error: File '{path}' does not exist"
    if not target.is_file():
        return f"Error: '{path}' is a directory, not a file"

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)
        start = max(1, int(start_line or 1))
        count = max(1, min(int(line_count or 200), 1000))
        end = min(start + count - 1, total_lines)

        slice_lines = lines[start - 1 : end]
        output = [f"File: {target} (Lines {start}-{end} of {total_lines})"]
        for idx, line in enumerate(slice_lines, start=start):
            output.append(f"{idx:4d} | {line}")
        return "\n".join(output)
    except Exception as ex:
        return f"Error reading file '{path}': {ex}"


def _builtin_write_file(path: str, content: str, overwrite: bool = True) -> str:
    """Write or overwrite text content to a file."""
    target = Path(path).resolve()
    if target.exists() and not overwrite:
        return f"Error: File '{path}' already exists and overwrite is False"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"สำเร็จ: บันทึกไฟล์ '{target}' เรียบร้อย ({len(content)} ตัวอักษร, {len(content.splitlines())} บรรทัด)"
    except Exception as ex:
        return f"Error writing file '{path}': {ex}"


def _builtin_search_files(query: str, path: str = ".", is_regex: bool = False, file_glob: str = "*") -> str:
    """Search for text or regex patterns in files."""
    import re
    target = Path(path).resolve()
    if not target.exists():
        return f"Error: Path '{path}' does not exist"

    matches = []
    flags = re.IGNORECASE
    try:
        pattern = re.compile(query, flags) if is_regex else None
    except Exception as ex:
        return f"Invalid regex pattern: {ex}"

    files_searched = 0
    max_matches = 50

    try:
        search_root = target if target.is_dir() else target.parent
        for root, dirs, files in os.walk(search_root):
            dirs[:] = [d for d in dirs if not d.startswith((".", "__pycache__", "node_modules", "venv", ".git"))]
            for f in files:
                if not Path(f).match(file_glob):
                    continue
                file_path = Path(root) / f
                files_searched += 1
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    for line_no, line in enumerate(text.splitlines(), start=1):
                        found = bool(pattern.search(line)) if pattern else (query.lower() in line.lower())
                        if found:
                            rel = os.path.relpath(file_path, search_root)
                            matches.append(f"{rel}:{line_no}: {line.strip()[:150]}")
                            if len(matches) >= max_matches:
                                break
                except Exception:
                    continue
                if len(matches) >= max_matches:
                    break
            if len(matches) >= max_matches:
                break

        if not matches:
            return f"ไม่พบข้อความ '{query}' ใน {files_searched} ไฟล์ที่ค้นหา"
        summary = f"พบ {len(matches)} จุด (ค้นหาจาก {files_searched} ไฟล์):\n\n"
        return summary + "\n".join(matches)
    except Exception as ex:
        return f"Error searching in files: {ex}"


def _builtin_run_command(command: str, cwd: str = ".", timeout_seconds: int = 30) -> str:
    """Run a safe CLI command and return stdout/stderr output without hanging."""
    command = command.strip()
    if not command:
        return "Error: Command is empty"

    timeout = max(1, min(int(timeout_seconds or 30), 120))
    target_cwd = str(Path(cwd).resolve())

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=target_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        code = proc.returncode

        res = [f"Exit Code: {code}"]
        if out:
            res.append(f"STDOUT:\n{out}")
        if err:
            res.append(f"STDERR:\n{err}")
        if not out and not err:
            res.append("(No output produced)")
        return "\n\n".join(res)
    except subprocess.TimeoutExpired:
        return f"Error: คำสั่งถูกยกเลิกเนื่องจาก Timeout ({timeout} วินาที)"
    except Exception as ex:
        return f"Error running command: {ex}"


def _builtin_run_python(code: str, timeout_seconds: int = 15) -> str:
    """Execute Python code in an isolated subprocess and return output."""
    import tempfile
    code = code.strip()
    if not code:
        return "Error: Code is empty"

    timeout = max(1, min(int(timeout_seconds or 15), 60))

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(code)
        temp_path = temp_file.name

    try:
        proc = subprocess.run(
            [sys.executable, temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        res = []
        if out:
            res.append(f"Output:\n{out}")
        if err:
            res.append(f"Errors/Traceback:\n{err}")
        if not out and not err:
            res.append("Python script executed successfully with no console output.")
        return "\n\n".join(res)
    except subprocess.TimeoutExpired:
        return f"Error: Python script timed out after {timeout} seconds"
    except Exception as ex:
        return f"Error executing Python code: {ex}"
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass


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
        # 1. Search Web
        self.builtin_tools["search_web"] = (
            MCPTool(
                name="search_web",
                description="ค้นหาข้อมูลบนอินเทอร์เน็ตผ่าน Search Engine (คืนค่าหัวข้อ ลิงก์ และคำอธิบายย่อ)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "คำค้นหาหรือสิ่งที่ต้องการสืบค้น"},
                        "count": {"type": "integer", "description": "จำนวนผลลัพธ์ที่ต้องการ (ค่าเริ่มต้น 5, สูงสุด 10)", "default": 5},
                    },
                    "required": ["query"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_search_web(str(args.get("query", "")), count=int(args.get("count", 5))),
        )

        # 2. Fetch Web Page Content
        self.builtin_tools["fetch_web_content"] = (
            MCPTool(
                name="fetch_web_content",
                description="เปิดอ่านเนื้อหาหน้าเว็บหรือดึงข้อมูลจาก URL (แปลง HTML เป็นข้อความสะอาดที่อ่านง่าย)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL ของหน้าเว็บที่ต้องการอ่าน เช่น https://example.com"},
                        "max_length": {"type": "integer", "description": "ความยาวตัวอักษรสูงสุดที่ต้องการดึง (ค่าเริ่มต้น 8000)", "default": 8000},
                    },
                    "required": ["url"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_fetch_web(str(args.get("url", "")), max_length=int(args.get("max_length", 8000))),
        )

        # 3. List Directory
        self.builtin_tools["list_directory"] = (
            MCPTool(
                name="list_directory",
                description="แสดงโครงสร้างโฟลเดอร์และไฟล์ในโฟลเดอร์ที่กำหนด (Workspace / Project tree)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของโฟลเดอร์ (ค่าเริ่มต้นคือ . หรือโฟลเดอร์ปัจจุบัน)", "default": "."},
                        "max_depth": {"type": "integer", "description": "ระดับความลึกสูงสุดของโฟลเดอร์ย่อย (ค่าเริ่มต้น 2)", "default": 2},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_list_dir(str(args.get("path", ".")), max_depth=int(args.get("max_depth", 2))),
        )

        # 4. Read File
        self.builtin_tools["read_file"] = (
            MCPTool(
                name="read_file",
                description="อ่านเนื้อหาไฟล์โค้ดหรือไฟล์ข้อความในเครื่อง พร้อมระบุบรรทัด",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์ที่ต้องการอ่าน"},
                        "start_line": {"type": "integer", "description": "บรรทัดเริ่มต้น (ค่าเริ่มต้น 1)", "default": 1},
                        "line_count": {"type": "integer", "description": "จำนวนบรรทัดที่ต้องการอ่าน (ค่าเริ่มต้น 200)", "default": 200},
                    },
                    "required": ["path"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_read_file(
                str(args.get("path", "")),
                start_line=int(args.get("start_line", 1)),
                line_count=int(args.get("line_count", 200)),
            ),
        )

        # 5. Write File
        self.builtin_tools["write_file"] = (
            MCPTool(
                name="write_file",
                description="สร้างหรือแก้ไขบันทึกไฟล์ข้อความ/โค้ดในโปรเจกต์",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์ที่ต้องการเขียน"},
                        "content": {"type": "string", "description": "เนื้อหาข้อความหรือโค้ดที่ต้องการบันทึก"},
                        "overwrite": {"type": "boolean", "description": "อนุญาตให้เขียนทับไฟล์เดิมหรือไม่ (ค่าเริ่มต้น True)", "default": True},
                    },
                    "required": ["path", "content"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_write_file(
                str(args.get("path", "")),
                str(args.get("content", "")),
                overwrite=bool(args.get("overwrite", True)),
            ),
        )

        # 6. Search Files
        self.builtin_tools["search_files"] = (
            MCPTool(
                name="search_files",
                description="ค้นหาข้อความหรือ Regular Expression ในไฟล์ต่างๆ ในโปรเจกต์ (Grep / Search)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "ข้อความหรือ regex ที่ต้องการค้นหา"},
                        "path": {"type": "string", "description": "โฟลเดอร์เริ่มต้นค้นหา (ค่าเริ่มต้น .)", "default": "."},
                        "is_regex": {"type": "boolean", "description": "ค้นหาด้วย Regex หรือไม่", "default": False},
                        "file_glob": {"type": "string", "description": "รูปแบบชื่อไฟล์ เช่น *.py, *.md, * (ค่าเริ่มต้น *)", "default": "*"},
                    },
                    "required": ["query"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_search_files(
                str(args.get("query", "")),
                path=str(args.get("path", ".")),
                is_regex=bool(args.get("is_regex", False)),
                file_glob=str(args.get("file_glob", "*")),
            ),
        )

        # 7. Run Shell Command
        self.builtin_tools["run_command"] = (
            MCPTool(
                name="run_command",
                description="รันคำสั่ง Terminal / Shell (PowerShell / Command Prompt) บนเครื่อง และรับ stdout/stderr",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "คำสั่ง CLI ที่ต้องการรัน เช่น git status, dir, pip list"},
                        "cwd": {"type": "string", "description": "ไดเรกทอรีที่ต้องการรันคำสั่ง (ค่าเริ่มต้น .)", "default": "."},
                        "timeout_seconds": {"type": "integer", "description": "Timeout สูงสุดเป็นวินาที (ค่าเริ่มต้น 30)", "default": 30},
                    },
                    "required": ["command"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_run_command(
                str(args.get("command", "")),
                cwd=str(args.get("cwd", ".")),
                timeout_seconds=int(args.get("timeout_seconds", 30)),
            ),
        )

        # 8. Run Python Code
        self.builtin_tools["run_python_code"] = (
            MCPTool(
                name="run_python_code",
                description="รันโค้ด Python ในสภาพแวดล้อมที่แยกส่วน และคืนค่าผลลัพธ์ที่พิมพ์ออกมา (Print output)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "สคริปต์ Python ที่ต้องการรัน"},
                        "timeout_seconds": {"type": "integer", "description": "Timeout สูงสุดเป็นวินาที (ค่าเริ่มต้น 15)", "default": 15},
                    },
                    "required": ["code"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_run_python(
                str(args.get("code", "")),
                timeout_seconds=int(args.get("timeout_seconds", 15)),
            ),
        )

        # 9. Math Calculator
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

        # 10. Current DateTime
        self.builtin_tools["get_current_time"] = (
            MCPTool(
                name="get_current_time",
                description="ดึงวันและเวลาปัจจุบันของระบบท้องถิ่น",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin",
            ),
            lambda _args: _builtin_datetime(),
        )

        # 11. System Info
        self.builtin_tools["get_system_info"] = (
            MCPTool(
                name="get_system_info",
                description="ดึงข้อมูลระบบปฏิบัติการ เวอร์ชัน Python และไดเรกทอรีทำงานปัจจุบัน",
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
