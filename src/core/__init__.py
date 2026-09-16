"""
Core logic and backend services for MaxPlus AI.
"""

from .ai_client import AIClient, ask, chat
from .mcp_manager import MCPManager, MCPTool
from .provider_profiles import default_profiles, normalize_profile, normalize_profiles, new_custom_profile
from .settings_store import SettingsStore
from .skill_manager import Skill, SkillManager

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
