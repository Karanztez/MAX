"""Unit tests for Code Diff Editing Engine (Gemini/Antigravity style) and Modular MCP."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from core.mcp import (
        MCPManager,
        render_diff,
        replace_content_chunk,
    )
except (ImportError, ModuleNotFoundError):
    from src.core.mcp import (  # type: ignore[no-redef]
        MCPManager,
        render_diff,
        replace_content_chunk,
    )


class TestDiffEditing(unittest.TestCase):
    def test_render_diff_basic(self) -> None:
        old_text = "def hello():\n    print('hello')\n"
        new_text = "def hello():\n    print('hello world')\n"
        diff = render_diff(old_text, new_text, filename="hello.py", use_color=False)
        self.assertIn("diff_block_start", diff)
        self.assertIn("-    print('hello')", diff)
        self.assertIn("+    print('hello world')", diff)
        self.assertIn("diff_block_end", diff)

    def test_replace_content_chunk_success(self) -> None:
        original = """def calculate(a, b):
    return a + b

def main():
    print(calculate(1, 2))
"""
        target = "    return a + b"
        replacement = "    # Add numbers\n    return a + b"

        ok, updated, diff = replace_content_chunk(original, target, replacement)
        self.assertTrue(ok)
        self.assertIn("# Add numbers", updated)
        self.assertIn("+    # Add numbers", diff)

    def test_replace_content_chunk_mismatch(self) -> None:
        original = "print('foo')\n"
        target = "print('bar')"
        replacement = "print('baz')"

        ok, msg, diff = replace_content_chunk(original, target, replacement)
        self.assertFalse(ok)
        self.assertIn("does not match", msg)

    def test_replace_file_content_tool(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fpath = Path(tmp_dir) / "app.py"
            fpath.write_text("name = 'old_name'\nversion = 1.0\n", encoding="utf-8")

            mgr = MCPManager()
            res = mgr.execute_tool("replace_file_content", {
                "path": str(fpath),
                "target_content": "name = 'old_name'",
                "replacement_content": "name = 'new_name'",
            })
            self.assertIn("สำเร็จ", res)
            self.assertIn("+name = 'new_name'", res)

            # Check file on disk
            content = fpath.read_text(encoding="utf-8")
            self.assertEqual(content, "name = 'new_name'\nversion = 1.0\n")


if __name__ == "__main__":
    unittest.main()
