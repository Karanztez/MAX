import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.settings_store import SettingsStore
    from core.provider_profiles import default_profiles
except ImportError:
    from src.core.settings_store import SettingsStore  # type: ignore[no-redef]
    from src.core.provider_profiles import default_profiles  # type: ignore[no-redef]


class TestSettingsStore(unittest.TestCase):
    def test_encrypted_settings_persistence(self) -> None:
        with TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            store = SettingsStore(path)
            store.save_api_key("test-secret-key", remember=True)
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("test-secret-key", raw)
            self.assertEqual(store.load_api_key(), "test-secret-key")

            profiles = default_profiles()
            profiles[0]["api_key"] = "chinese-secret"
            profiles[1]["api_key"] = "grok-secret"
            profiles[2]["api_key"] = "claude-cursor-secret"
            target_id = profiles[2]["id"]

            store.save_provider_settings(profiles, target_id, remember=True)
            raw = path.read_text(encoding="utf-8")
            for secret in ("chinese-secret", "grok-secret", "claude-cursor-secret"):
                self.assertNotIn(secret, raw)

            loaded, selected = store.load_provider_settings(default_profiles())
            self.assertEqual(selected, target_id)
            self.assertEqual(loaded[0]["api_key"], "chinese-secret")
            self.assertEqual(loaded[1]["api_key"], "grok-secret")
            self.assertEqual(loaded[2]["api_key"], "claude-cursor-secret")

            store.save_provider_settings(loaded, selected, remember=False)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
