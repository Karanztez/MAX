"""
tests/test_cli.py — Unit tests for Terminal & Mobile CLI features.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from src.cli import MaxTerminalApp
    from src.core.settings_store import SettingsStore
except (ImportError, ModuleNotFoundError):
    from cli import MaxTerminalApp  # type: ignore[no-redef]
    from core.settings_store import SettingsStore  # type: ignore[no-redef]


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.settings_path = Path(self.tmpdir.name) / "settings.json"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_cli_initialization(self) -> None:
        with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(tempfile.gettempdir()) / "test_s.json")):
            app = MaxTerminalApp()
            self.assertIsNotNone(app.active_profile)
            self.assertTrue(len(app.profiles) > 0)

    def test_handle_profile_number_switch(self) -> None:
        with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(tempfile.gettempdir()) / "test_s.json")):
            app = MaxTerminalApp()
            # Switch to profile 2
            app.handle_command("/profile 2")
            self.assertEqual(app.active_profile["id"], app.profiles[1]["id"])

    def test_handle_model_number_switch(self) -> None:
        with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(tempfile.gettempdir()) / "test_s.json")):
            app = MaxTerminalApp()
            models = app.active_profile.get("models", [])
            if len(models) >= 2:
                app.handle_command("/model 2")
                self.assertEqual(app.active_profile["model"], models[1])

    def test_handle_key_and_baseurl_commands(self) -> None:
        with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(tempfile.gettempdir()) / "test_s.json")):
            app = MaxTerminalApp()
            app.handle_command("/key test-secret-key-1234")
            self.assertEqual(app.active_profile["api_key"], "test-secret-key-1234")

            app.handle_command("/baseurl https://api.custom.ai/v1")
            self.assertEqual(app.active_profile["base_url"], "https://api.custom.ai/v1")


if __name__ == "__main__":
    unittest.main()
