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


try:
    from ...screen_manager import ScreenManager
except (ImportError, ModuleNotFoundError):
    from src.core.screen_manager import ScreenManager  # type: ignore[no-redef]

_global_screen_manager: Optional[ScreenManager] = None


def get_screen_manager() -> ScreenManager:
    global _global_screen_manager
    if _global_screen_manager is None:
        _global_screen_manager = ScreenManager()
    return _global_screen_manager


def set_screen_manager(mgr: ScreenManager) -> None:
    global _global_screen_manager
    _global_screen_manager = mgr


def _builtin_list_screens(_args: dict[str, Any]) -> str:
    mgr = get_screen_manager()
    screens = mgr.list_screens()
    lines = [f"🖥️ รายการ MAX Screens ({len(screens)} หน้าจอ):"]
    lines.append(f"{'ID':<4} {'Name':<16} {'Role':<12} {'Model':<20} {'Linked To':<10} {'Msgs'}")
    lines.append("-" * 70)
    for s in screens:
        active_mark = "*" if s.id == mgr.active_id else " "
        link_str = f"Screen {s.linked_to}" if s.linked_to else "-"
        m_str = s.model or "default"
        lines.append(f"{s.id + active_mark:<4} {s.name:<16} {s.role:<12} {m_str[:18]:<20} {link_str:<10} {len(s.history)}")
    return "\n".join(lines)


def _builtin_create_screen(args: dict[str, Any]) -> str:
    name = str(args.get("name") or "New Screen")
    role = str(args.get("role") or "general")
    model = str(args.get("model") or "")
    link_to = str(args.get("link_to") or "") or None
    mgr = get_screen_manager()
    s = mgr.create_screen(name=name, role=role, model=model, linked_to=link_to)
    return f"สร้าง Screen {s.id}: '{s.name}' ({s.role}) สำเร็จ"


def _builtin_switch_screen(args: dict[str, Any]) -> str:
    sid = str(args.get("screen_id") or "")
    mgr = get_screen_manager()
    if mgr.switch_screen(sid):
        s = mgr.active_screen
        return f"สลับไปยัง Screen {s.id}: '{s.name}' สำเร็จ"
    return f"ไม่พบ Screen ID: {sid}"


def _builtin_link_screens(args: dict[str, Any]) -> str:
    fid = str(args.get("from_screen_id") or args.get("from_id") or "")
    tid = str(args.get("to_screen_id") or args.get("to_id") or "")
    mgr = get_screen_manager()
    if mgr.link_screens(fid, tid):
        return f"เชื่อมโยง Screen {fid} ➔ Screen {tid} สำเร็จ"
    return f"ไม่สามารถเชื่อมโยง Screen {fid} กับ {tid} ได้"


# Aliases for convenience
_builtin_screen_list = _builtin_list_screens
_builtin_screen_create = _builtin_create_screen
_builtin_screen_switch = _builtin_switch_screen
_builtin_screen_link = _builtin_link_screens


def get_workspace_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return MCP tools for workspace tab, team, and screen management."""
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
        "screen_list": (
            MCPTool(
                name="screen_list",
                description="ดูรายการ MAX Virtual Screens ทั้งหมด (1, 2, 3...) และสถานะการเชื่อมต่อ (Link Screen)",
                input_schema={
                    "type": "object",
                    "properties": {},
                },
            ),
            lambda args: _builtin_list_screens(args),
        ),
        "screen_create": (
            MCPTool(
                name="screen_create",
                description="สร้าง Screen ใหม่ด้วยตนเอง พร้อมกำหนดชื่อ บทบาท และลิงก์ไปยัง Screen อื่น",
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "ชื่อ Screen เช่น 'Tester', 'DevOps'"},
                        "role": {"type": "string", "description": "บทบาทหน้าที่", "default": "general"},
                        "model": {"type": "string", "description": "โมเดลที่ต้องการใช้", "default": ""},
                        "link_to": {"type": "string", "description": "ID ของ Screen ถัดไปที่ต้องการส่งต่อข้อมูลไปหา", "default": ""},
                    },
                    "required": ["name"],
                },
            ),
            lambda args: _builtin_create_screen(args),
        ),
        "screen_switch": (
            MCPTool(
                name="screen_switch",
                description="สลับไปยัง Screen ที่ระบุด้วย ID (เช่น '1', '2', '3')",
                input_schema={
                    "type": "object",
                    "properties": {
                        "screen_id": {"type": "string", "description": "ID ของ Screen ที่ต้องการสลับไป เช่น '1', '2'"},
                    },
                    "required": ["screen_id"],
                },
            ),
            lambda args: _builtin_switch_screen(args),
        ),
        "screen_link": (
            MCPTool(
                name="screen_link",
                description="เชื่อมโยง (Link) หน้าจอสองหน้าจอเข้าด้วยกัน เพื่อให้ Screen แรกส่งต่อ Output ไปยัง Screen ถัดไป",
                input_schema={
                    "type": "object",
                    "properties": {
                        "from_screen_id": {"type": "string", "description": "ID ของ Screen ต้นทาง เช่น '1'"},
                        "to_screen_id": {"type": "string", "description": "ID ของ Screen ปลายทาง เช่น '2'"},
                    },
                    "required": ["from_screen_id", "to_screen_id"],
                },
            ),
            lambda args: _builtin_link_screens(args),
        ),
    }

