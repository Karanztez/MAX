"""System execution, process management, clipboard, encoding, and OS utility tools."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
from typing import Any, Optional

try:
    from ..types import MCPTool
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]


_BACKGROUND_TASKS: dict[str, dict[str, Any]] = {}


def _builtin_calculate(expression: str) -> str:
    """Safe arithmetic calculation."""
    expr = expression.strip()
    if not expr:
        return "Error: Expression cannot be empty."

    # Validate characters
    if not re.match(r"^[\d\s\+\-\*\/\%\(\)\.\,\^a-zA-Z_]+$", expr):
        return "Error: Expression contains invalid characters."

    # Disallowed dangerous words
    forbidden = ["import", "exec", "eval", "compile", "open", "file", "os", "sys", "subprocess", "__"]
    for word in forbidden:
        if word in expr.lower():
            return "Error: Expression contains invalid characters."

    safe_dict: dict[str, Any] = {
        "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
        "pow": pow, "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "pi": math.pi, "e": math.e, "log": math.log,
        "log10": math.log10, "ceil": math.ceil, "floor": math.floor,
    }

    try:
        res = eval(expr, {"__builtins__": {}}, safe_dict)  # noqa: S307
        if isinstance(res, float) and res.is_integer():
            return str(int(res))
        return str(res)
    except Exception as ex:
        return f"Calculation Error: {ex}"


def _builtin_get_current_time(timezone: str = "local") -> str:
    """Get formatted system date and time."""
    now = time.localtime()
    iso = time.strftime("%Y-%m-%d %H:%M:%S", now)
    tz_name = time.tzname[0] if time.tzname else "Local"
    return f"{iso} ({tz_name})"


def _builtin_system_info() -> str:
    """Get CPU, Memory, Disk, and OS hardware info."""
    import psutil  # type: ignore[import-untyped]
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        cpu_pct = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)

        return (
            f"💻 OS: {platform.system()} {platform.release()} ({platform.machine()})\n"
            f"🐍 Python: {platform.python_version()}\n"
            f"⚡ CPU: {cpu_count} Cores ({cpu_pct}% Usage)\n"
            f"🧠 RAM: {mem.used / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB ({mem.percent}%)\n"
            f"💾 Disk ({os.path.abspath(os.sep)}): {disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB ({disk.percent}%)"
        )
    except Exception as ex:
        return f"Error gathering system info: {ex}"


def _builtin_run_command(command: str, timeout_seconds: int = 30, background: bool = False) -> str:
    """Execute shell command safely with Windows hang prevention."""
    cmd = command.strip()
    if not cmd:
        return "Error: Command cannot be empty."

    # Background execution
    if background:
        task_id = str(uuid.uuid4())[:8]
        _BACKGROUND_TASKS[task_id] = {
            "command": cmd,
            "status": "running",
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "start_time": time.time(),
        }

        def _worker() -> None:
            try:
                proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                stdout, stderr = proc.communicate()
                _BACKGROUND_TASKS[task_id]["status"] = "completed" if proc.returncode == 0 else "failed"
                _BACKGROUND_TASKS[task_id]["stdout"] = stdout
                _BACKGROUND_TASKS[task_id]["stderr"] = stderr
                _BACKGROUND_TASKS[task_id]["returncode"] = proc.returncode
            except Exception as ex:
                _BACKGROUND_TASKS[task_id]["status"] = "error"
                _BACKGROUND_TASKS[task_id]["stderr"] = str(ex)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return f"🚀 คำสั่งถูกรันใน Background แล้ว (Task ID: {task_id})\nใช้คำสั่ง task_status(task_id='{task_id}') เพื่อตรวจสอบสถานะและผลลัพธ์"

    # Synchronous execution
    proc: Optional[subprocess.Popen[str]] = None
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        ret = proc.returncode
        out = stdout.strip()
        err = stderr.strip()

        res_parts = [f"Exit Code: {ret}"]
        if out:
            res_parts.append(f"\n--- STDOUT ---\n{out}")
        if err:
            res_parts.append(f"\n--- STDERR ---\n{err}")
        return "\n".join(res_parts)
    except subprocess.TimeoutExpired:
        if proc is not None:
            proc.kill()
        return f"Error: Command timed out after {timeout_seconds} seconds."
    except Exception as ex:
        return f"Error executing command: {ex}"


def _builtin_run_python_code(code: str, timeout_seconds: int = 30) -> str:
    """Execute Python code snippet in isolated process."""
    if not code.strip():
        return "Error: Python code cannot be empty."

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        temp_script = f.name

    proc: Optional[subprocess.Popen[str]] = None
    try:
        proc = subprocess.Popen(
            [sys.executable, temp_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        ret = proc.returncode
        out = stdout.strip()
        err = stderr.strip()

        res_parts = [f"Exit Code: {ret}"]
        if out:
            res_parts.append(f"\n--- Output ---\n{out}")
        if err:
            res_parts.append(f"\n--- Errors ---\n{err}")
        return "\n".join(res_parts)
    except subprocess.TimeoutExpired:
        if proc is not None:
            proc.kill()
        return f"Error: Python code execution timed out after {timeout_seconds}s."
    except Exception as ex:
        return f"Error running Python code: {ex}"
    finally:
        try:
            os.remove(temp_script)
        except Exception:
            pass


def _builtin_git_status() -> str:
    return _builtin_run_command("git status", timeout_seconds=15)


def _builtin_git_diff() -> str:
    return _builtin_run_command("git diff", timeout_seconds=15)


def _builtin_git_log(count: int = 5) -> str:
    return _builtin_run_command(f"git log -n {count} --oneline", timeout_seconds=15)


def _builtin_list_processes(count: int = 15) -> str:
    """List active processes."""
    import psutil  # type: ignore[import-untyped]
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: (x.get("cpu_percent") or 0.0), reverse=True)
        lines = [f"{'PID':<8} {'CPU%':<8} {'MEM%':<8} {'NAME'}"]
        for p in procs[:count]:
            lines.append(f"{p.get('pid', ''):<8} {p.get('cpu_percent', 0.0):<8.1f} {p.get('memory_percent', 0.0):<8.1f} {p.get('name', '')}")
        return "\n".join(lines)
    except Exception as ex:
        return f"Error listing processes: {ex}"


def _builtin_get_environment_variable(name: str) -> str:
    val = os.environ.get(name)
    if val is None:
        return f"Environment variable '{name}' is not set."
    return f"{name}={val}"


def _builtin_json_format(json_text: str, indent: int = 2) -> str:
    try:
        data = json.loads(json_text)
        return json.dumps(data, indent=indent, ensure_ascii=False)
    except Exception as ex:
        return f"Invalid JSON: {ex}"


def _builtin_hash_data(text: str, algorithm: str = "sha256") -> str:
    try:
        h = hashlib.new(algorithm.lower())
        h.update(text.encode("utf-8"))
        return h.hexdigest()
    except Exception as ex:
        return f"Hash error: {ex}"


def _builtin_base64_codec(text: str, action: str = "encode") -> str:
    try:
        if action.lower() == "decode":
            return base64.b64decode(text.encode("utf-8")).decode("utf-8", errors="replace")
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")
    except Exception as ex:
        return f"Base64 error: {ex}"


def _builtin_task_status(task_id: str) -> str:
    """Check background task status."""
    if task_id not in _BACKGROUND_TASKS:
        return f"Error: Task ID '{task_id}' not found."
    t = _BACKGROUND_TASKS[task_id]
    dur = time.time() - t["start_time"]
    res = [
        f"Task ID: {task_id}",
        f"Command: {t['command']}",
        f"Status: {t['status'].upper()} (Elapsed: {dur:.1f}s)",
    ]
    if t["returncode"] is not None:
        res.append(f"Return Code: {t['returncode']}")
    if t["stdout"]:
        res.append(f"\n--- STDOUT ---\n{t['stdout'][:4000]}")
    if t["stderr"]:
        res.append(f"\n--- STDERR ---\n{t['stderr'][:2000]}")
    return "\n".join(res)


def _builtin_get_clipboard() -> str:
    try:
        import pyperclip  # type: ignore[import-untyped]
        return pyperclip.paste() or "(Clipboard is empty)"
    except Exception as ex:
        return f"Error reading clipboard: {ex}"


def _builtin_set_clipboard(text: str) -> str:
    try:
        import pyperclip  # type: ignore[import-untyped]
        pyperclip.copy(text)
        return f"✅ Copied {len(text)} characters to clipboard."
    except Exception as ex:
        return f"Error writing to clipboard: {ex}"


def get_system_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return dictionary of system tools."""
    return {
        "calculate": (
            MCPTool(
                name="calculate",
                description="คำนวณคณิตศาสตร์ทางคณิตศาสตร์อย่างปลอดภัย",
                input_schema={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "นิพจน์คณิตศาสตร์ เช่น 12 * 5 + 8"},
                    },
                    "required": ["expression"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_calculate(str(args.get("expression", ""))),
        ),
        "get_current_time": (
            MCPTool(
                name="get_current_time",
                description="ตรวจสอบวันที่และเวลาปัจจุบันของระบบ",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin",
            ),
            lambda _args: _builtin_get_current_time(),
        ),
        "get_system_info": (
            MCPTool(
                name="get_system_info",
                description="ตรวจสอบข้อมูลระบบฮาร์ดแวร์ (CPU, RAM, Disk, OS)",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin",
            ),
            lambda _args: _builtin_system_info(),
        ),
        "system_info": (
            MCPTool(
                name="system_info",
                description="ตรวจสอบข้อมูลระบบฮาร์ดแวร์ (CPU, RAM, พื้นที่ Disk, ระบบปฏิบัติการ)",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin",
            ),
            lambda _args: _builtin_system_info(),
        ),
        "run_command": (
            MCPTool(
                name="run_command",
                description="รันคำสั่ง Shell / Terminal (รองรับทั้งแบบรันปกติและ Background Task)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "คำสั่งที่ต้องการรัน เช่น git status, python test.py, ls -la"},
                        "timeout_seconds": {"type": "integer", "description": "เวลารอคอยสูงสุดเป็นวินาที (ค่าเริ่มต้น 30)", "default": 30},
                        "background": {"type": "boolean", "description": "รันเบื้องหลังทันทีโดยไม่บล็อกรอบการทำงานหรือไม่", "default": False},
                    },
                    "required": ["command"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_run_command(
                str(args.get("command", "")),
                timeout_seconds=int(args.get("timeout_seconds", 30)),
                background=bool(args.get("background", False)),
            ),
        ),
        "run_python_code": (
            MCPTool(
                name="run_python_code",
                description="รันสคริปต์โค้ด Python ใน Sandbox ชั่วคราว",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "โค้ด Python ที่ต้องการรัน"},
                        "timeout_seconds": {"type": "integer", "description": "เวลาจำกัดการทำงาน", "default": 30},
                    },
                    "required": ["code"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_run_python_code(
                str(args.get("code", "")),
                timeout_seconds=int(args.get("timeout_seconds", 30)),
            ),
        ),
        "git_status": (
            MCPTool(
                name="git_status",
                description="ตรวจสอบสถานะ Git ของโปรเจกต์ (git status)",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin",
            ),
            lambda _args: _builtin_git_status(),
        ),
        "git_diff": (
            MCPTool(
                name="git_diff",
                description="ตรวจสอบความเปลี่ยนแปลงของโค้ดที่ยังไม่ได้ commit (git diff)",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin",
            ),
            lambda _args: _builtin_git_diff(),
        ),
        "git_log": (
            MCPTool(
                name="git_log",
                description="ดูประวัติการ commit ย้อนหลัง (git log)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "จำนวน commit ที่ต้องการดู", "default": 5},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_git_log(int(args.get("count", 5))),
        ),
        "list_processes": (
            MCPTool(
                name="list_processes",
                description="แสดงรายการโปรเซสที่กำลังทำงานอยู่ในระบบ",
                input_schema={
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "จำนวนโปรเซสที่ต้องการแสดง", "default": 15},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_list_processes(int(args.get("count", 15))),
        ),
        "get_environment_variable": (
            MCPTool(
                name="get_environment_variable",
                description="อ่านค่าตัวแปรสภาพแวดล้อม (Environment Variable)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "ชื่อของตัวแปร เช่น PATH, HOME"},
                    },
                    "required": ["name"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_get_environment_variable(str(args.get("name", ""))),
        ),
        "json_format": (
            MCPTool(
                name="json_format",
                description="จัดรูปแบบข้อความ JSON ให้อ่านง่าย (Prettify JSON)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "json_text": {"type": "string", "description": "ข้อความ JSON"},
                        "indent": {"type": "integer", "description": "จำนวนช่องไฟย่อหน้า (ค่าเริ่มต้น 2)", "default": 2},
                    },
                    "required": ["json_text"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_json_format(str(args.get("json_text", "")), indent=int(args.get("indent", 2))),
        ),
        "hash_data": (
            MCPTool(
                name="hash_data",
                description="คำนวณ Hash (SHA256, MD5, SHA1) ของข้อความ",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "ข้อความที่ต้องการคำนวณ Hash"},
                        "algorithm": {"type": "string", "description": "อัลกอริทึม (sha256, md5, sha1)", "default": "sha256"},
                    },
                    "required": ["text"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_hash_data(str(args.get("text", "")), algorithm=str(args.get("algorithm", "sha256"))),
        ),
        "base64_codec": (
            MCPTool(
                name="base64_codec",
                description="เข้ารหัสหรือถอดรหัสข้อความแบบ Base64",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "ข้อความที่ต้องการแปลง"},
                        "action": {"type": "string", "description": "encode หรือ decode", "default": "encode"},
                    },
                    "required": ["text"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_base64_codec(str(args.get("text", "")), action=str(args.get("action", "encode"))),
        ),
        "task_status": (
            MCPTool(
                name="task_status",
                description="ตรวจสอบสถานะและผลลัพธ์ของคำสั่งที่รันใน Background (Task ID)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "รหัส Task ID"},
                    },
                    "required": ["task_id"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_task_status(str(args.get("task_id", ""))),
        ),
        "get_clipboard": (
            MCPTool(
                name="get_clipboard",
                description="อ่านข้อความล่าสุดที่คัดลอกอยู่ใน Clipboard ของระบบ",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin",
            ),
            lambda _args: _builtin_get_clipboard(),
        ),
        "set_clipboard": (
            MCPTool(
                name="set_clipboard",
                description="คัดลอกข้อความที่กำหนดลงใน Clipboard ของระบบ",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "ข้อความที่ต้องการ Copy"},
                    },
                    "required": ["text"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_set_clipboard(str(args.get("text", ""))),
        ),
    }
