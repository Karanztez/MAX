"""
test_multimedia.py — Unit tests for AI Image and Video generation tools in MAX.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.mcp_manager import MCPManager, _builtin_generate_image, _builtin_generate_video
    from core.skill_manager import SkillManager
except ImportError:
    from src.core.mcp_manager import MCPManager, _builtin_generate_image, _builtin_generate_video  # type: ignore[no-redef]
    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]


class TestMultimediaTools(unittest.TestCase):

    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.cfg_file = Path(self.tmpdir.name) / "mcp_servers.json"
        self.mcp = MCPManager(config_path=self.cfg_file)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_multimedia_tools_registered(self):
        """Verify generate_image and generate_video tools are registered in MCPManager."""
        all_tools = self.mcp.get_all_tools()
        tool_names = [t.name for t in all_tools]
        self.assertIn("generate_image", tool_names)
        self.assertIn("generate_video", tool_names)

    def test_multimedia_skill_discovered(self):
        """Verify SkillManager discovers the new multimedia-generator skill."""
        sm = SkillManager()
        self.assertIn("multimedia-generator", sm.skills)
        skill = sm.skills["multimedia-generator"]
        self.assertEqual(skill.name, "Multimedia Generator")

    @patch("urllib.request.urlopen")
    def test_builtin_generate_image_success(self, mock_urlopen):
        """Verify _builtin_generate_image writes downloaded image bytes to target path."""
        fake_png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 600
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_png_data
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        out_file = Path(self.tmpdir.name) / "test_art.png"
        result = _builtin_generate_image(
            prompt="a glowing neon wolf in cyberpunk city",
            output_path=str(out_file),
            width=512,
            height=512,
            model="flux",
        )

        self.assertIn("สร้างรูปภาพสำเร็จเรียบร้อยแล้ว", result)
        self.assertTrue(out_file.exists())
        self.assertEqual(out_file.read_bytes(), fake_png_data)

    def test_builtin_generate_image_empty_prompt(self):
        """Verify _builtin_generate_image returns error on empty prompt."""
        result = _builtin_generate_image(prompt="")
        self.assertTrue(result.startswith("Error"))

    @patch("urllib.request.urlopen")
    def test_builtin_generate_video_success(self, mock_urlopen):
        """Verify _builtin_generate_video writes downloaded video bytes to target path."""
        fake_mp4_data = b"ftypmp42" + b"\x00" * 2000
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_mp4_data
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        out_file = Path(self.tmpdir.name) / "test_video.mp4"
        result = _builtin_generate_video(
            prompt="drone flying over neon cityscape",
            output_path=str(out_file),
            duration_seconds=4,
            aspect_ratio="16:9",
        )

        self.assertIn("สร้างวิดีโอสำเร็จเรียบร้อยแล้ว", result)
        self.assertTrue(out_file.exists())
        self.assertEqual(out_file.read_bytes(), fake_mp4_data)

    def test_builtin_generate_video_empty_prompt(self):
        """Verify _builtin_generate_video returns error on empty prompt."""
        result = _builtin_generate_video(prompt="")
        self.assertTrue(result.startswith("Error"))


if __name__ == "__main__":
    unittest.main()
