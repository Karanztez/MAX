"""
tests/test_bump_version.py — Unit tests for bump_version script logic.
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load scripts/bump_version.py dynamically to be robust in all test runner environments
_script_file = _PROJECT_ROOT / "scripts" / "bump_version.py"
_spec = importlib.util.spec_from_file_location("scripts.bump_version", _script_file)
if _spec and _spec.loader:
    _bump_mod = importlib.util.module_from_spec(_spec)
    sys.modules["scripts.bump_version"] = _bump_mod
    _spec.loader.exec_module(_bump_mod)
else:
    raise ImportError(f"Cannot load {_script_file}")

bump_semver = _bump_mod.bump_semver
get_current_version = _bump_mod.get_current_version
extract_release_notes = _bump_mod.extract_release_notes
update_changelog = _bump_mod.update_changelog
apply_version = _bump_mod.apply_version


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
        notes = extract_release_notes("v1.0.6")
        self.assertIn("MAX for AI", notes)

    def test_extract_release_notes_fallback(self) -> None:
        notes = extract_release_notes("v99.99.99")
        self.assertTrue(len(notes) > 0)

    def test_update_changelog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n- initial\n", encoding="utf-8")
            original_root = getattr(_bump_mod, "ROOT_DIR")
            try:
                setattr(_bump_mod, "ROOT_DIR", root)
                update_changelog("2.0.0")
            finally:
                setattr(_bump_mod, "ROOT_DIR", original_root)
            self.assertIn("[v2.0.0]", (root / "CHANGELOG.md").read_text(encoding="utf-8"))

    def test_apply_version_updates_python_and_javascript_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "src/__init__.py": '__version__ = "1.0.2"\n',
                "src/max_ai/__init__.py": '__version__ = "1.0.2"\n',
                "src/core/updater.py": 'APP_VERSION = "1.0.2"\n',
                "src/core/mcp_manager.py": '"clientInfo": {"name": "MaxPlusAI", "version": "1.0.2"}\n',
                "setup.py": 'version="1.0.2"\n',
                "pyproject.toml": 'version = "1.0.2"\n',
                "js/src/index.ts": 'export const VERSION = "1.0.2";\n',
                "package.json": json.dumps({"name": "@karanztez/max-ai", "version": "1.0.2"}),
                "package-lock.json": json.dumps({
                    "name": "@karanztez/max-ai",
                    "version": "1.0.2",
                    "packages": {"": {"version": "1.0.2"}},
                }),
            }
            for relative_path, content in files.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            original_root = getattr(_bump_mod, "ROOT_DIR")
            try:
                setattr(_bump_mod, "ROOT_DIR", root)
                apply_version("v2.3.4")
            finally:
                setattr(_bump_mod, "ROOT_DIR", original_root)

            self.assertIn('__version__ = "2.3.4"', (root / "src/max_ai/__init__.py").read_text())
            self.assertIn('VERSION = "2.3.4"', (root / "js/src/index.ts").read_text())
            self.assertEqual(json.loads((root / "package.json").read_text())["version"], "2.3.4")
            lock = json.loads((root / "package-lock.json").read_text())
            self.assertEqual(lock["version"], "2.3.4")
            self.assertEqual(lock["packages"][""]["version"], "2.3.4")


if __name__ == "__main__":
    unittest.main()
