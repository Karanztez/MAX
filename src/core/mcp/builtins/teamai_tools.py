"""
src/core/mcp/builtins/teamai_tools.py — Tencent TeamAI CLI integration tools.
Provides seamless team skill, rules, and MCP sync across AI agents.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

try:
    from ..workspace_context import get_workspace_root
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.workspace_context import get_workspace_root  # type: ignore[no-redef]

try:
    from ..types import MCPTool
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]


def get_teamai_binary() -> tuple[list[str], str]:
    """
    Detect teamai executable or npx fallback.
    Returns (command_prefix_list, display_name).
    """
    # 1. Direct binary in PATH
    teamai_path = shutil.which("teamai")
    if teamai_path:
        return ([teamai_path], "teamai")

    # 2. Windows npm global path e.g. %APPDATA%/npm/teamai.cmd
    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            win_cmd = Path(appdata) / "npm" / "teamai.cmd"
            if win_cmd.exists():
                return ([str(win_cmd)], "teamai")

    # 3. Fallback to npx -y teamai-cli
    npx_path = shutil.which("npx")
    if npx_path:
        return ([npx_path, "-y", "teamai-cli"], "npx teamai-cli")

    return ([], "")


def run_teamai(args: list[str], cwd: Optional[str] = None, timeout: int = 90) -> tuple[int, str]:
    """Execute a TeamAI CLI command safely."""
    cmd_prefix, _ = get_teamai_binary()
    if not cmd_prefix:
        return (
            -1,
            "❌ ไม่พบคำสั่ง 'teamai' หรือ 'npx' บนเครื่องของคุณ\n"
            "กรุณาติดตั้ง Node.js 20+ (https://nodejs.org) แล้วติดตั้ง TeamAI ผ่านคำสั่ง:\n"
            "  npm install -g teamai-cli\n"
            "หรือตรวจสอบว่าได้เพิ่ม npm/node ลงใน PATH ของระบบแล้ว",
        )

    full_cmd = cmd_prefix + args
    work_dir = cwd or str(get_workspace_root())

    try:
        # Use shell=True on Windows if executing batch file or npx
        use_shell = os.name == "nt"
        proc = subprocess.run(
            full_cmd,
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=use_shell,
        )
        output = proc.stdout.strip()

        # If pull succeeded, dynamically reload local skills in MAX
        if args and args[0] in ("pull", "init") and proc.returncode == 0:
            try:
                from core.skill_manager import SkillManager
                SkillManager().refresh()
            except Exception:
                try:
                    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]
                    SkillManager().refresh()
                except Exception:
                    pass

        return (proc.returncode, output)
    except subprocess.TimeoutExpired:
        return (-2, f"❌ คำสั่ง TeamAI หมดเวลา (Timeout {timeout}s)")
    except Exception as ex:
        return (-3, f"❌ เกิดข้อผิดพลาดในการรัน TeamAI: {ex}")


def _builtin_teamai_command(subcommand: str = "status", extra_args: str = "") -> str:
    """Run TeamAI subcommand e.g. status, pull, push, init."""
    sub = subcommand.strip()
    if not sub:
        sub = "status"

    args = [sub]
    if extra_args.strip():
        # Split arguments respecting simple spaces
        args.extend(extra_args.strip().split())

    code, output = run_teamai(args)
    if code == 0:
        return output or f"✅ ดำเนินการคำสั่ง 'teamai {sub}' สำเร็จ"
    return output


def _builtin_teamai_sync() -> str:
    """Pull and synchronize team skills, rules, and MCP configurations."""
    code, output = run_teamai(["pull"])
    if code == 0:
        return f"✅ ซิงค์ความรู้และสกิลของทีมจาก TeamAI สำเร็จ:\n\n{output}"
    return output


def get_teamai_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return MCP tool definitions for Tencent TeamAI integration."""
    return {
        "teamai_command": (
            MCPTool(
                name="teamai_command",
                description="รันคำสั่ง Tencent TeamAI CLI เพื่อจัดการ ซิงค์ และแชร์ Skills, Rules และ MCP ร่วมกับทีม (รองรับ status, pull, push, init, source)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "subcommand": {
                            "type": "string",
                            "description": "คำสั่งย่อยของ TeamAI เช่น 'status', 'pull', 'push', 'init', 'roles', 'projects'",
                            "default": "status",
                        },
                        "extra_args": {
                            "type": "string",
                            "description": "พารามิเตอร์เพิ่มเติม เช่น URL ของ repository หรือ flag (เช่น 'https://github.com/my-org/my-skills')",
                            "default": "",
                        },
                    },
                    "required": ["subcommand"],
                },
            ),
            lambda args: _builtin_teamai_command(
                subcommand=str(args.get("subcommand", "status")),
                extra_args=str(args.get("extra_args", "")),
            ),
        ),
        "teamai_sync": (
            MCPTool(
                name="teamai_sync",
                description="ดึงและอัปเดต Skills, Rules, และความรู้ของทีมล่าสุดจาก Git Repo กลางผ่าน TeamAI CLI (teamai pull)",
                input_schema={
                    "type": "object",
                    "properties": {},
                },
            ),
            lambda _args: _builtin_teamai_sync(),
        ),
    }
