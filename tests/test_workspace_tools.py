"""
tests/test_workspace_tools.py — Unit tests for AI Tab & Team Room creation tools with user consent.
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

_root = str(Path(__file__).resolve().parent.parent)
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from core.mcp.builtins.workspace_tools import (
        get_workspace_tools,
        set_workspace_ui_dispatcher,
    )
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.builtins.workspace_tools import (  # type: ignore[no-redef]
        get_workspace_tools,
        set_workspace_ui_dispatcher,
    )


class TestWorkspaceTools(unittest.TestCase):
    """Test AI workspace tools for creating tabs and team rooms."""

    def tearDown(self):
        set_workspace_ui_dispatcher(None)

    def test_tools_registered(self):
        tools = get_workspace_tools()
        self.assertIn("create_chat_tab", tools)
        self.assertIn("create_team_room", tools)

        chat_tool, chat_fn = tools["create_chat_tab"]
        self.assertEqual(chat_tool.name, "create_chat_tab")
        self.assertIn("tab_name", chat_tool.input_schema["properties"])
        self.assertIn("reason", chat_tool.input_schema["properties"])

        team_tool, team_fn = tools["create_team_room"]
        self.assertEqual(team_tool.name, "create_team_room")
        self.assertIn("team_name", team_tool.input_schema["properties"])
        self.assertIn("reason", team_tool.input_schema["properties"])

    def test_no_dispatcher_fallback(self):
        tools = get_workspace_tools()
        _tool, chat_fn = tools["create_chat_tab"]
        res = chat_fn({"tab_name": "Test", "reason": "Testing"})
        self.assertIn("ระบบไม่สามารถสร้างแท็บได้", res)

    def test_dispatcher_permission_allowed(self):
        tools = get_workspace_tools()
        _tool, chat_fn = tools["create_chat_tab"]

        mock_dispatcher = MagicMock(return_value="สร้างแท็บ 'Frontend' สำเร็จ")
        set_workspace_ui_dispatcher(mock_dispatcher)

        res = chat_fn({"tab_name": "Frontend", "reason": "Work on UI"})
        mock_dispatcher.assert_called_once_with(
            "create_chat_tab", {"tab_name": "Frontend", "reason": "Work on UI"}
        )
        self.assertIn("สร้างแท็บ", res)

    def test_dispatcher_permission_denied(self):
        tools = get_workspace_tools()
        _tool, team_fn = tools["create_team_room"]

        mock_dispatcher = MagicMock(return_value="ผู้ใช้ไม่อนุญาตให้สร้างห้องทีม")
        set_workspace_ui_dispatcher(mock_dispatcher)

        res = team_fn({"team_name": "QA Team", "reason": "Test everything"})
        mock_dispatcher.assert_called_once_with(
            "create_team_room", {"team_name": "QA Team", "reason": "Test everything"}
        )
        self.assertIn("ผู้ใช้ไม่อนุญาต", res)


if __name__ == "__main__":
    unittest.main()
