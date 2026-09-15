"""Live diagnostic for MaxPlus Gemini Full (never prints or persists the key)."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.ai_client import AIClient
from src.core.provider_profiles import default_profiles
from src.core.settings_store import SettingsStore


def main() -> None:
    profiles, _selected = SettingsStore().load_provider_settings(default_profiles())
    profile = next(item for item in profiles if item["id"] == "maxplus-gemini")
    api_key = os.environ.get("MAXPLUS_TEST_API_KEY", "").strip() or profile["api_key"]
    if not api_key:
        raise RuntimeError("Gemini Full API key is not configured")

    probe = AIClient(api_key=api_key, base_url=profile["base_url"],
                     model=profile["model"], timeout=30)
    models = probe.list_models()
    print(f"GET /models: PASS ({len(models)} models)")
    for model in models:
        started = time.monotonic()
        try:
            answer = AIClient(api_key=api_key, base_url=profile["base_url"],
                              model=model, timeout=45).ask(
                                  "Reply with exactly: OK", temperature=0, max_tokens=16)
            elapsed = time.monotonic() - started
            print(f"{model}: PASS ({elapsed:.2f}s) {answer[:80]!r}")
        except Exception as ex:
            elapsed = time.monotonic() - started
            print(f"{model}: FAIL ({elapsed:.2f}s) {str(ex)[:240]}")


if __name__ == "__main__":
    main()
