"""
tests/test_draft_manager.py — Unit tests for DraftManager & MCP diagnostic tools.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.draft_manager import DraftManager
    from core.mcp.builtins.diagnostic_tools import (
        _builtin_inspect_ide_diagnostics,
        _builtin_create_code_draft,
        _builtin_apply_code_draft,
        _builtin_discard_code_draft,
        _builtin_list_code_drafts,
    )
    from core.mcp.workspace_context import set_workspace_root
except ImportError:
    from src.core.draft_manager import DraftManager  # type: ignore[no-redef]
    from src.core.mcp.builtins.diagnostic_tools import (  # type: ignore[no-redef]
        _builtin_inspect_ide_diagnostics,
        _builtin_create_code_draft,
        _builtin_apply_code_draft,
        _builtin_discard_code_draft,
        _builtin_list_code_drafts,
    )
    from src.core.mcp.workspace_context import set_workspace_root  # type: ignore[no-redef]


class TestDraftManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        set_workspace_root(self.workspace)
        self.mgr = DraftManager(workspace_path=self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_apply_draft(self):
        """Test creating a code draft, verifying diff, and applying it with backup."""
        file_path = self.workspace / "sample.py"
        file_path.write_text("def old_function():\n    return 1\n", encoding="utf-8")

        new_code = "def old_function():\n    return 2\n"
        draft = self.mgr.create_draft(file_path, new_code, metadata={"author": "AI"})

        self.assertEqual(draft.status, "PENDING")
        self.assertIn("+    return 2", draft.diff_preview)
        self.assertIn("-    return 1", draft.diff_preview)
        self.assertFalse(draft.has_syntax_error)

        # Apply
        success, msg = self.mgr.apply_draft(draft.draft_id, create_backup=True)
        self.assertTrue(success)
        self.assertEqual(draft.status, "APPLIED")
        self.assertEqual(file_path.read_text(encoding="utf-8"), new_code)

        # Backup file must exist
        backup = file_path.with_suffix(".py.bak")
        self.assertTrue(backup.exists())
        self.assertIn("return 1", backup.read_text(encoding="utf-8"))

    def test_discard_draft(self):
        """Test discarding a pending draft."""
        file_path = self.workspace / "discard_me.py"
        file_path.write_text("x = 1\n", encoding="utf-8")

        draft = self.mgr.create_draft(file_path, "x = 99\n")
        self.assertTrue(self.mgr.discard_draft(draft.draft_id))
        self.assertEqual(draft.status, "DISCARDED")
        self.assertEqual(file_path.read_text(encoding="utf-8"), "x = 1\n")

    def test_mcp_builtin_tools(self):
        """Test MCP diagnostic and draft built-in wrapper functions."""
        target = self.workspace / "mcp_sample.py"
        target.write_text("def test_ok():\n    return True\n", encoding="utf-8")

        # 1. inspect_ide_diagnostics
        report = _builtin_inspect_ide_diagnostics(str(target))
        self.assertIn("✅", report)

        # 2. create_code_draft
        create_res = _builtin_create_code_draft(str(target), "def test_ok():\n    return 'changed'\n")
        self.assertIn("สร้างแบบร่าง", create_res)

        # 3. list_code_drafts
        list_res = _builtin_list_code_drafts()
        self.assertIn("mcp_sample.py", list_res)


if __name__ == "__main__":
    unittest.main()
