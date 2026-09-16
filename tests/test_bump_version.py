"""
tests/test_bump_version.py — Unit tests for bump_version script logic.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.bump_version import (
    bump_semver,
    get_current_version,
    extract_release_notes,
)


class TestBumpVersion(unittest.TestCase):
    def test_bump_semver_patch(self) -> None:
        self.assertEqual(bump_semver("1.0.1", "patch"), "1.0.2")
        self.assertEqual(bump_semver("v1.0.9", "patch"), "1.0.10")
        self.assertEqual(bump_semver("2.1.0", "patch"), "2.1.1")

    def test_bump_semver_minor(self) -> None:
        self.assertEqual(bump_semver("1.0.1", "minor"), "1.1.0")
        self.assertEqual(bump_semver("v1.5.9", "minor"), "1.6.0")

    def test_bump_semver_major(self) -> None:
        self.assertEqual(bump_semver("1.0.1", "major"), "2.0.0")
        self.assertEqual(bump_semver("v2.3.4", "major"), "3.0.0")

    def test_get_current_version(self) -> None:
        ver = get_current_version()
        self.assertTrue(len(ver.split(".")) >= 2)

    def test_extract_release_notes_existing(self) -> None:
        notes = extract_release_notes("v1.0.1")
        self.assertIn("Cross-Platform Support", notes)

    def test_extract_release_notes_fallback(self) -> None:
        notes = extract_release_notes("v99.99.99")
        self.assertTrue(len(notes) > 0)


if __name__ == "__main__":
    unittest.main()
