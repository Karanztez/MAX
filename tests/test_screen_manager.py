"""
tests/test_screen_manager.py — Unit tests for MAX Screen Manager, linked pipeline, and CLI screen commands.
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

_root = str(Path(__file__).resolve().parent.parent)
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from core.screen_manager import Screen, ScreenManager
    from core.mcp.builtins.workspace_tools import (
        get_screen_manager,
        set_screen_manager,
        _builtin_screen_list,
        _builtin_screen_create,
        _builtin_screen_switch,
        _builtin_screen_link,
    )
    from cli import MaxTerminalApp
except (ImportError, ModuleNotFoundError):
    from src.core.screen_manager import Screen, ScreenManager  # type: ignore[import-not-found,no-redef]
    from src.core.mcp.builtins.workspace_tools import (  # type: ignore[import-not-found,no-redef]
        get_screen_manager,
        set_screen_manager,
        _builtin_screen_list,
        _builtin_screen_create,
        _builtin_screen_switch,
        _builtin_screen_link,
    )
    from src.cli import MaxTerminalApp  # type: ignore[import-not-found,no-redef]


class TestScreenManager(unittest.TestCase):
    def setUp(self):
        self.mgr = ScreenManager()

    def test_default_screen(self):
        screens = self.mgr.list_screens()
        self.assertEqual(len(screens), 1)
        self.assertEqual(screens[0].id, "1")
        self.assertEqual(screens[0].name, "Main")
        self.assertEqual(self.mgr.active_id, "1")
        self.assertEqual(self.mgr.active_screen.id, "1")

    def test_create_sequential_screens(self):
        s2 = self.mgr.create_screen(name="Coder", role="coder", model="qwen-2.5")
        self.assertEqual(s2.id, "2")
        self.assertEqual(s2.name, "Coder")
        self.assertEqual(s2.role, "coder")
        self.assertEqual(s2.model, "qwen-2.5")

        s3 = self.mgr.create_screen(name="Reviewer", role="reviewer")
        self.assertEqual(s3.id, "3")

        s4 = self.mgr.create_screen(name="Tester")
        self.assertEqual(s4.id, "4")

        screens = self.mgr.list_screens()
        self.assertEqual(len(screens), 4)
        self.assertEqual([s.id for s in screens], ["1", "2", "3", "4"])

    def test_switch_screen(self):
        self.mgr.create_screen(name="Second")
        self.assertTrue(self.mgr.switch_screen("2"))
        self.assertEqual(self.mgr.active_id, "2")
        self.assertEqual(self.mgr.active_screen.name, "Second")

        # Non-existent screen
        self.assertFalse(self.mgr.switch_screen("999"))
        self.assertEqual(self.mgr.active_id, "2")

    def test_link_and_unlink_screens(self):
        self.mgr.create_screen(name="Planner")
        self.mgr.create_screen(name="Coder")
        # Link 1 -> 2 -> 3
        self.assertTrue(self.mgr.link_screens("1", "2"))
        self.assertTrue(self.mgr.link_screens("2", "3"))

        s1 = self.mgr.get_screen("1")
        s2 = self.mgr.get_screen("2")
        s3 = self.mgr.get_screen("3")
        assert s1 is not None and s2 is not None and s3 is not None
        self.assertEqual(s1.linked_to, "2")
        self.assertEqual(s2.linked_to, "3")
        self.assertIsNone(s3.linked_to)

        # Cannot link to self
        self.assertFalse(self.mgr.link_screens("1", "1"))
        # Cannot link non-existent
        self.assertFalse(self.mgr.link_screens("1", "99"))

        # Unlink
        self.assertTrue(self.mgr.unlink_screen("1"))
        s1 = self.mgr.get_screen("1")
        assert s1 is not None
        self.assertIsNone(s1.linked_to)

    def test_remove_screen(self):
        self.mgr.create_screen(name="Screen 2")
        self.mgr.link_screens("1", "2")
        self.assertTrue(self.mgr.remove_screen("2"))
        self.assertEqual(len(self.mgr.list_screens()), 1)
        # Link to 2 should be cleaned
        s1 = self.mgr.get_screen("1")
        assert s1 is not None
        self.assertIsNone(s1.linked_to)

        # Cannot remove only screen
        self.assertFalse(self.mgr.remove_screen("1"))
        self.assertEqual(len(self.mgr.list_screens()), 1)

    def test_setup_team_screens(self):
        team = self.mgr.setup_team_screens(default_model="deepseek-v3")
        self.assertEqual(len(team), 3)
        self.assertEqual([s.id for s in team], ["1", "2", "3"])
        self.assertEqual(team[0].name, "Planner")
        self.assertEqual(team[0].role, "planner")
        self.assertEqual(team[0].linked_to, "2")
        self.assertEqual(team[0].model, "deepseek-v3")

        self.assertEqual(team[1].name, "Coder")
        self.assertEqual(team[1].role, "coder")
        self.assertEqual(team[1].linked_to, "3")

        self.assertEqual(team[2].name, "Reviewer")
        self.assertEqual(team[2].role, "reviewer")
        self.assertIsNone(team[2].linked_to)


class TestScreenMCPTools(unittest.TestCase):
    def setUp(self):
        self.mgr = ScreenManager()
        set_screen_manager(self.mgr)

    def test_screen_list_tool(self):
        out = _builtin_screen_list({})
        self.assertIn("1*", out)
        self.assertIn("Main", out)

    def test_screen_create_tool(self):
        res = _builtin_screen_create({"name": "Research", "role": "researcher", "model": "gemini-pro"})
        self.assertIn("Screen 2", res)
        self.assertIn("Research", res)
        self.assertEqual(len(self.mgr.list_screens()), 2)

    def test_screen_switch_tool(self):
        self.mgr.create_screen(name="Research")
        res = _builtin_screen_switch({"screen_id": "2"})
        self.assertIn("Screen 2", res)
        self.assertEqual(self.mgr.active_id, "2")

    def test_screen_link_tool(self):
        self.mgr.create_screen(name="Coder")
        res = _builtin_screen_link({"from_id": "1", "to_id": "2"})
        self.assertIn("Screen 1", res)
        self.assertIn("Screen 2", res)
        s1 = self.mgr.get_screen("1")
        assert s1 is not None
        self.assertEqual(s1.linked_to, "2")


class TestCLIScreenIntegration(unittest.TestCase):
    @patch("src.cli.SettingsStore.has_saved_key", return_value=True)
    def setUp(self, _mock_has_key):
        self.app = MaxTerminalApp()

    def test_cli_screen_list_command(self):
        self.assertTrue(self.app.handle_command("/screens"))
        self.assertTrue(self.app.handle_command("/screen list"))

    def test_cli_screen_create_and_switch(self):
        self.assertTrue(self.app.handle_command("/screen create Dev coder"))
        screens = self.app.screen_manager.list_screens()
        self.assertEqual(len(screens), 2)
        self.assertEqual(screens[1].id, "2")
        self.assertEqual(screens[1].name, "Dev")

        # Switch using "/screen 2"
        self.assertTrue(self.app.handle_command("/screen 2"))
        self.assertEqual(self.app.screen_manager.active_id, "2")

        # Switch using "/screen 1"
        self.assertTrue(self.app.handle_command("/screen 1"))
        self.assertEqual(self.app.screen_manager.active_id, "1")

    def test_cli_screen_link_and_unlink(self):
        self.app.handle_command("/screen create Coder coder")
        self.assertTrue(self.app.handle_command("/screen link 1 2"))
        s1 = self.app.screen_manager.get_screen("1")
        assert s1 is not None
        self.assertEqual(s1.linked_to, "2")

        self.assertTrue(self.app.handle_command("/screen unlink 1"))
        s1_after = self.app.screen_manager.get_screen("1")
        assert s1_after is not None
        self.assertIsNone(s1_after.linked_to)

    def test_cli_team_init_and_status(self):
        self.assertTrue(self.app.handle_command("/team init"))
        screens = self.app.screen_manager.list_screens()
        self.assertEqual(len(screens), 3)
        self.assertEqual(screens[0].name, "Planner")
        self.assertEqual(screens[0].linked_to, "2")
        self.assertEqual(screens[1].name, "Coder")
        self.assertEqual(screens[1].linked_to, "3")
        self.assertEqual(screens[2].name, "Reviewer")
        self.assertIsNone(screens[2].linked_to)

        self.assertTrue(self.app.handle_command("/team status"))


if __name__ == "__main__":
    unittest.main()
