import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.settings_store import SettingsStore
from src.core.provider_profiles import default_profiles


def main() -> None:
    with TemporaryDirectory() as folder:
        path = Path(folder) / "settings.json"
        store = SettingsStore(path)
        store.save_api_key("test-secret-key", remember=True)
        raw = path.read_text(encoding="utf-8")
        assert "test-secret-key" not in raw
        assert store.load_api_key() == "test-secret-key"
        profiles = default_profiles()
        profiles[0]["api_key"] = "chinese-secret"
        profiles[1]["api_key"] = "grok-secret"
        profiles[2]["api_key"] = "claude-cursor-secret"
        target_id = profiles[2]["id"]
        store.save_provider_settings(profiles, target_id, remember=True)
        raw = path.read_text(encoding="utf-8")
        for secret in ("chinese-secret", "grok-secret", "claude-cursor-secret"):
            assert secret not in raw
        loaded, selected = store.load_provider_settings(default_profiles())
        assert selected == target_id
        assert loaded[0]["api_key"] == "chinese-secret"
        assert loaded[1]["api_key"] == "grok-secret"
        assert loaded[2]["api_key"] == "claude-cursor-secret"
        store.save_provider_settings(loaded, selected, remember=False)
        assert not path.exists()
    print("encrypted settings test passed")


if __name__ == "__main__":
    main()
