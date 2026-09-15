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
        profiles[0]["api_key"] = "gemini-secret"
        profiles[1]["api_key"] = "claude-secret"
        profiles[2]["api_key"] = "openai-secret"
        store.save_provider_settings(profiles, "maxplus-claude", remember=True)
        raw = path.read_text(encoding="utf-8")
        for secret in ("gemini-secret", "claude-secret", "openai-secret"):
            assert secret not in raw
        loaded, selected = store.load_provider_settings(default_profiles())
        assert selected == "maxplus-claude"
        assert [p["api_key"] for p in loaded] == [
            "gemini-secret", "claude-secret", "openai-secret"
        ]
        store.save_provider_settings(loaded, selected, remember=False)
        assert not path.exists()
    print("encrypted settings test passed")


if __name__ == "__main__":
    main()
