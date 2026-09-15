"""
tests/test_cli.py — Unit tests for Terminal & Mobile CLI interface.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cli import MaxTerminalApp


class TestCLI(unittest.TestCase):

    def test_cli_initialization(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app = MaxTerminalApp()
            self.assertIsNotNone(app.active_profile)
            self.assertIsNotNone(app.mcp_manager)

            # Test command handling
            self.assertTrue(app.handle_command("/clear"))
            self.assertTrue(app.handle_command("/help"))
            self.assertTrue(app.handle_command("/profiles"))
            self.assertTrue(app.handle_command("/models"))
            self.assertTrue(app.handle_command("/tools"))


if __name__ == "__main__":
    unittest.main()
