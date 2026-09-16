"""
src/core/mcp/builtins/diagnostic_tools.py — Autonomous IDE Diagnostics, Staged Code Drafts,
and Background Test Runner Tools for MAX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

try:
    from ...ide_inspector import IDEInspector
    from ...background_runner import BackgroundTestRunner
    from ...draft_manager import DraftManager
    from ..types import MCPTool
    from ..workspace_context import resolve_workspace_path, get_workspace_root
except (ImportError, ModuleNotFoundError):
    from src.core.ide_inspector import IDEInspector  # type: ignore[no-redef]
    from src.core.background_runner import BackgroundTestRunner  # type: ignore[no-redef]
    from src.core.draft_manager import DraftManager  # type: ignore[no-redef]
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]
    from src.core.mcp.workspace_context import resolve_workspace_path, get_workspace_root  # type: ignore[no-redef]


def _builtin_inspect_ide_diagnostics(path: str = "", project_scan: bool = False) -> str:
    """Inspect IDE diagnostics, syntax errors, and linter warnings for a file or the whole project."""
    workspace = get_workspace_root()
    inspector = IDEInspector(workspace_path=workspace)

    if project_scan or not path:
        target_dir = resolve_workspace_path(path) if path else workspace
        diags = inspector.inspect_project(target_dir)
        return inspector.format_report(diags)

    target_file = resolve_workspace_path(path)
    if not target_file.exists():
        return f"❌ ไม่พบไฟล์เป้าหมาย: {path}"

    diags = inspector.inspect_file(target_file)
    return inspector.format_report(diags)


def _builtin_create_code_draft(file_path: str, content: str, note: str = "") -> str:
    """Create a staged code draft for review without directly modifying the workspace file."""
    workspace = get_workspace_root()
    target = resolve_workspace_path(file_path)
    mgr = DraftManager.get_instance(workspace_path=workspace)

    draft = mgr.create_draft(target, content, metadata={"note": note})
    diag_summary = (
        "✅ โค้ดในแบบร่างถูกต้อง (ไวยากรณ์ผ่าน ไร้ Error)"
        if not draft.has_syntax_error
        else f"⚠️ พบ Error ในแบบร่าง {len(draft.diagnostics)} รายการ (กรุณาตรวจทานในแท็บ Drafts)"
    )

    return (
        f"📝 สร้างแบบร่างรหัส '{draft.draft_id}' สำหรับไฟล์ '{target.name}' สำเร็จแล้ว!\n"
        f"- สถานะ: PENDING (รอการตรวจทานในแท็บ Draft)\n"
        f"- ตรวจทาน IDE: {diag_summary}\n\n"
        f"ดู Diff ตัวอย่าง:\n```diff\n{draft.diff_preview[:1000]}\n```"
    )


def _builtin_apply_code_draft(draft_id: str) -> str:
    """Apply an existing staged draft to the actual file."""
    workspace = get_workspace_root()
    mgr = DraftManager.get_instance(workspace_path=workspace)
    success, msg = mgr.apply_draft(draft_id)
    return f"{'✅' if success else '❌'} {msg}"


def _builtin_discard_code_draft(draft_id: str) -> str:
    """Discard an existing staged draft."""
    workspace = get_workspace_root()
    mgr = DraftManager.get_instance(workspace_path=workspace)
    if mgr.discard_draft(draft_id):
        return f"🗑️ ยกเลิกแบบร่าง '{draft_id}' เรียบร้อยแล้ว"
    return f"❌ ไม่พบแบบร่าง '{draft_id}'"


def _builtin_list_code_drafts() -> str:
    """List all active and recent code drafts."""
    workspace = get_workspace_root()
    mgr = DraftManager.get_instance(workspace_path=workspace)
    drafts = mgr.list_drafts()
    if not drafts:
        return "ℹ️ ขณะนี้ไม่มีแบบร่าง (Draft) ค้างอยู่ในระบบ"

    lines = ["### 📋 รายการแบบร่าง (Code Drafts):", ""]
    for d in drafts:
        badge = "🟡 PENDING" if d.status == "PENDING" else ("🟢 APPLIED" if d.status == "APPLIED" else "⚪ DISCARDED")
        err_badge = " [❌ Has Syntax Error]" if d.has_syntax_error else " [✔ Valid Syntax]"
        lines.append(f"- **ID:** `{d.draft_id}` | ไฟล์: `{Path(d.file_path).name}` | สถานะ: {badge}{err_badge} | วันที่: {d.created_at}")

    return "\n".join(lines)


def _builtin_run_background_test(target_path: str = "", command: str = "", timeout: int = 120) -> str:
    """Start automated tests in the background without freezing the chat or UI."""
    workspace = get_workspace_root()
    runner = BackgroundTestRunner.get_instance(workspace_path=workspace)

    resolved_path = resolve_workspace_path(target_path) if target_path else None
    task_id = runner.start_test_run(
        target_path=resolved_path,
        custom_command=command if command else None,
        timeout_sec=timeout,
    )

    return (
        f"🧪 เริ่มรันการทดสอบเบื้องหลังเรียบร้อยแล้ว (Task ID: `{task_id}`)\n"
        f"- คำสั่ง: `{command or (target_path if target_path else 'unittest discover')}`\n"
        f"- โฟลเดอร์: `{workspace}`\n"
        f"- คุณสามารถตรวจสอบสถานะได้ด้วยเครื่องมือ `get_background_test_status` หรือดูสดในแท็บ Drafts"
    )


def _builtin_get_background_test_status(task_id: str = "") -> str:
    """Check the current status and terminal log output of a background test run."""
    workspace = get_workspace_root()
    runner = BackgroundTestRunner.get_instance(workspace_path=workspace)
    result = runner.get_status(task_id if task_id else None)

    if not result:
        return "ℹ️ ไม่พบประวัติการทดสอบเบื้องหลังที่กำลังรันอยู่"

    lines = [
        f"### 🧪 สถานะการทดสอบเบื้องหลัง (Task ID: `{result.task_id}`)",
        f"- **สถานะ:** {result.status}",
        f"- **สรุป:** {result.summary}",
        f"- **ระยะเวลาที่ใช้:** {result.duration_sec:.2f} วินาที",
    ]
    if result.exit_code is not None:
        lines.append(f"- **Exit Code:** {result.exit_code}")

    if result.stdout or result.stderr:
        out = (result.stdout + "\n" + result.stderr).strip()
        lines.append("\n**Terminal Output Preview (Last 30 lines):**\n```text")
        output_lines = out.splitlines()[-30:]
        lines.append("\n".join(output_lines))
        lines.append("```")

    return "\n".join(lines)


def get_diagnostic_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return dictionary of diagnostic, draft, and test tools."""
    return {
        "inspect_ide_diagnostics": (
            MCPTool(
                name="inspect_ide_diagnostics",
                description="ตรวจทานข้อผิดพลาดทางไวยากรณ์ (Syntax Errors), Type Warnings และปัญหา Static Analysis ในไฟล์หรือทั้งโปรเจกต์",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "เส้นทางไฟล์หรือโฟลเดอร์ที่ต้องการตรวจทาน (เว้นว่างเพื่อตรวจทั้งโปรเจกต์)"},
                        "project_scan": {"type": "boolean", "description": "ตรวจทานทั้งโปรเจกต์หรือไม่ (ค่าเริ่มต้น False)"},
                    },
                },
                server_name="builtin_diagnostics",
            ),
            _builtin_inspect_ide_diagnostics,
        ),
        "create_code_draft": (
            MCPTool(
                name="create_code_draft",
                description="สร้างแบบร่างโค้ด (Draft / Staged Code) ในแท็บ Drafts เพื่อให้ผู้ใช้ตรวจทานและรันทดสอบก่อนนำไปเขียนลงไฟล์จริง",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "ไฟล์เป้าหมายที่จะสร้างแบบร่าง"},
                        "content": {"type": "string", "description": "เนื้อหาโค้ดใหม่ฉบับแบบร่าง"},
                        "note": {"type": "string", "description": "บันทึกเหตุผลหรือคำอธิบายการแก้ไข"},
                    },
                    "required": ["file_path", "content"],
                },
                server_name="builtin_diagnostics",
            ),
            _builtin_create_code_draft,
        ),
        "apply_code_draft": (
            MCPTool(
                name="apply_code_draft",
                description="นำแบบร่างโค้ด (Draft) ที่ผ่านการตรวจทานและทดสอบแล้วไปบันทึกจริงลงในไฟล์",
                input_schema={
                    "type": "object",
                    "properties": {
                        "draft_id": {"type": "string", "description": "รหัสของแบบร่าง (เช่น draft_1710000000_abc123)"},
                    },
                    "required": ["draft_id"],
                },
                server_name="builtin_diagnostics",
            ),
            _builtin_apply_code_draft,
        ),
        "discard_code_draft": (
            MCPTool(
                name="discard_code_draft",
                description="ยกเลิกและลบแบบร่างโค้ดที่ไม่ต้องการ",
                input_schema={
                    "type": "object",
                    "properties": {
                        "draft_id": {"type": "string", "description": "รหัสของแบบร่างที่จะยกเลิก"},
                    },
                    "required": ["draft_id"],
                },
                server_name="builtin_diagnostics",
            ),
            _builtin_discard_code_draft,
        ),
        "list_code_drafts": (
            MCPTool(
                name="list_code_drafts",
                description="แสดงรายการแบบร่างโค้ดทั้งหมดที่กำลังรอการตรวจทานหรือนำไปใช้",
                input_schema={"type": "object", "properties": {}},
                server_name="builtin_diagnostics",
            ),
            _builtin_list_code_drafts,
        ),
        "run_background_test": (
            MCPTool(
                name="run_background_test",
                description="สั่งรันชุดทดสอบอัตโนมัติ (Automated Tests / Unit tests) ใน Background ทันที โดยไม่บล็อกการสนทนาหรือหน้าจอ UI",
                input_schema={
                    "type": "object",
                    "properties": {
                        "target_path": {"type": "string", "description": "ไฟล์ทดสอบหรือโฟลเดอร์ที่ต้องการทดสอบ (เช่น tests/test_mcp_integration.py)"},
                        "command": {"type": "string", "description": "คำสั่งทดสอบเฉพาะ (เช่น pytest tests/)"},
                        "timeout": {"type": "integer", "description": "เวลาจำกัดสูงสุดเป็นวินาที (ค่าเริ่มต้น 120s)"},
                    },
                },
                server_name="builtin_diagnostics",
            ),
            _builtin_run_background_test,
        ),
        "get_background_test_status": (
            MCPTool(
                name="get_background_test_status",
                description="ตรวจสอบสถานะ ผลลัพธ์ และ Terminal Log ของการทดสอบที่รันอยู่ใน Background",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "รหัสงานทดสอบ (เว้นว่างเพื่อดูงานล่าสุด)"},
                    },
                },
                server_name="builtin_diagnostics",
            ),
            _builtin_get_background_test_status,
        ),
    }
