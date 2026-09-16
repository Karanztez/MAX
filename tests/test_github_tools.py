"""
test_github_tools.py — Unit tests for GitHub tools and skill in MAX.
"""

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.mcp_manager import (
        MCPManager,
        _builtin_github_search_repos,
        _builtin_github_get_repo,
        _builtin_github_read_file,
        _builtin_github_list_issues,
        _builtin_github_clone_repo,
    )
    from core.skill_manager import SkillManager
except ImportError:
    from src.core.mcp_manager import (  # type: ignore[no-redef]
        MCPManager,
        _builtin_github_search_repos,
        _builtin_github_get_repo,
        _builtin_github_read_file,
        _builtin_github_list_issues,
        _builtin_github_clone_repo,
    )
    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]


class TestGitHubTools(unittest.TestCase):

    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.cfg_file = Path(self.tmpdir.name) / "mcp_servers.json"
        self.mcp = MCPManager(config_path=self.cfg_file)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_github_tools_registered(self):
        """Verify all 5 GitHub tools are registered in MCPManager (31 tools total)."""
        tools = self.mcp.get_all_tools()
        tool_names = {t.name for t in tools}
        expected = {
            "github_search_repos",
            "github_get_repo",
            "github_read_file",
            "github_list_issues",
            "github_clone_repo",
        }
        for exp in expected:
            self.assertIn(exp, tool_names)

    def test_github_specialist_skill_discovered(self):
        """Verify SkillManager discovers the github-specialist skill."""
        sm = SkillManager()
        self.assertIn("github-specialist", sm.skills)
        skill = sm.skills["github-specialist"]
        self.assertEqual(skill.name, "GitHub Specialist")

    @patch("urllib.request.urlopen")
    def test_github_search_repos(self, mock_urlopen):
        """Verify search repos parses GitHub search API JSON response."""
        fake_data = {
            "total_count": 1,
            "items": [
                {
                    "full_name": "Karanztez/MAX",
                    "description": "MAX AI Agent",
                    "stargazers_count": 42,
                    "forks_count": 5,
                    "language": "Python",
                    "html_url": "https://github.com/Karanztez/MAX",
                }
            ],
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = _builtin_github_search_repos("MAX AI", count=1)
        self.assertIn("Karanztez/MAX", result)
        self.assertIn("★ 42", result)

    @patch("urllib.request.urlopen")
    def test_github_get_repo(self, mock_urlopen):
        """Verify get repo details parses GitHub repo API response."""
        fake_data = {
            "full_name": "Karanztez/MAX",
            "description": "MAX AI Agent Project",
            "stargazers_count": 100,
            "forks_count": 10,
            "subscribers_count": 5,
            "open_issues_count": 2,
            "language": "Python",
            "license": {"name": "MIT License"},
            "default_branch": "main",
            "created_at": "2026-09-01T00:00:00Z",
            "updated_at": "2026-09-16T00:00:00Z",
            "html_url": "https://github.com/Karanztez/MAX",
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = _builtin_github_get_repo("Karanztez/MAX")
        self.assertIn("Repository: Karanztez/MAX", result)
        self.assertIn("License: MIT License", result)

    @patch("urllib.request.urlopen")
    def test_github_read_file(self, mock_urlopen):
        """Verify reading raw file from GitHub."""
        fake_code = b"# Hello from MAX\nprint('running')"
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_code
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = _builtin_github_read_file("Karanztez/MAX", "src/main.py")
        self.assertIn("File: Karanztez/MAX/src/main.py", result)
        self.assertIn("print('running')", result)

    @patch("urllib.request.urlopen")
    def test_github_list_issues(self, mock_urlopen):
        """Verify listing issues and PRs."""
        fake_issues = [
            {
                "number": 1,
                "title": "Add GitHub Tools",
                "user": {"login": "developer"},
                "comments": 3,
                "created_at": "2026-09-16T00:00:00Z",
                "html_url": "https://github.com/Karanztez/MAX/issues/1",
                "labels": [{"name": "enhancement"}],
            }
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_issues).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = _builtin_github_list_issues("Karanztez/MAX", state="open")
        self.assertIn("Issue #1: Add GitHub Tools", result)
        self.assertIn("@developer", result)


if __name__ == "__main__":
    unittest.main()
