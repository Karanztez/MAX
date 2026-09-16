"""
tests/test_ide_inspector.py — Unit tests for IDEInspector.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.ide_inspector import IDEInspector, IDEDiagnostic
except ImportError:
    from src.core.ide_inspector import IDEInspector, IDEDiagnostic  # type: ignore[no-redef]


class TestIDEInspector(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.inspector = IDEInspector(workspace_path=self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_inspect_clean_python_file(self):
        """Test that a syntactically correct Python file produces no syntax errors."""
        good_file = self.workspace / "clean.py"
        good_file.write_text("def hello(name: str) -> str:\n    return f'Hello, {name}'\n", encoding="utf-8")

        diags = self.inspector.inspect_file(good_file)
        errors = [d for d in diags if d.severity.lower() == "error"]
        self.assertEqual(len(errors), 0, f"Expected 0 errors for clean file, got: {errors}")

    def test_inspect_syntax_error(self):
        """Test that a syntax error is correctly flagged with line, col, and message."""
        bad_file = self.workspace / "broken.py"
        bad_file.write_text("def broken_syntax(:\n    pass\n", encoding="utf-8")

        diags = self.inspector.inspect_file(bad_file)
        syntax_errors = [d for d in diags if d.code == "syntax-error"]
        self.assertGreaterEqual(len(syntax_errors), 1)
        self.assertEqual(syntax_errors[0].line, 1)
        self.assertIn("SyntaxCheck", syntax_errors[0].source)

    def test_review_code_draft_fixes_and_introduces_issues(self):
        """Test reviewing a proposed code draft against original file."""
        target_file = self.workspace / "target.py"
        target_file.write_text("def faulty(:\n    pass\n", encoding="utf-8")

        good_replacement = "def faulty():\n    return 42\n"
        review = self.inspector.review_code_draft(target_file, good_replacement)

        self.assertTrue(review["is_valid"])
        self.assertGreaterEqual(len(review["fixed_issues"]), 1)
        self.assertEqual(len(review["new_issues"]), 0)

        # Now test proposing broken code
        broken_replacement = "def faulty(\n"
        review_broken = self.inspector.review_code_draft(target_file, broken_replacement)
        self.assertFalse(review_broken["is_valid"])
        self.assertIn("❌", review_broken["summary"])

    def test_format_report(self):
        """Test format_report generates Markdown table."""
        diag = IDEDiagnostic(
            file_path=str(self.workspace / "test.py"),
            line=10,
            col=5,
            severity="error",
            code="syntax-error",
            message="invalid syntax",
            source="SyntaxCheck",
        )
        report = self.inspector.format_report([diag])
        self.assertIn("### 🔍 รายงานการตรวจทาน", report)
        self.assertIn("🔴 Error", report)
        self.assertIn("invalid syntax", report)


if __name__ == "__main__":
    unittest.main()
