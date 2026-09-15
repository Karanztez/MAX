"""
tests/test_updater.py — Unit tests for updater logic and skip version persistence.
"""

import tempfile
import unittest
from pathlib import Path

from src.core.updater import (
    parse_version_tuple,
    is_newer_version,
    UpdateInfo,
    APP_VERSION,
)
from src.core.settings_store import SettingsStore


class TestUpdater(unittest.TestCase):
    def test_parse_version_tuple(self) -> None:
        self.assertEqual(parse_version_tuple("1.0.0"), (1, 0, 0))
        self.assertEqual(parse_version_tuple("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version_tuple("V2.0"), (2, 0))
        self.assertEqual(parse_version_tuple("v1.0.4-beta.1"), (1, 0, 4))
        self.assertEqual(parse_version_tuple("invalid"), (0,))

    def test_is_newer_version(self) -> None:
        self.assertTrue(is_newer_version("1.0.1", "1.0.0"))
        self.assertTrue(is_newer_version("v2.0.0", "1.9.9"))
        self.assertTrue(is_newer_version("1.1.0", "1.0.9"))
        self.assertFalse(is_newer_version("1.0.0", "1.0.0"))
        self.assertFalse(is_newer_version("v1.0.0", "1.0.0"))
        self.assertFalse(is_newer_version("0.9.9", "1.0.0"))

    def test_skip_version_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SettingsStore(Path(tmpdir) / "test_settings.json")
            self.assertEqual(store.load_skipped_version(), "")

            store.save_skipped_version("v1.2.0")
            self.assertEqual(store.load_skipped_version(), "v1.2.0")

            store.save_skipped_version("v2.0.0")
            self.assertEqual(store.load_skipped_version(), "v2.0.0")


if __name__ == "__main__":
    unittest.main()
