"""
tests/test_background_runner.py — Unit tests for BackgroundTestRunner.
"""

import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.background_runner import BackgroundTestRunner
except ImportError:
    from src.core.background_runner import BackgroundTestRunner  # type: ignore[no-redef]


class TestBackgroundTestRunner(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.runner = BackgroundTestRunner(workspace_path=self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_successful_script(self):
        """Test running a python one-shot test script that passes."""
        script = self.workspace / "mini_test.py"
        script.write_text("import unittest\nclass Demo(unittest.TestCase):\n    def test_one(self):\n        self.assertEqual(1+1, 2)\nif __name__ == '__main__':\n    unittest.main()\n", encoding="utf-8")

        done_event = time.time()
        task_id = self.runner.start_test_run(
            target_path=script,
            cwd=self.workspace,
            timeout_sec=10,
        )
        self.assertTrue(task_id.startswith("test_"))

        # Wait for finish (should take < 2 seconds)
        for _ in range(50):
            res = self.runner.get_status(task_id)
            if res and res.status in ("PASSED", "FAILED", "ERROR"):
                break
            time.sleep(0.1)

        final_res = self.runner.get_status(task_id)
        self.assertIsNotNone(final_res)
        self.assertEqual(final_res.status, "PASSED")
        self.assertEqual(final_res.exit_code, 0)
        self.assertIn("Ran 1 test", final_res.stdout + final_res.stderr)

    def test_run_failing_script(self):
        """Test running a failing test script returns FAILED status."""
        script = self.workspace / "fail_test.py"
        script.write_text("import unittest\nclass DemoFail(unittest.TestCase):\n    def test_bad(self):\n        self.assertEqual(1, 2)\nif __name__ == '__main__':\n    unittest.main()\n", encoding="utf-8")

        task_id = self.runner.start_test_run(
            target_path=script,
            cwd=self.workspace,
            timeout_sec=10,
        )

        for _ in range(50):
            res = self.runner.get_status(task_id)
            if res and res.status in ("PASSED", "FAILED", "ERROR"):
                break
            time.sleep(0.1)

        final_res = self.runner.get_status(task_id)
        self.assertIsNotNone(final_res)
        self.assertEqual(final_res.status, "FAILED")
        self.assertNotEqual(final_res.exit_code, 0)

    def test_cancel_run(self):
        """Test cancelling a long-running background test."""
        script = self.workspace / "sleep_test.py"
        script.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")

        task_id = self.runner.start_test_run(
            custom_command=[sys.executable, str(script)],
            cwd=self.workspace,
            timeout_sec=30,
        )

        # Allow process to start
        time.sleep(0.2)
        cancelled = self.runner.cancel_run(task_id)
        self.assertTrue(cancelled)

        final_res = self.runner.get_status(task_id)
        self.assertIsNotNone(final_res)
        self.assertEqual(final_res.status, "CANCELLED")


if __name__ == "__main__":
    unittest.main()
