"""
tests/test_gui_window.py — Comprehensive smoke test for MAX GUI window lifecycle and components.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

try:
    from ui.main_window import MaxPlusGUI
except (ImportError, ModuleNotFoundError):
    from src.ui.main_window import MaxPlusGUI  # type: ignore[no-redef]


class TestGUIWindow(unittest.TestCase):
    def setUp(self) -> None:
        self.app = None

    def tearDown(self) -> None:
        if self.app:
            try:
                self.app.destroy()
            except Exception:
                pass

    def test_main_gui_window_initialization(self) -> None:
        """Test full MaxPlusGUI window instantiation and component binding."""
        try:
            self.app = MaxPlusGUI()
            self.app.withdraw()  # Keep hidden during automated tests
        except Exception as e:
            self.skipTest(f"Tkinter display not available: {e}")

        # Verify core subsystems and attributes
        self.assertIsNotNone(self.app.settings_store)
        self.assertIsNotNone(self.app.mcp_manager)
        self.assertIsNotNone(self.app.profiles)
        self.assertTrue(len(self.app.profiles) > 0)
        self.assertIsNotNone(self.app.selected_profile_id)

        # Verify tabs exist and at least one chat tab was initialized
        self.assertTrue(len(self.app._tabs) >= 1)
        active_tab = self.app._current_tab()
        self.assertIsNotNone(active_tab)

        # Verify Workspace binding in GUI
        self.assertTrue(hasattr(self.app, "project_path"))
        self.assertTrue(Path(self.app.project_path).exists())

        # Process tkinter event queue to ensure all layout calculations succeed without error
        self.app.update_idletasks()
        self.app.update()

    def test_gui_tab_management(self) -> None:
        """Test opening a new tab in GUI."""
        try:
            self.app = MaxPlusGUI()
            self.app.withdraw()
        except Exception as e:
            self.skipTest(f"Tkinter display not available: {e}")

        initial_count = len(self.app._tabs)
        self.app._new_tab()
        self.assertEqual(len(self.app._tabs), initial_count + 1)

        self.app.update_idletasks()

    def test_gui_chat_tab_messaging(self) -> None:
        """Test sending message, rendering bubbles, and updating chat frame."""
        try:
            self.app = MaxPlusGUI()
            self.app.withdraw()
        except Exception as e:
            self.skipTest(f"Tkinter display not available: {e}")

        active_tab = self.app._current_tab()
        self.assertIsNotNone(active_tab)

        from ui.themes import T
        # Append user message bubble
        b_user = active_tab._add_bubble("You", "Test message from user", T["bg_user"], T["user_hdr"])
        self.assertIsNotNone(b_user)

        # Append AI thinking bubble and complete it
        b_ai = active_tab._add_bubble("AI", "", T["bg_ai"], T["ai_hdr"], is_thinking=True)
        self.assertIsNotNone(b_ai)
        b_ai.add_step("Analyzing workspace", "Directory: src/", status="done")
        b_ai.finish_processing("Verified code changes.", role="AI 🛠", elapsed_sec=0.5)

        self.app.update_idletasks()
        self.app.update()

    def test_gui_project_switch_updates_tools_and_prompt(self) -> None:
        """Verify GUI project folder switch anchors MCP tools and system prompt to the selected project."""
        import tempfile
        from unittest.mock import patch

        try:
            self.app = MaxPlusGUI()
            self.app.withdraw()
        except Exception as e:
            self.skipTest(f"Tkinter display not available: {e}")

        with tempfile.TemporaryDirectory(prefix="max_gui_other_project_") as other_proj:
            other_path = Path(other_proj).resolve()

            with patch("tkinter.filedialog.askdirectory", return_value=str(other_path)):
                self.app._choose_project_folder()

            # 1. Verify app state
            self.assertEqual(Path(self.app.project_path).resolve(), other_path)
            self.assertEqual(Path(self.app.mcp_manager.workspace_root).resolve(), other_path)

            # 2. Verify tool execution writes to the other project
            res = self.app.mcp_manager.execute_tool("write_file", {
                "path": "gui_created_file.py",
                "content": "GUI_TEST = 'ok'\n",
            })
            self.assertNotIn("Error", res)
            created_file = other_path / "gui_created_file.py"
            self.assertTrue(created_file.exists())
            self.assertEqual(created_file.read_text(encoding="utf-8"), "GUI_TEST = 'ok'\n")

            # 3. Verify effective system prompt in active tab is anchored to other project
            active_tab = self.app._current_tab()
            self.assertIsNotNone(active_tab)
            sys_prompt = active_tab._effective_system_prompt()
            self.assertIn(str(other_path), sys_prompt)
            self.assertIn("only report completion when the tool result confirms", sys_prompt)


if __name__ == "__main__":
    unittest.main()

