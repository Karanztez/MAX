"""
tests/test_teamai_integration.py — Unit tests for Tencent TeamAI CLI integration in MAX.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import core.mcp.builtins.teamai_tools as t_mod
    from core.mcp.builtins.teamai_tools import (
        get_teamai_binary,
        run_teamai,
        _builtin_teamai_command,
        _builtin_teamai_sync,
        get_teamai_tools,
    )
    from core.mcp_manager import MCPManager
    from core.skill_manager import SkillManager
    from cli import MaxTerminalApp
except (ImportError, ModuleNotFoundError):
    import src.core.mcp.builtins.teamai_tools as t_mod  # type: ignore[no-redef]
    from src.core.mcp.builtins.teamai_tools import (  # type: ignore[no-redef]
        get_teamai_binary,
        run_teamai,
        _builtin_teamai_command,
        _builtin_teamai_sync,
        get_teamai_tools,
    )
    from src.core.mcp_manager import MCPManager  # type: ignore[no-redef]
    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]
    from src.cli import MaxTerminalApp  # type: ignore[no-redef]


class TestTeamAIIntegration(unittest.TestCase):
    def test_get_teamai_binary_direct(self):
        with patch("shutil.which", side_effect=lambda x: "/usr/local/bin/teamai" if x == "teamai" else None):
            prefix, name = get_teamai_binary()
            self.assertEqual(prefix, ["/usr/local/bin/teamai"])
            self.assertEqual(name, "teamai")

    def test_get_teamai_binary_npx_fallback(self):
        with patch("shutil.which", side_effect=lambda x: "/usr/bin/npx" if x == "npx" else None):
            prefix, name = get_teamai_binary()
            self.assertEqual(prefix, ["/usr/bin/npx", "-y", "teamai-cli"])
            self.assertEqual(name, "npx teamai-cli")

    def test_get_teamai_binary_none(self):
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=False):
                prefix, name = get_teamai_binary()
                self.assertEqual(prefix, [])
                self.assertEqual(name, "")

    def test_run_teamai_missing_binary(self):
        with patch.object(t_mod, "get_teamai_binary", return_value=([], "")):
            code, out = run_teamai(["status"])
            self.assertEqual(code, -1)
            self.assertIn("ไม่พบคำสั่ง 'teamai' หรือ 'npx'", out)

    @patch("subprocess.run")
    def test_run_teamai_success(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "TeamAI version 1.2.0 - Synced with git@github.com:my-team/ai-skills.git"
        mock_run.return_value = mock_proc

        with patch.object(t_mod, "get_teamai_binary", return_value=(["teamai"], "teamai")):
            code, out = run_teamai(["status"])
            self.assertEqual(code, 0)
            self.assertIn("TeamAI version 1.2.0", out)

    @patch("subprocess.run")
    def test_run_teamai_pull_triggers_skill_refresh(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Pulled 3 new skills: code-review, security-audit, api-design"
        mock_run.return_value = mock_proc

        with patch.object(t_mod, "get_teamai_binary", return_value=(["teamai"], "teamai")):
            with patch.object(SkillManager, "refresh") as mock_refresh:
                code, out = run_teamai(["pull"])
                self.assertEqual(code, 0)
                mock_refresh.assert_called()

    def test_teamai_tools_registered_in_mcp_manager(self):
        with TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "mcp_servers.json"
            mgr = MCPManager(config_path=cfg_path)
            tools = mgr.get_all_tools()
            tool_names = [t.name for t in tools]
            self.assertIn("teamai_command", tool_names)
            self.assertIn("teamai_sync", tool_names)

    @patch("subprocess.run")
    def test_cli_handle_teamai_command(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "TeamAI connected to repository"
        mock_run.return_value = mock_proc

        with TemporaryDirectory() as tmpdir:
            try:
                from core.settings_store import SettingsStore
            except (ImportError, ModuleNotFoundError):
                from src.core.settings_store import SettingsStore  # type: ignore[no-redef]

            with patch.object(SettingsStore, "__init__", lambda self, p=None: setattr(self, "path", Path(tmpdir) / "test_s.json")):
                app = MaxTerminalApp()
                res = app.handle_command("/teamai status")
                self.assertTrue(res)

                res_help = app.handle_command("/teamai help")
                self.assertTrue(res_help)


if __name__ == "__main__":
    unittest.main()
