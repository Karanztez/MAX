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
                    "clientInfo": {"name": "MaxPlusAI", "version": "1.0.1"},
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
    count = max(1, min(count, 10))

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


_WEB_PERMISSION_HANDLER: Optional[Callable[[str, str, str], bool]] = None


def set_web_permission_handler(handler: Optional[Callable[[str, str, str], bool]]) -> None:
    """Register interactive permission handler for web access: handler(domain, url, action) -> bool."""
    global _WEB_PERMISSION_HANDLER
    _WEB_PERMISSION_HANDLER = handler


def check_web_permission(url: str, action: str = "อ่านเนื้อหาหน้าเว็บ") -> tuple[bool, str]:
    """Check if web access to URL is permitted by policy, whitelist, or user confirmation."""
    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(url if url.startswith(("http://", "https://")) else f"https://{url}")
        domain = (parsed.hostname or parsed.netloc or "").strip().lower()
    except Exception:
        domain = ""

    if not domain:
        return True, ""

    try:
        from core.settings_store import SettingsStore
    except ImportError:
        from src.core.settings_store import SettingsStore  # type: ignore[no-redef]

    store = SettingsStore()
    settings = store.load_web_security_settings()
    policy = settings.get("policy", "ask")
    allowed = {d.strip().lower() for d in settings.get("allowed_domains", [])}
    denied = {d.strip().lower() for d in settings.get("denied_domains", [])}

    # 1. Check if explicitly denied
    if domain in denied or any(domain.endswith(f".{d}") for d in denied):
        return False, f"⚠️ การเข้าถึงเว็บไซต์ '{domain}' ถูกปฏิเสธตามนโยบายความปลอดภัย (Denied by security policy)"

    # 2. Check if allow_all policy or in allowed whitelist
    if policy == "allow_all":
        return True, ""

    if domain in allowed or any(domain.endswith(f".{d}") for d in allowed):
        return True, ""

    # 3. If policy is deny_all
    if policy == "deny_all":
        return False, f"⚠️ การเข้าถึงเว็บไซต์ '{domain}' ถูกปฏิเสธ (Web access disabled by policy: deny_all)"

    # 4. If policy is 'ask', invoke permission handler if available
    if _WEB_PERMISSION_HANDLER is not None:
        try:
            is_granted = _WEB_PERMISSION_HANDLER(domain, url, action)
            if is_granted:
                return True, ""
            else:
                return False, f"⚠️ ผู้ใช้ไม่อนุญาตให้ AI เข้าถึงเว็บไซต์ '{domain}' ({url})"
        except Exception as ex:
            return False, f"Error checking permission for '{domain}': {ex}"

    # Default fallback if no interactive handler registered
    return True, ""


def _builtin_fetch_web(url: str, max_length: int = 8000) -> str:
    """Fetch content of a webpage, parse and extract clean readable text."""
    import urllib.request
    import urllib.parse
    import html
    import re

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Security check
    allowed, err_msg = check_web_permission(url, action="เปิดอ่านเนื้อหาหน้าเว็บ")
    if not allowed:
        return err_msg

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,text/plain,application/json;q=0.9,*/*;q=0.8",
    }
    max_length = max(500, min(max_length, 30000))

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
        start = max(1, start_line)
        count = max(1, min(line_count, 1000))
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

    timeout = max(1, min(timeout_seconds, 120))
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

    timeout = max(1, min(timeout_seconds, 60))

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


def _builtin_edit_snippet(path: str, target: str, replacement: str) -> str:
    """Surgically replace a specific code snippet in a file without rewriting the whole file."""
    p = Path(path).resolve()
    if not p.exists():
        return f"Error: File '{path}' does not exist"
    if not p.is_file():
        return f"Error: '{path}' is not a file"

    try:
        content = p.read_text(encoding="utf-8")
        if target not in content:
            return f"Error: Target snippet not found in '{p.name}'"
        count = content.count(target)
        new_content = content.replace(target, replacement, 1)
        p.write_text(new_content, encoding="utf-8")
        return f"สำเร็จ: แก้ไขโค้ดใน '{p.name}' เรียบร้อย (พบ {count} จุด, แทนที่ 1 จุด)"
    except Exception as ex:
        return f"Error editing file snippet: {ex}"


def _builtin_get_file_info(path: str) -> str:
    """Get metadata and statistics about a file or directory."""
    p = Path(path).resolve()
    if not p.exists():
        return f"Error: Path '{path}' does not exist"

    import datetime
    stat = p.stat()
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    ctime_val = getattr(stat, "st_birthtime", stat.st_mtime)
    ctime = datetime.datetime.fromtimestamp(ctime_val).strftime("%Y-%m-%d %H:%M:%S")
    is_dir = p.is_dir()
    size = stat.st_size
    size_str = f"{size} B" if size < 1024 else f"{size/1024:.2f} KB ({size/1024/1024:.2f} MB)"

    info = [
        f"Path: {p}",
        f"Type: {'Directory' if is_dir else 'File'}",
        f"Size: {size_str}",
        f"Modified: {mtime}",
        f"Created: {ctime}",
    ]
    if not is_dir:
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            info.append(f"Lines: {len(lines)}")
        except Exception:
            pass
    return "\n".join(info)


def _builtin_delete_file(path: str) -> str:
    """Delete a file from the filesystem."""
    p = Path(path).resolve()
    if not p.exists():
        return f"Error: Path '{path}' does not exist"
    if p.is_dir():
        return f"Error: '{path}' is a directory, not a file (for safety, directories cannot be deleted with this tool)"

    try:
        p.unlink()
        return f"สำเร็จ: ลบไฟล์ '{p}' เรียบร้อย"
    except Exception as ex:
        return f"Error deleting file '{path}': {ex}"


def _builtin_http_request(url: str, method: str = "GET", headers: Optional[dict[str, str]] = None,
                          body: Optional[str] = None) -> str:
    """Send an HTTP request (GET, POST, PUT, DELETE, PATCH) and return response status and body."""
    import urllib.request
    import urllib.error

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    method = method.strip().upper()

    # Security check
    allowed, err_msg = check_web_permission(url, action=f"ส่ง HTTP Request ({method})")
    if not allowed:
        return err_msg
    req_headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "*/*",
    }
    if headers and isinstance(headers, dict):
        req_headers.update(headers)

    data_bytes = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.status
            content = resp.read().decode("utf-8", errors="replace")
            # Truncate if response is excessively large
            if len(content) > 10000:
                content = content[:10000] + "\n... [Response truncated at 10,000 characters]"
            return f"HTTP {code} OK\n\n{content}"
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8", errors="replace")
        return f"HTTP Error {e.code}: {e.reason}\n\n{err_content}"
    except Exception as ex:
        return f"HTTP Request Error: {ex}"


def _builtin_git_status(path: str = ".") -> str:
    """Get current Git status, branch, and uncommitted changes."""
    return _builtin_run_command("git status --short --branch", cwd=path, timeout_seconds=10)


def _builtin_git_diff(path: str = ".", cached: bool = False) -> str:
    """Get Git diff for unstaged or cached changes."""
    cmd = "git diff --cached" if cached else "git diff"
    return _builtin_run_command(cmd, cwd=path, timeout_seconds=10)


def _builtin_git_log(path: str = ".", count: int = 5) -> str:
    """Get recent Git commits in oneline format."""
    n = max(1, min(count, 30))
    return _builtin_run_command(f"git log -n {n} --oneline", cwd=path, timeout_seconds=10)


def _builtin_list_processes(filter_name: str = "") -> str:
    """List running processes filtered by name."""
    filter_name = (filter_name or "").strip().lower()
    if os.name == "nt":
        cmd = f'tasklist /FI "IMAGENAME eq {filter_name}*"' if filter_name else "tasklist"
    else:
        cmd = f"ps aux | grep -i {filter_name}" if filter_name else "ps aux"
    res = _builtin_run_command(cmd, timeout_seconds=10)
    lines = res.splitlines()
    if len(lines) > 60:
        return "\n".join(lines[:60]) + f"\n... [แสดงผล 60 จาก {len(lines)} กระบวนการ]"
    return res


def _builtin_get_env(name: str) -> str:
    """Get environment variable value safely."""
    val = os.environ.get(name.strip())
    if val is None:
        return f"Environment variable '{name}' is not set"
    return val


def _builtin_json_format(text: str, indent: int = 2) -> str:
    """Parse, validate, and pretty-print JSON string."""
    try:
        data = json.loads(text.strip())
        return json.dumps(data, indent=max(0, min(indent, 8)), ensure_ascii=False)
    except Exception as ex:
        return f"Invalid JSON error: {ex}"


def _builtin_hash_data(text: str, algorithm: str = "sha256") -> str:
    """Calculate cryptographic hash (sha256, md5, sha1) for a string."""
    import hashlib
    algo = algorithm.strip().lower()
    raw = text.encode("utf-8")
    if algo == "md5":
        return hashlib.md5(raw).hexdigest()
    elif algo == "sha1":
        return hashlib.sha1(raw).hexdigest()
    elif algo == "sha512":
        return hashlib.sha512(raw).hexdigest()
    return hashlib.sha256(raw).hexdigest()


def _builtin_base64_codec(text: str, action: str = "encode") -> str:
    """Encode or decode Base64 string."""
    import base64
    act = action.strip().lower()
    try:
        if act == "decode":
            return base64.b64decode(text.strip().encode("ascii")).decode("utf-8", errors="replace")
        return base64.b64encode(text.encode("utf-8")).decode("ascii")
    except Exception as ex:
        return f"Base64 error: {ex}"


def _builtin_export_to_download(source_path: str = ".", output_name: str = "") -> str:
    """Compress and export project or files to user's standard Download directory (e.g. Android Termux /sdcard/Download or PC Downloads)."""
    import shutil
    import zipfile

    src = Path(source_path or ".").resolve()
    if not src.exists():
        return f"Error: ไม่พบโฟลเดอร์หรือไฟล์ '{source_path}'"

    # Search for accessible Download directory
    download_dirs: list[Path] = []
    # 1. Android Termux shared storage & sdcard paths
    download_dirs.append(Path.home() / "storage" / "shared" / "Download")
    download_dirs.append(Path("/sdcard/Download"))
    download_dirs.append(Path("/storage/emulated/0/Download"))
    download_dirs.append(Path("/storage/emulated/0/Download/MAX_Projects"))
    # 2. Windows Downloads
    if os.name == "nt":
        download_dirs.append(Path.home() / "Downloads")
        if "USERPROFILE" in os.environ:
            download_dirs.append(Path(os.environ["USERPROFILE"]) / "Downloads")
    # 3. Linux / macOS standard Downloads
    download_dirs.append(Path.home() / "Downloads")
    download_dirs.append(Path.home())

    dest_dir: Optional[Path] = None
    for d in download_dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            test_f = d / ".max_write_test"
            test_f.write_text("ok", encoding="utf-8")
            test_f.unlink()
            dest_dir = d
            break
        except Exception:
            continue

    if not dest_dir:
        dest_dir = Path.home()

    name = output_name.strip()
    if not name:
        base_name = src.name if src.name and src.name not in {".", "/"} else "max_project"
        name = f"{base_name}.zip"
    elif not name.endswith(".zip"):
        name += ".zip"

    zip_path = dest_dir / name

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if src.is_file():
                zf.write(src, arcname=src.name)
            else:
                for root, dirs, files in os.walk(src):
                    dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "venv", ".venv", "build", "dist", "node_modules", ".gradle"}]
                    for file in files:
                        full_p = Path(root) / file
                        rel_p = full_p.relative_to(src)
                        zf.write(full_p, arcname=str(rel_p))

        termux_hint = ""
        if shutil.which("termux-open"):
            termux_hint = f"\n💡 สามารถสั่ง 'termux-open \"{zip_path}\"' เพื่อเปิดหรือส่งต่อไฟล์ได้ทันที"

        return (
            f"📦 ส่งออกโปรเจกต์สำเร็จเรียบร้อยแล้ว!\n"
            f"• ไฟล์ ZIP: {zip_path}\n"
            f"• โฟลเดอร์ปลายทาง: {dest_dir}\n"
            f"• คุณสามารถเปิดดูไฟล์นี้ได้ในแอพ 'จัดการไฟล์ (Files / My Files / Downloads)' บนมือถือได้ทันที{termux_hint}"
        )
    except Exception as ex:
        return f"Error exporting project: {ex}"


def _builtin_generate_image(
    prompt: str,
    output_path: str = "",
    width: int = 1024,
    height: int = 1024,
    model: str = "flux",
    seed: Optional[int] = None,
    negative_prompt: str = "",
) -> str:
    """Generate high-quality AI images using Pollinations / Flux / AI Engine and save to disk."""
    import urllib.request
    import urllib.parse
    import time
    import random
    import shutil

    prompt = prompt.strip()
    if not prompt:
        return "Error: Prompt cannot be empty"

    width = max(256, min(width, 2048))
    height = max(256, min(height, 2048))
    seed_val = seed if seed is not None else random.randint(1, 99999999)

    # Determine destination file path
    if output_path.strip():
        dest = Path(output_path.strip()).resolve()
    else:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dest = (Path.cwd() / f"image_{timestamp}.png").resolve()

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Build image generation URL
    encoded_prompt = urllib.parse.quote(prompt)
    params = {
        "width": str(width),
        "height": str(height),
        "seed": str(seed_val),
        "model": model.strip().lower() if model else "flux",
        "nologo": "true",
        "enhance": "true",
    }
    if negative_prompt.strip():
        params["negative"] = negative_prompt.strip()

    query_str = urllib.parse.urlencode(params)
    api_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?{query_str}"

    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "image/png,image/jpeg,image/*",
    }

    try:
        req = urllib.request.Request(api_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()

        if len(data) < 500:
            return f"Error: Failed to generate image (Response too small: {len(data)} bytes)"

        dest.write_bytes(data)
        file_size_kb = len(data) / 1024

        termux_hint = ""
        if shutil.which("termux-open"):
            termux_hint = f"\n💡 ดูภาพบนมือถือ: termux-open \"{dest}\""

        return (
            f"🎨 สร้างรูปภาพสำเร็จเรียบร้อยแล้ว!\n"
            f"• ไฟล์ภาพ: {dest}\n"
            f"• ขนาดภาพ: {width}x{height} px ({file_size_kb:.1f} KB)\n"
            f"• โมเดล: {model} (Seed: {seed_val})\n"
            f"• Prompt: {prompt}{termux_hint}"
        )
    except Exception as ex:
        return f"Error generating image: {ex}"


def _builtin_generate_video(
    prompt: str,
    output_path: str = "",
    duration_seconds: int = 4,
    aspect_ratio: str = "16:9",
    model: str = "wan2.1",
) -> str:
    """Generate AI video / animation and save to MP4/GIF format."""
    import urllib.request
    import urllib.parse
    import time
    import shutil

    prompt = prompt.strip()
    if not prompt:
        return "Error: Prompt cannot be empty"

    duration = max(2, min(duration_seconds, 15))
    ar = aspect_ratio.strip() if aspect_ratio.strip() else "16:9"

    if output_path.strip():
        dest = Path(output_path.strip()).resolve()
    else:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dest = (Path.cwd() / f"video_{timestamp}.mp4").resolve()

    dest.parent.mkdir(parents=True, exist_ok=True)

    encoded_prompt = urllib.parse.quote(prompt)
    api_url = f"https://video.pollinations.ai/prompt/{encoded_prompt}?duration={duration}&aspect_ratio={ar}&model={urllib.parse.quote(model)}"

    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "video/mp4,video/*,*/*",
    }

    try:
        req = urllib.request.Request(api_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()

        if len(data) > 1000:
            dest.write_bytes(data)
            size_mb = len(data) / (1024 * 1024)
            termux_hint = ""
            if shutil.which("termux-open"):
                termux_hint = f"\n💡 เปิดวิดีโอบนมือถือ: termux-open \"{dest}\""

            return (
                f"🎬 สร้างวิดีโอสำเร็จเรียบร้อยแล้ว!\n"
                f"• ไฟล์วิดีโอ: {dest}\n"
                f"• ขนาดไฟล์: {size_mb:.2f} MB (ความยาว ~{duration} วินาที, สัดส่วน {ar})\n"
                f"• โมเดล: {model}\n"
                f"• Prompt: {prompt}{termux_hint}"
            )
        else:
            return f"Error: ได้รับข้อมูลวิดีโอไม่สมบูรณ์ ({len(data)} bytes)"
    except Exception as ex:
        return (
            f"⚠️ ไม่สามารถดึงวิดีโอจาก Cloud Generator ได้โดยตรง ({ex})\n"
            f"💡 ข้อแนะนำ: คุณสามารถสั่งให้สร้างภาพผ่าน `generate_image` แล้วนำมาสร้างเป็น GIF/Flipbook/Animation ด้วย Python ได้"
        )


def _normalize_github_repo_name(repo: str) -> str:
    """Extract 'owner/repo' from URL or shorthand."""
    r = repo.strip()
    if r.startswith("http://") or r.startswith("https://"):
        r = r.split("github.com/")[-1]
    return r.rstrip("/").removesuffix(".git")


def _builtin_github_search_repos(query: str, count: int = 5, sort: str = "stars") -> str:
    """Search public GitHub repositories by keyword, stars, or topic."""
    import urllib.request
    import urllib.parse

    q = query.strip()
    if not q:
        return "Error: Search query cannot be empty"

    n = max(1, min(count, 15))
    sort_by = sort.strip() if sort.strip() in {"stars", "forks", "updated"} else "stars"
    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort={sort_by}&per_page={n}"

    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        items = data.get("items", [])
        if not items:
            return f"ไม่พบ GitHub Repository สำหรับคำค้นหา '{q}'"

        total_count = data.get("total_count", len(items))
        res = [f"🔍 พบ {total_count:,} Repositories สำหรับ '{q}' (แสดง {len(items)} อันดับแรก):\n"]
        for idx, item in enumerate(items, 1):
            full_name = item.get("full_name", "")
            desc = (item.get("description") or "ไม่มีคำอธิบาย").strip()
            stars = item.get("stargazers_count", 0)
            forks = item.get("forks_count", 0)
            lang = item.get("language") or "N/A"
            html_url = item.get("html_url", "")
            res.append(
                f"{idx}. ⭐ {full_name} ({lang} | ★ {stars:,} | ⑂ {forks:,})\n"
                f"   📝 {desc}\n"
                f"   🔗 {html_url}"
            )
        return "\n\n".join(res)
    except Exception as ex:
        return f"Error searching GitHub repositories: {ex}"


def _builtin_github_get_repo(repo: str) -> str:
    """Get metadata, stats, description, license, and latest release for a GitHub repository."""
    import urllib.request
    import urllib.error

    repo_name = _normalize_github_repo_name(repo)
    if not repo_name or "/" not in repo_name:
        return f"Error: รูปแบบชื่อ Repository ไม่ถูกต้อง (ต้องเป็น 'owner/repo' หรือ URL เต็ม)"

    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        # 1. Repo info
        url = f"https://api.github.com/repos/{repo_name}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        full_name = data.get("full_name", repo_name)
        desc = data.get("description") or "ไม่มีคำอธิบาย"
        stars = data.get("stargazers_count", 0)
        forks = data.get("forks_count", 0)
        watchers = data.get("subscribers_count", data.get("watchers_count", 0))
        open_issues = data.get("open_issues_count", 0)
        lang = data.get("language") or "N/A"
        license_info = data.get("license") or {}
        license_name = license_info.get("name") if isinstance(license_info, dict) else "N/A"
        default_branch = data.get("default_branch", "main")
        homepage = data.get("homepage") or ""
        created_at = data.get("created_at", "")[:10]
        updated_at = data.get("updated_at", "")[:10]
        html_url = data.get("html_url", f"https://github.com/{repo_name}")

        # 2. Check latest release
        latest_release_str = "ไม่มี Release อย่างเป็นทางการ"
        try:
            rel_url = f"https://api.github.com/repos/{repo_name}/releases/latest"
            rel_req = urllib.request.Request(rel_url, headers=headers, method="GET")
            with urllib.request.urlopen(rel_req, timeout=8) as rel_resp:
                rel_data = json.loads(rel_resp.read().decode("utf-8", errors="replace"))
                tag = rel_data.get("tag_name", "")
                rel_name = rel_data.get("name", tag)
                rel_date = rel_data.get("published_at", "")[:10]
                latest_release_str = f"{rel_name} (Tag: {tag}, Published: {rel_date})"
        except Exception:
            pass

        info = [
            f"📦 Repository: {full_name}",
            f"• URL: {html_url}",
            f"• Description: {desc}",
            f"• Primary Language: {lang}",
            f"• Stars: ★ {stars:,} | Forks: ⑂ {forks:,} | Watchers: 👁 {watchers:,}",
            f"• Open Issues / PRs: {open_issues:,}",
            f"• Default Branch: {default_branch}",
            f"• License: {license_name}",
            f"• Latest Release: {latest_release_str}",
            f"• Created: {created_at} | Last Updated: {updated_at}",
        ]
        if homepage:
            info.append(f"• Homepage: {homepage}")

        return "\n".join(info)
    except urllib.error.HTTPError as e:
        return f"GitHub API Error ({e.code}): ไม่พบ Repository '{repo_name}' หรือถูกจำกัดการเข้าถึง ({e.reason})"
    except Exception as ex:
        return f"Error querying GitHub repo '{repo_name}': {ex}"


def _builtin_github_read_file(repo: str, file_path: str, branch: str = "") -> str:
    """Read source code or file directly from a GitHub repository without cloning."""
    import urllib.request
    import urllib.error

    repo_name = _normalize_github_repo_name(repo)
    clean_path = file_path.strip().lstrip("/")
    if not repo_name or not clean_path:
        return "Error: กรุณาระบุชื่อ repo (เช่น 'owner/repo') และ path ของไฟล์ (เช่น 'README.md' หรือ 'src/main.py')"

    branches_to_try = [branch.strip()] if branch.strip() else ["HEAD", "main", "master"]
    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "text/plain,application/vnd.github.v3.raw",
    }

    for b in branches_to_try:
        raw_url = f"https://raw.githubusercontent.com/{repo_name}/{b}/{clean_path}"
        try:
            req = urllib.request.Request(raw_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                lines = content.splitlines()
                return (
                    f"📄 File: {repo_name}/{clean_path} (Branch: {b}, {len(lines)} บรรทัด, {len(content)} ตัวอักษร)\n"
                    f"{'─'*60}\n"
                    f"{content}"
                )
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            return f"HTTP Error {e.code} reading '{clean_path}' from '{repo_name}': {e.reason}"
        except Exception as ex:
            return f"Error reading '{clean_path}' from '{repo_name}': {ex}"

    return f"Error: ไม่พบไฟล์ '{clean_path}' ใน repository '{repo_name}' (ค้นหาใน branches: {', '.join(branches_to_try)})"


def _builtin_github_list_issues(repo: str, state: str = "open", count: int = 5) -> str:
    """List issues and pull requests for a repository."""
    import urllib.request
    import urllib.error

    repo_name = _normalize_github_repo_name(repo)
    if not repo_name or "/" not in repo_name:
        return "Error: กรุณาระบุชื่อ repo ในรูปแบบ 'owner/repo'"

    n = max(1, min(count, 20))
    st = state.strip().lower() if state.strip().lower() in {"open", "closed", "all"} else "open"
    url = f"https://api.github.com/repos/{repo_name}/issues?state={st}&per_page={n}"

    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        if not data:
            return f"ไม่พบรายการ Issues / PRs สถานะ '{st}' ใน '{repo_name}'"

        res = [f"📋 รายการ Issues/PRs ({st}) ใน {repo_name} (แสดง {len(data)} รายการล่าสุด):\n"]
        for idx, item in enumerate(data, 1):
            num = item.get("number", "?")
            title = item.get("title", "")
            user = item.get("user", {}).get("login", "unknown")
            is_pr = "pull_request" in item
            kind = "🔀 PR" if is_pr else "📌 Issue"
            comments = item.get("comments", 0)
            created = item.get("created_at", "")[:10]
            item_url = item.get("html_url", "")
            labels = [lbl.get("name", "") for lbl in item.get("labels", []) if isinstance(lbl, dict)]
            lbl_str = f" [{', '.join(labels)}]" if labels else ""
            res.append(f"{idx}. {kind} #{num}: {title}{lbl_str}\n   โดย: @{user} ({created}) | ความเห็น: {comments}\n   🔗 {item_url}")

        return "\n\n".join(res)
    except Exception as ex:
        return f"Error listing issues for '{repo_name}': {ex}"


def _builtin_github_clone_repo(repo_url: str, target_dir: str = "") -> str:
    """Clone a GitHub repository safely into local workspace."""
    r = repo_url.strip()
    if not r:
        return "Error: Repository URL or name cannot be empty"

    if not r.startswith("http://") and not r.startswith("https://") and not r.startswith("git@"):
        r = f"https://github.com/{r.rstrip('.git')}.git"

    cmd = f"git clone {r}"
    if target_dir.strip():
        cmd += f" \"{target_dir.strip()}\""

    res = _builtin_run_command(cmd, timeout_seconds=120)
    return f"📥 สั่งโคลน Repository: {r}\n\n{res}"


def _builtin_install_skill(source: str, skill_id: str = "", content: str = "") -> str:
    """Install a skill from GitHub repository, URL, or raw markdown content."""
    try:
        from core.skill_manager import SkillManager
    except ImportError:
        try:
            from src.core.skill_manager import SkillManager
        except ImportError:
            return "Error: Cannot import SkillManager"

    mgr = SkillManager()
    src = source.strip()

    # If source is raw content or empty and content is provided
    if not src and content.strip():
        sid = skill_id.strip() or "custom-skill"
        _ok, msg = mgr.install_skill(sid, content, overwrite=True)
        return msg

    if src.startswith("http://") or src.startswith("https://") or ("/" in src and not src.startswith("#") and "\n" not in src):
        _ok, msg = mgr.install_from_github(src, skill_id=skill_id)
        return msg

    # If user passed raw text in source
    if "\n" in src or src.startswith("---") or not skill_id:
        sid = skill_id.strip() or "custom-skill"
        _ok, msg = mgr.install_skill(sid, src if not content else content, overwrite=True)
        return msg

    _ok, msg = mgr.install_from_github(src, skill_id=skill_id)
    return msg


def _builtin_remove_skill(skill_id: str) -> str:
    """Delete an installed skill by ID."""
    try:
        from core.skill_manager import SkillManager
    except ImportError:
        try:
            from src.core.skill_manager import SkillManager
        except ImportError:
            return "Error: Cannot import SkillManager"

    mgr = SkillManager()
    _ok, msg = mgr.delete_skill(skill_id)
    return msg


def _builtin_list_skills() -> str:
    """List all installed skills with status, description and paths."""
    try:
        from core.skill_manager import SkillManager
    except ImportError:
        try:
            from src.core.skill_manager import SkillManager
        except ImportError:
            return "Error: Cannot import SkillManager"

    mgr = SkillManager()
    skills = mgr.list_skills_info()
    if not skills:
        return "ℹ️ ยังไม่มี Skill ใดติดตั้งในระบบ (โฟลเดอร์ skills/ ว่างเปล่า)"

    lines = [f"📦 ทักษะ (Skills) ที่ติดตั้งในระบบทั้งหมด ({len(skills)} รายการ):\n"]
    for idx, s in enumerate(skills, 1):
        def_tag = " [Default: เปิดใช้งานเสมอ]" if s.get("default") else ""
        desc = s.get("description") or "ไม่มีคำอธิบาย"
        lines.append(f"{idx}. 🧩 **{s['name']}** (`{s['id']}`){def_tag}\n   คำอธิบาย: {desc}\n   พาธ: {s['path']}")

    return "\n\n".join(lines)


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

        # 12. Edit File Snippet
        self.builtin_tools["edit_file_snippet"] = (
            MCPTool(
                name="edit_file_snippet",
                description="แก้ไขโค้ดเฉพาะจุดในไฟล์โดยการค้นหาท่อนโค้ดเป้าหมาย (target) และแทนที่ด้วยโค้ดใหม่ (replacement) อย่างแม่นยำ โดยไม่ต้องเขียนทับไฟล์ใหม่ทั้งไฟล์",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์ที่ต้องการแก้ไข"},
                        "target": {"type": "string", "description": "โค้ดเดิมที่ต้องการค้นหาและแทนที่ (ต้องตรงทุกตัวอักษร)"},
                        "replacement": {"type": "string", "description": "โค้ดใหม่ที่จะนำไปแทนที่"},
                    },
                    "required": ["path", "target", "replacement"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_edit_snippet(
                str(args.get("path", "")),
                str(args.get("target", "")),
                str(args.get("replacement", "")),
            ),
        )

        # 13. Get File Info
        self.builtin_tools["get_file_info"] = (
            MCPTool(
                name="get_file_info",
                description="ตรวจสอบข้อมูลคุณสมบัติของไฟล์ (ขนาด, จำนวนบรรทัด, วันที่สร้าง/แก้ไขล่าสุด, สิทธิ์)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์หรือโฟลเดอร์ที่ต้องการตรวจสอบ"},
                    },
                    "required": ["path"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_get_file_info(str(args.get("path", ""))),
        )

        # 14. Delete File
        self.builtin_tools["delete_file"] = (
            MCPTool(
                name="delete_file",
                description="ลบไฟล์เดี่ยวที่ไม่ต้องการออกจากระบบอย่างปลอดภัย (ไม่สามารถลบโฟลเดอร์ได้)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์ที่ต้องการลบ"},
                    },
                    "required": ["path"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_delete_file(str(args.get("path", ""))),
        )

        # 15. HTTP Request
        self.builtin_tools["http_request"] = (
            MCPTool(
                name="http_request",
                description="ส่ง HTTP Request (GET, POST, PUT, DELETE, PATCH) ไปยัง Webhook, REST API หรือ URL ภายนอก",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL ปลายทาง"},
                        "method": {"type": "string", "description": "HTTP Method (GET, POST, PUT, DELETE, PATCH)", "default": "GET"},
                        "headers": {"type": "object", "description": "HTTP Headers ในรูปแบบ key-value", "default": {}},
                        "body": {"type": "string", "description": "Request body (string หรือ JSON string)"},
                    },
                    "required": ["url"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_http_request(
                str(args.get("url", "")),
                method=str(args.get("method", "GET")),
                headers=args.get("headers"),
                body=str(args.get("body", "")) if args.get("body") is not None else None,
            ),
        )

        # 16. Git Status
        self.builtin_tools["git_status"] = (
            MCPTool(
                name="git_status",
                description="ตรวจสอบสถานะ Git ของโปรเจกต์ (branch ปัจจุบัน, ไฟล์ที่แก้ไข, ไฟล์ใหม่)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "ไดเรกทอรีของ Git repository (ค่าเริ่มต้น .)", "default": "."},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_git_status(str(args.get("path", "."))),
        )

        # 17. Git Diff
        self.builtin_tools["git_diff"] = (
            MCPTool(
                name="git_diff",
                description="ตรวจสอบความเปลี่ยนแปลงของโค้ดใน Git (Git Diff) เทียบกับ commit ล่าสุด",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "ไดเรกทอรีของ Git repository (ค่าเริ่มต้น .)", "default": "."},
                        "cached": {"type": "boolean", "description": "ดู diff ของ staged changes หรือไม่", "default": False},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_git_diff(str(args.get("path", ".")), cached=bool(args.get("cached", False))),
        )

        # 18. Git Log
        self.builtin_tools["git_log"] = (
            MCPTool(
                name="git_log",
                description="ดูประวัติการ Commit ล่าสุดใน Git",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "ไดเรกทอรีของ Git repository (ค่าเริ่มต้น .)", "default": "."},
                        "count": {"type": "integer", "description": "จำนวน commit ที่ต้องการดู (ค่าเริ่มต้น 5)", "default": 5},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_git_log(str(args.get("path", ".")), count=int(args.get("count", 5))),
        )

        # 19. List Processes
        self.builtin_tools["list_processes"] = (
            MCPTool(
                name="list_processes",
                description="ตรวจสอบรายการ Process / โปรแกรมที่กำลังทำงานอยู่บนเครื่อง พร้อมตัวกรองชื่อ",
                input_schema={
                    "type": "object",
                    "properties": {
                        "filter_name": {"type": "string", "description": "กรองตามชื่อโปรแกรม เช่น python, node, blender, git (ค่าเริ่มต้นแสดงทั้งหมด)"},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_list_processes(str(args.get("filter_name", ""))),
        )

        # 20. Get Environment Variable
        self.builtin_tools["get_environment_variable"] = (
            MCPTool(
                name="get_environment_variable",
                description="อ่านค่า Environment Variable ของระบบตามชื่อที่ระบุ",
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "ชื่อ Environment Variable เช่น PATH, USERNAME, APPDATA"},
                    },
                    "required": ["name"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_get_env(str(args.get("name", ""))),
        )

        # 21. JSON Format
        self.builtin_tools["json_format"] = (
            MCPTool(
                name="json_format",
                description="ตรวจสอบความถูกต้อง และจัดรูปแบบ Pretty-Print ให้กับข้อความ JSON",
                input_schema={
                    "type": "object",
                    "properties": {
                        "json_text": {"type": "string", "description": "ข้อความ JSON ที่ต้องการจัดรูปแบบ"},
                        "indent": {"type": "integer", "description": "จำนวน space ย่อหน้า (ค่าเริ่มต้น 2)", "default": 2},
                    },
                    "required": ["json_text"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_json_format(str(args.get("json_text", "")), indent=int(args.get("indent", 2))),
        )

        # 22. Hash Data
        self.builtin_tools["hash_data"] = (
            MCPTool(
                name="hash_data",
                description="คำนวณค่า Cryptographic Hash (SHA256, MD5, SHA1) สำหรับข้อความ",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "ข้อความที่ต้องการคำนวณ Hash"},
                        "algorithm": {"type": "string", "description": "อัลกอริทึม (sha256, md5, sha1, sha512)", "default": "sha256"},
                    },
                    "required": ["text"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_hash_data(str(args.get("text", "")), algorithm=str(args.get("algorithm", "sha256"))),
        )

        # 23. Base64 Codec
        self.builtin_tools["base64_codec"] = (
            MCPTool(
                name="base64_codec",
                description="แปลงข้อมูลเป็น Base64 (encode) หรือถอดรหัสจาก Base64 (decode)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "ข้อความที่ต้องการ encode หรือ decode"},
                        "action": {"type": "string", "description": "action: encode หรือ decode (ค่าเริ่มต้น encode)", "default": "encode"},
                    },
                    "required": ["text"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_base64_codec(str(args.get("text", "")), action=str(args.get("action", "encode"))),
        )

        # 24. Export to Download
        self.builtin_tools["export_to_download"] = (
            MCPTool(
                name="export_to_download",
                description="บีบอัดและส่งออกโฟลเดอร์/โปรเจกต์ไปยังโฟลเดอร์ Download ของมือถือ (Android Termux) หรือเครื่อง เพื่อให้เปิดดูและแชร์ไฟล์ได้ทันที",
                input_schema={
                    "type": "object",
                    "properties": {
                        "source_path": {"type": "string", "description": "โฟลเดอร์หรือไฟล์ที่ต้องการส่งออก (ค่าเริ่มต้น . โฟลเดอร์ปัจจุบัน)", "default": "."},
                        "output_name": {"type": "string", "description": "ชื่อไฟล์ ZIP ปลายทาง เช่น my-app.zip", "default": ""},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_export_to_download(
                source_path=str(args.get("source_path", ".")),
                output_name=str(args.get("output_name", "")),
            ),
        )

        # 25. Generate AI Image
        self.builtin_tools["generate_image"] = (
            MCPTool(
                name="generate_image",
                description="สร้างรูปภาพด้วย AI ตามคำบรรยาย (Prompt) ความละเอียดสูง บันทึกเป็นไฟล์ภาพ PNG/JPG ลงเครื่อง",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "คำอธิบายภาพที่ต้องการสร้าง เช่น a cybernetic glowing cat in cyberpunk city, 8k"},
                        "output_path": {"type": "string", "description": "พาธไฟล์ภาพปลายทาง เช่น images/cat.png (หากไม่ระบุจะตั้งชื่ออัตโนมัติตามเวลา)", "default": ""},
                        "width": {"type": "integer", "description": "ความกว้างของภาพ (pixels, เช่น 1024, 768, 512)", "default": 1024},
                        "height": {"type": "integer", "description": "ความสูงของภาพ (pixels, เช่น 1024, 768, 512)", "default": 1024},
                        "model": {"type": "string", "description": "โมเดลที่ต้องการสร้าง (flux, turbo, dall-e-3)", "default": "flux"},
                        "negative_prompt": {"type": "string", "description": "สิ่งที่ไม่ต้องการให้ปรากฏในภาพ", "default": ""},
                    },
                    "required": ["prompt"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_generate_image(
                prompt=str(args.get("prompt", "")),
                output_path=str(args.get("output_path", "")),
                width=int(args.get("width", 1024)),
                height=int(args.get("height", 1024)),
                model=str(args.get("model", "flux")),
                negative_prompt=str(args.get("negative_prompt", "")),
            ),
        )

        # 26. Generate AI Video
        self.builtin_tools["generate_video"] = (
            MCPTool(
                name="generate_video",
                description="สร้างวิดีโอหรือคลิปอนิเมชันสั้นด้วย AI ตาม Prompt บันทึกเป็นไฟล์ MP4 ลงเครื่อง",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "คำอธิบายคลิปวิดีโอหรืออนิเมชันที่ต้องการสร้าง เช่น cinematic drone shot flying over futuristic neon city"},
                        "output_path": {"type": "string", "description": "พาธไฟล์วิดีโอปลายทาง เช่น videos/city.mp4 (หากไม่ระบุจะตั้งชื่ออัตโนมัติตามเวลา)", "default": ""},
                        "duration_seconds": {"type": "integer", "description": "ความยาวคลิปเป็นวินาที (ค่าเริ่มต้น 4, สูงสุด 15)", "default": 4},
                        "aspect_ratio": {"type": "string", "description": "สัดส่วนภาพ เช่น 16:9, 9:16, 1:1", "default": "16:9"},
                        "model": {"type": "string", "description": "โมเดลสร้างวิดีโอ (wan2.1, cogvideo, luma)", "default": "wan2.1"},
                    },
                    "required": ["prompt"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_generate_video(
                prompt=str(args.get("prompt", "")),
                output_path=str(args.get("output_path", "")),
                duration_seconds=int(args.get("duration_seconds", 4)),
                aspect_ratio=str(args.get("aspect_ratio", "16:9")),
                model=str(args.get("model", "wan2.1")),
            ),
        )

        # 27. GitHub Search Repositories
        self.builtin_tools["github_search_repos"] = (
            MCPTool(
                name="github_search_repos",
                description="ค้นหาและสำรวจ Repositories บน GitHub ตามคำค้นหา ภาษา หรือจำนวนดาว (Stars)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "คำค้นหา เช่น fastmcp, android termux, machine learning"},
                        "count": {"type": "integer", "description": "จำนวนผลลัพธ์ที่ต้องการ (ค่าเริ่มต้น 5, สูงสุด 15)", "default": 5},
                        "sort": {"type": "string", "description": "การเรียงลำดับ: stars, forks, updated (ค่าเริ่มต้น stars)", "default": "stars"},
                    },
                    "required": ["query"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_search_repos(
                query=str(args.get("query", "")),
                count=int(args.get("count", 5)),
                sort=str(args.get("sort", "stars")),
            ),
        )

        # 28. GitHub Get Repository Details
        self.builtin_tools["github_get_repo"] = (
            MCPTool(
                name="github_get_repo",
                description="ดึงข้อมูลสรุปของ GitHub Repository (จำนวนดาว, ภาษาหลัก, License, สถิติ, และ Release ล่าสุด)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "ชื่อ repository ในรูปแบบ 'owner/repo' หรือ URL เต็ม เช่น 'Karanztez/MAX'"},
                    },
                    "required": ["repo"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_get_repo(str(args.get("repo", ""))),
        )

        # 29. GitHub Read File
        self.builtin_tools["github_read_file"] = (
            MCPTool(
                name="github_read_file",
                description="อ่านเนื้อหาไฟล์โค้ดหรือข้อความจาก GitHub Repository โดยตรง โดยไม่ต้องดาวน์โหลดหรือโคลนทั้งโปรเจกต์",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "ชื่อ repository เช่น 'Karanztez/MAX'"},
                        "file_path": {"type": "string", "description": "พาธของไฟล์ใน repo เช่น 'README.md' หรือ 'src/cli.py'"},
                        "branch": {"type": "string", "description": "ชื่อ branch (ค่าเริ่มต้นดึงจาก default branch / HEAD)", "default": ""},
                    },
                    "required": ["repo", "file_path"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_read_file(
                repo=str(args.get("repo", "")),
                file_path=str(args.get("file_path", "")),
                branch=str(args.get("branch", "")),
            ),
        )

        # 30. GitHub List Issues & PRs
        self.builtin_tools["github_list_issues"] = (
            MCPTool(
                name="github_list_issues",
                description="ดึงรายการ Issues และ Pull Requests ล่าสุดของ GitHub Repository",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "ชื่อ repository ในรูปแบบ 'owner/repo'"},
                        "state": {"type": "string", "description": "สถานะ: open, closed, all (ค่าเริ่มต้น open)", "default": "open"},
                        "count": {"type": "integer", "description": "จำนวนรายการที่ต้องการดึง (ค่าเริ่มต้น 5)", "default": 5},
                    },
                    "required": ["repo"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_list_issues(
                repo=str(args.get("repo", "")),
                state=str(args.get("state", "open")),
                count=int(args.get("count", 5)),
            ),
        )

        # 31. GitHub Clone Repo
        self.builtin_tools["github_clone_repo"] = (
            MCPTool(
                name="github_clone_repo",
                description="โคลน GitHub Repository ลงมายังเครื่องในโฟลเดอร์ที่กำหนด",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo_url": {"type": "string", "description": "URL ของ GitHub repo หรือ 'owner/repo' เช่น 'https://github.com/Karanztez/MAX'"},
                        "target_dir": {"type": "string", "description": "โฟลเดอร์ปลายทางที่ต้องการโคลนไปเก็บ (หากไม่ระบุจะใช้ชื่อ repo เดิม)", "default": ""},
                    },
                    "required": ["repo_url"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_clone_repo(
                repo_url=str(args.get("repo_url", "")),
                target_dir=str(args.get("target_dir", "")),
            ),
        )

        # 32. Install Skill
        self.builtin_tools["install_skill"] = (
            MCPTool(
                name="install_skill",
                description="ติดตั้ง Skill ใหม่ให้กับ AI โดยอัตโนมัติจาก GitHub repository, URL ของ SKILL.md หรือคำสั่ง Markdown โดยตรง เพื่อเพิ่มความสามารถใหม่",
                input_schema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "ชื่อ GitHub repo (เช่น 'owner/repo' หรือ 'owner/repo:skill_name') หรือ URL ของ SKILL.md หรือเนื้อหาคำสั่ง"},
                        "skill_id": {"type": "string", "description": "ID ของ Skill เช่น 'flutter-expert', 'docker-pro' (หากไม่ระบุจะตรวจจับอัตโนมัติ)", "default": ""},
                        "content": {"type": "string", "description": "เนื้อหาคำสั่ง Skill (หากติดตั้งจากข้อความโดยตรง)", "default": ""},
                    },
                    "required": ["source"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_install_skill(
                source=str(args.get("source", "")),
                skill_id=str(args.get("skill_id", "")),
                content=str(args.get("content", "")),
            ),
        )

        # 33. Remove Skill
        self.builtin_tools["remove_skill"] = (
            MCPTool(
                name="remove_skill",
                description="ลบ Skill ที่ติดตั้งออกจากระบบอย่างปลอดภัยตาม ID หรือชื่อโฟลเดอร์ของ Skill",
                input_schema={
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string", "description": "ID หรือชื่อโฟลเดอร์ของ Skill ที่ต้องการลบ เช่น 'github-specialist'"},
                    },
                    "required": ["skill_id"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_remove_skill(
                skill_id=str(args.get("skill_id", "")),
            ),
        )

        # 34. List Skills
        self.builtin_tools["list_skills"] = (
            MCPTool(
                name="list_skills",
                description="แสดงรายการ Skill ทั้งหมดที่ติดตั้งอยู่ในระบบ พร้อมสถานะและคำอธิบาย",
                input_schema={
                    "type": "object",
                    "properties": {},
                },
                server_name="builtin",
            ),
            lambda args: _builtin_list_skills(),
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
