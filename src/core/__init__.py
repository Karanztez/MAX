"""
Core logic and backend services for MaxPlus AI.
"""

from src.core.ai_client import AIClient, ask, chat
from src.core.mcp_manager import MCPManager, MCPTool
from src.core.provider_profiles import default_profiles, normalize_profile, normalize_profiles, new_custom_profile
from src.core.settings_store import SettingsStore
from src.core.skill_manager import Skill, SkillManager

__all__ = [
    "AIClient",
    "ask",
    "chat",
    "MCPManager",
    "MCPTool",
    "default_profiles",
    "normalize_profile",
    "normalize_profiles",
    "new_custom_profile",
    "SettingsStore",
    "Skill",
    "SkillManager",
]
