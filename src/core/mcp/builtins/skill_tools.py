"""Autonomous skill management tools (install, delete, and list skills)."""

from __future__ import annotations

from typing import Any

try:
    from ..types import MCPTool
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]


def _get_skill_manager() -> Any:
    try:
        from core.skill_manager import SkillManager
        return SkillManager()
    except (ImportError, ModuleNotFoundError):
        pass

    try:
        from ...skill_manager import SkillManager
        return SkillManager()
    except (ImportError, ModuleNotFoundError):
        pass

    try:
        from src.core.skill_manager import SkillManager  # type: ignore[no-redef]
        return SkillManager()
    except (ImportError, ModuleNotFoundError):
        return None


def _builtin_install_skill(source: str, skill_id: str = "", content: str = "") -> str:
    """Install a skill from GitHub repository, URL, or raw markdown content."""
    mgr = _get_skill_manager()
    if not mgr:
        return "Error: Cannot initialize SkillManager"

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
    mgr = _get_skill_manager()
    if not mgr:
        return "Error: Cannot initialize SkillManager"

    _ok, msg = mgr.delete_skill(skill_id)
    return msg


def _builtin_list_skills() -> str:
    """List all installed skills with status, description and paths."""
    mgr = _get_skill_manager()
    if not mgr:
        return "Error: Cannot initialize SkillManager"

    skills = mgr.list_skills_info()
    if not skills:
        return "ℹ️ ยังไม่มี Skill ใดติดตั้งในระบบ (โฟลเดอร์ skills/ ว่างเปล่า)"

    lines = [f"📦 ทักษะ (Skills) ที่ติดตั้งในระบบทั้งหมด ({len(skills)} รายการ):\n"]
    for idx, s in enumerate(skills, 1):
        def_tag = " [Default: เปิดใช้งานเสมอ]" if s.get("default") else ""
        desc = s.get("description") or "ไม่มีคำอธิบาย"
        lines.append(f"{idx}. 🧩 **{s['name']}** (`{s['id']}`){def_tag}\n   คำอธิบาย: {desc}\n   พาธ: {s['path']}")

    return "\n\n".join(lines)


def get_skill_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return dictionary of skill management tools."""
    return {
        "install_skill": (
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
        ),
        "remove_skill": (
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
        ),
        "list_skills": (
            MCPTool(
                name="list_skills",
                description="แสดงรายการ Skill ทั้งหมดที่ติดตั้งอยู่ในระบบ พร้อมสถานะและคำอธิบาย",
                input_schema={
                    "type": "object",
                    "properties": {},
                },
                server_name="builtin",
            ),
            lambda _args: _builtin_list_skills(),
        ),
    }
