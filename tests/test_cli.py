"""
tests/test_cli.py — Unit tests for Terminal & Mobile CLI features.
"""

import os
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from cli import MaxTerminalApp
    from core.settings_store import SettingsStore
except (ImportError, ModuleNotFoundError):
    from src.cli import MaxTerminalApp  # type: ignore[no-redef]
    from src.core.settings_store import SettingsStore  # type: ignore[no-redef]


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.settings_path = Path(self.tmpdir.name) / "settings.json"

    def tearDown(self) -> None:
        try:
            from core.mcp.workspace_context import set_workspace_root
        except ImportError:
            from src.core.mcp.workspace_context import set_workspace_root  # type: ignore[no-redef]
        set_workspace_root(Path.cwd())
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

    def test_handle_export_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sample_file = Path(tmp_dir) / "test.txt"
            sample_file.write_text("MAX export test content", encoding="utf-8")
            with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(tempfile.gettempdir()) / "test_s.json")):
                app = MaxTerminalApp()
                res = app.handle_command(f"/export {tmp_dir}")
                self.assertTrue(res)

    def test_handle_profile_flexible_switch(self) -> None:
        with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(tempfile.gettempdir()) / "test_s.json")):
            app = MaxTerminalApp()
            app.handle_command("/profile china")
            self.assertIn("china", app.active_profile["id"].lower())
            self.assertEqual(app.active_profile["base_url"], "https://api.maxplus-ai.cc/china-town/v1")

    def test_run_cli_provider_and_model_args(self) -> None:
        from cli import run_cli
        with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(tempfile.gettempdir()) / "test_s.json")):
            with patch.object(MaxTerminalApp, "run_prompt_single") as mock_run:
                run_cli(["-P", "china", "-m", "glm-5.3", "-p", "hello"])
                mock_run.assert_called_once_with("hello")

    def test_cli_workspace_routes_relative_tools_and_system_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(project_dir) / "settings.json")):
                app = MaxTerminalApp()
                app.set_workspace(project_dir)

                result = app.mcp_manager.execute_tool("write_file", {
                    "path": "src/cli_created.py",
                    "content": "CLI_OK = True\n",
                })
                target = Path(project_dir) / "src" / "cli_created.py"
                self.assertTrue(target.exists())
                self.assertEqual(target.read_text(encoding="utf-8"), "CLI_OK = True\n")
                self.assertNotIn("Error", result)

                client = app._create_client()
                self.assertIn(str(Path(project_dir).resolve()), client.system_prompt)
                self.assertIn("verify changes on disk", client.system_prompt)

    def test_workspace_slash_command_supports_paths_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="max cli project ") as project_dir:
            with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(project_dir) / "settings.json")):
                app = MaxTerminalApp()
                self.assertTrue(app.handle_command(f'/workspace "{project_dir}"'))
                self.assertEqual(app.workspace_path, Path(project_dir).resolve())

    def test_run_cli_workspace_argument_is_applied_before_prompt(self) -> None:
        from cli import run_cli

        with tempfile.TemporaryDirectory() as project_dir:
            observed = {}

            def fake_run_prompt(app, prompt):
                observed["prompt"] = prompt
                observed["workspace"] = app.workspace_path

            with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(project_dir) / "settings.json")):
                with patch.object(MaxTerminalApp, "run_prompt_single", fake_run_prompt):
                    run_cli(["--workspace", project_dir, "--prompt", "fix it"])

            self.assertEqual(observed["prompt"], "fix it")
            self.assertEqual(observed["workspace"], Path(project_dir).resolve())

    def test_team_pipeline_can_execute_project_tools(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(project_dir) / "settings.json")):
                app = MaxTerminalApp()
                app.set_workspace(project_dir)

                class FakeClient:
                    def chat_with_tools(self, prompt, history, tools, tool_executor, on_status):
                        tool_executor("write_file", {"path": "team_result.txt", "content": "done\n"})
                        return history + [
                            {"role": "user", "content": prompt},
                            {"role": "assistant", "content": "Implemented and verified."},
                        ], ["write_file"]

                with patch.object(app, "_create_client", return_value=FakeClient()):
                    app._run_team_pipeline("Create the requested file")

                self.assertEqual(
                    (Path(project_dir) / "team_result.txt").read_text(encoding="utf-8"),
                    "done\n",
                )

    def test_single_prompt_tool_loop_edits_another_project_end_to_end(self) -> None:
        try:
            from core.ai_client import AIClient
        except ImportError:
            from src.core.ai_client import AIClient  # type: ignore[no-redef]

        with tempfile.TemporaryDirectory() as project_dir:
            with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(project_dir) / "settings.json")):
                app = MaxTerminalApp()
                app.set_workspace(project_dir)
                client = AIClient(api_key="mock", api_mode="responses")
                responses = iter([
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{
                            "id": "call_write",
                            "type": "function",
                            "function": {
                                "name": "write_file",
                                "arguments": json.dumps({"path": "app.py", "content": "print('stable')\n"}),
                            },
                        }],
                    },
                    {"role": "assistant", "content": "Implemented and verified app.py."},
                ])
                client._call_response = lambda messages, **kwargs: next(responses)  # type: ignore[method-assign]

                with patch.object(app, "_ensure_credentials", return_value=True):
                    with patch.object(app, "_create_client", return_value=client):
                        app.run_prompt_single("Create app.py")

                self.assertEqual(
                    (Path(project_dir) / "app.py").read_text(encoding="utf-8"),
                    "print('stable')\n",
                )


if __name__ == "__main__":
    unittest.main()
