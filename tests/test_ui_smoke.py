"""
tests/test_ui_smoke.py — Smoke tests for UI widgets, MessageBubble, SettingsDialog, and themes.
"""

import sys
import unittest
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ui.main_window import MaxPlusGUI
from src.ui.widgets.message_bubble import MessageBubble
from src.ui.dialogs.settings_dialog import SettingsDialog
from src.ui.themes import T, DARK, LIGHT


class TestUISmoke(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_themes_keys(self) -> None:
        required = ["bg", "bg2", "bg3", "fg", "fg_dim", "sub", "border", "accent", "ai_hdr", "user_hdr", "code_bg", "code_fg"]
        for k in required:
            self.assertIn(k, DARK, f"Missing key {k} in DARK theme")
            self.assertIn(k, LIGHT, f"Missing key {k} in LIGHT theme")
            self.assertIn(k, T, f"Missing key {k} in active T theme")

    def test_message_bubble_creation(self) -> None:
        # User bubble
        b_user = MessageBubble(self.root, "You", "Hello world", T["bg_user"], T["user_hdr"])
        self.assertEqual(b_user._role_kind, "user")

        # AI thinking bubble
        b_ai = MessageBubble(self.root, "AI", "", T["bg_ai"], T["ai_hdr"], is_thinking=True)
        self.assertEqual(b_ai._role_kind, "ai")
        b_ai.add_step("Calling MCP tool", "args: {'x': 1}", status="running")
        b_ai.add_step("Tool output", "result: 42", status="done")
        b_ai.finish_processing("Here is the final answer:\n```python\nprint('hello')\n```", role="AI 🛠", elapsed_sec=2.5)

        self.assertIn("42", b_ai._steps[1]["detail"])
        self.assertEqual(b_ai._content, "Here is the final answer:\n```python\nprint('hello')\n```")

    def test_settings_dialog_creation(self) -> None:
        from src.core.provider_profiles import default_profiles
        profiles = default_profiles()
        saved = False

        def on_save(p, sid, rem):
            nonlocal saved
            saved = True

        dlg = SettingsDialog(self.root, profiles, profiles[0]["id"], True, on_save)
        self.assertIsNotNone(dlg)
        dlg.destroy()

    def test_health_dialog_creation(self) -> None:
        from src.core.provider_profiles import default_profiles
        from src.ui.dialogs.health_dialog import HealthCheckDialog
        profiles = default_profiles()
        dlg = HealthCheckDialog(self.root, profiles, profiles[0]["id"])
        self.assertIsNotNone(dlg)
        dlg.destroy()


if __name__ == "__main__":
    unittest.main()
