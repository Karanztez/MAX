"""
src/core/mcp/builtins/workspace_tools.py — Tools allowing AI to propose creating Tabs and Team Rooms.
Requires explicit user confirmation before creation and directs user to configure Provider and Model settings.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

try:
    from ..types import MCPTool
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]

# Callback registered by GUI (MaxPlusGUI) to handle tab/team creation with user permission
_workspace_ui_dispatcher: Optional[Callable[[str, dict[str, Any]], str]] = None


def set_workspace_ui_dispatcher(
    dispatcher: Optional[Callable[[str, dict[str, Any]], str]],
) -> None:
    """Register GUI dispatcher for workspace tools."""
    global _workspace_ui_dispatcher
    _workspace_ui_dispatcher = dispatcher


def _builtin_create_chat_tab(args: dict[str, Any]) -> str:
    """Request to create a new Chat Tab."""
    if _workspace_ui_dispatcher is None:
        return "ระบบไม่สามารถสร้างแท็บได้เนื่องจากไม่ได้ทำงานในโหมด GUI หรือยังไม่ได้ลงทะเบียน UI Dispatcher"
    return _workspace_ui_dispatcher("create_chat_tab", args)


def _builtin_create_team_room(args: dict[str, Any]) -> str:
    """Request to create a new Multi-Agent Team Room."""
    if _workspace_ui_dispatcher is None:
        return "ระบบไม่สามารถสร้างห้องทีมได้เนื่องจากไม่ได้ทำงานในโหมด GUI หรือยังไม่ได้ลงทะเบียน UI Dispatcher"
    return _workspace_ui_dispatcher("create_team_room", args)


def get_workspace_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return MCP tools for workspace tab and team management."""
    return {
        "create_chat_tab": (
            MCPTool(
                name="create_chat_tab",
                description=(
                    "ขออนุญาตผู้ใช้เพื่อสร้างแท็บสนทนาใหม่ (New Chat Tab) ในหน้าต่างโปรแกรม MAX "
                    "สำหรับแยกหัวข้อการสนทนา บริบทงาน หรือโจทย์ใหม่ "
                    "(ระบบจะแสดงกล่องขออนุญาตผู้ใช้ก่อนเสมอ และให้ผู้ใช้เลือกผู้ให้บริการและโมเดลเอง)"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "tab_name": {
                            "type": "string",
                            "description": "ชื่อแท็บที่ต้องการสร้าง เช่น 'Frontend Dev', 'Data Analyst', 'Code Refactor'",
                        },
                        "system_prompt": {
                            "type": "string",
                            "description": "คำสั่งระบบเริ่มต้นสำหรับแท็บใหม่นี้ (ถ้ามี)",
                            "default": "",
                        },
                        "reason": {
                            "type": "string",
                            "description": "เหตุผลที่เสนอให้สร้างแท็บใหม่เพื่อให้ผู้ใช้พิจารณาอนุญาต",
                        },
                    },
                    "required": ["tab_name", "reason"],
                },
            ),
            lambda args: _builtin_create_chat_tab(args),
        ),
        "create_team_room": (
            MCPTool(
                name="create_team_room",
                description=(
                    "ขออนุญาตผู้ใช้เพื่อสร้างห้องทีม AI (Multi-Agent Team Room) ใหม่ในโปรแกรม MAX "
                    "เพื่อระดมทีม AI หลายบทบาท (Planner, Coder, Reviewer) มาช่วยกันทำงานในโจทย์ที่ซับซ้อน "
                    "(ระบบจะแสดงกล่องขออนุญาตผู้ใช้ก่อนเสมอ และจะเปิดหน้าต่างให้ผู้ใช้ตั้งค่าผู้ให้บริการและโมเดลของแต่ละ Agent ด้วยตนเอง)"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "team_name": {
                            "type": "string",
                            "description": "ชื่อห้องทีม เช่น 'Security Review Team', 'Full-stack Squad'",
                            "default": "👥 Team Room",
                        },
                        "goal": {
                            "type": "string",
                            "description": "เป้าหมายหรือโจทย์หลักสำหรับทีมนี้ (จะถูกใส่ลงในช่องข้อความให้อัตโนมัติ)",
                            "default": "",
                        },
                        "reason": {
                            "type": "string",
                            "description": "เหตุผลที่เสนอให้สร้างห้องทีมเพื่อให้ผู้ใช้พิจารณาอนุญาต",
                        },
                    },
                    "required": ["reason"],
                },
            ),
            lambda args: _builtin_create_team_room(args),
        ),
    }
