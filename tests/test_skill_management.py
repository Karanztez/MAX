"""Unit tests for autonomous skill installation, deletion, and listing."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from core.skill_manager import SkillManager
    from core.mcp_manager import MCPManager
except ImportError:
    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]
    from src.core.mcp_manager import MCPManager  # type: ignore[no-redef]


class TestSkillManagement(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.mgr = SkillManager(root=self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_install_skill_with_frontmatter(self) -> None:
        content = """---
name: Flutter Pro
description: Expert flutter developer
default: false
---

Always write clean Dart code with strong typing."""
        ok, msg = self.mgr.install_skill("flutter-pro", content)
        self.assertTrue(ok)
        self.assertIn("flutter-pro", self.mgr.skills)
        self.assertEqual(self.mgr.skills["flutter-pro"].name, "Flutter Pro")
        self.assertEqual(self.mgr.skills["flutter-pro"].description, "Expert flutter developer")
        self.assertIn("Always write clean Dart code", self.mgr.skills["flutter-pro"].instructions)

    def test_install_skill_autowrap(self) -> None:
        raw = "You are a Docker deployment expert. Always generate secure Dockerfiles."
        ok, msg = self.mgr.install_skill("docker-expert", raw)
        self.assertTrue(ok)
        self.assertIn("docker-expert", self.mgr.skills)
        self.assertEqual(self.mgr.skills["docker-expert"].name, "Docker Expert")
        self.assertIn("Always generate secure Dockerfiles", self.mgr.skills["docker-expert"].instructions)

    def test_delete_skill(self) -> None:
        self.mgr.install_skill("temp-skill", "Temporary instructions")
        self.assertIn("temp-skill", self.mgr.skills)

        ok, msg = self.mgr.delete_skill("temp-skill")
        self.assertTrue(ok)
        self.assertNotIn("temp-skill", self.mgr.skills)
        self.assertFalse((self.root / "temp-skill").exists())

    def test_list_skills_info(self) -> None:
        self.mgr.install_skill("skill-a", "Instructions A")
        self.mgr.install_skill("skill-b", "Instructions B")

        info = self.mgr.list_skills_info()
        self.assertEqual(len(info), 2)
        ids = [s["id"] for s in info]
        self.assertIn("skill-a", ids)
        self.assertIn("skill-b", ids)

    @patch("urllib.request.urlopen")
    def test_install_from_github_mock(self, mock_urlopen: MagicMock) -> None:
        fake_content = """---
name: React Specialist
description: React 19 and Next.js specialist
default: false
---

Always use React Server Components when applicable."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_content.encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        ok, msg = self.mgr.install_from_github("facebook/react-skill", skill_id="react-specialist")
        self.assertTrue(ok)
        self.assertIn("react-specialist", self.mgr.skills)
        self.assertEqual(self.mgr.skills["react-specialist"].name, "React Specialist")

    def test_mcp_tools_skill_integration(self) -> None:
        mcp = MCPManager()
        tools = mcp.get_all_tools()
        tool_names = [t.name for t in tools]
        self.assertIn("install_skill", tool_names)
        self.assertIn("remove_skill", tool_names)
        self.assertIn("list_skills", tool_names)

        # Test list_skills tool
        res_list = mcp.execute_tool("list_skills", {})
        self.assertIsInstance(res_list, str)
        self.assertTrue(len(res_list) > 0)


if __name__ == "__main__":
    unittest.main()
