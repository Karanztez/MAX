"""Live diagnostic for the configured MaxPlus Claude pool (never prints the key)."""

import time
import json
import sys
from pathlib import Path
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.ai_client import AIClient
from src.core.provider_profiles import default_profiles
from src.core.settings_store import SettingsStore


def main() -> None:
    profiles, _selected = SettingsStore().load_provider_settings(default_profiles())
    profile = next(item for item in profiles if item["id"] == "maxplus-claude")
    if not profile["api_key"]:
        raise RuntimeError("MaxPlus Claude API key is not configured")

    probe = AIClient(api_key=profile["api_key"], base_url=profile["base_url"],
                     model=profile["model"], timeout=30)
    models = probe.list_models()
    print(f"GET /models: PASS ({len(models)} models)")
    if "--anthropic-only" not in sys.argv:
        for model in models:
            started = time.monotonic()
            try:
                answer = AIClient(api_key=profile["api_key"], base_url=profile["base_url"],
                                  model=model, timeout=45).ask(
                                      "Reply with exactly: OK", temperature=0, max_tokens=16)
                elapsed = time.monotonic() - started
                print(f"{model}: PASS ({elapsed:.2f}s) {answer[:80]!r}")
            except Exception as ex:
                elapsed = time.monotonic() - started
                print(f"{model}: FAIL ({elapsed:.2f}s) {str(ex)[:240]}")

    anthropic_url = f"{profile['base_url']}/messages"
    body = json.dumps({
        "model": profile["model"],
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
    }).encode("utf-8")
    request = urllib.request.Request(
        anthropic_url, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": profile["api_key"],
            "anthropic-version": "2023-06-01",
        },
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = "".join(item.get("text", "") for item in data.get("content", [])
                       if isinstance(item, dict))
        print(f"Anthropic /messages: PASS ({time.monotonic() - started:.2f}s) {text[:80]!r}")
    except urllib.error.HTTPError as ex:
        detail = ex.read().decode("utf-8", errors="replace")
        print(f"Anthropic /messages: FAIL ({time.monotonic() - started:.2f}s) HTTP {ex.code}: {detail[:220]}")
    except Exception as ex:
        print(f"Anthropic /messages: FAIL ({time.monotonic() - started:.2f}s) {str(ex)[:220]}")


if __name__ == "__main__":
    main()
