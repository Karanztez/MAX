import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.ai_client import AIClient
from src.core.provider_profiles import CLAUDE_MODELS, default_profiles, normalize_profiles


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def main() -> None:
    profiles = default_profiles()
    native_p = next(p for p in profiles if p["id"] == "maxplus-claude-native")
    cursor_p = next(p for p in profiles if p["id"] == "maxplus-claude-cursor")
    anti_p = next(p for p in profiles if p["id"] == "maxplus-claude-antigravity")

    assert native_p["base_url"].endswith("/claude-native/v1")
    assert "claude-fable-5-1" in native_p["models"]
    assert cursor_p["base_url"].endswith("/claude-cursor-full/v1")
    assert "claude-fable-5-1" in cursor_p["models"]
    assert anti_p["base_url"].endswith("/claude-antigravity-full/v1")
    assert "claude-opus-4-6-thinking" in anti_p["models"]

    duplicate = normalize_profiles([profiles[0], {**profiles[0], "id": "copy"}])
    assert duplicate[0]["name"] != duplicate[1]["name"]

    captured = {}

    def fake_urlopen(request, timeout=0):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response({"output": [{"content": [{"type": "output_text", "text": "ok"}]}]})

    client = AIClient(api_key="secret", base_url="https://api.openai.com/v1",
                      model="gpt-6-astra", api_mode="responses")
    with patch("urllib.request.urlopen", fake_urlopen):
        answer = client.ask([
            {"type": "text", "text": "describe"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
        ])
    assert answer == "ok"
    assert captured["url"].endswith("/responses")
    assert captured["payload"]["input"][0]["content"][1]["type"] == "input_image"
    assert "temperature" not in captured["payload"]

    def fake_chat_urlopen(request, timeout=0):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response({"choices": [{"message": {"content": "claude-ok"}}]})

    claude = AIClient(api_key="secret", base_url=cursor_p["base_url"],
                      model="claude-sonnet-4-6", api_mode="chat_completions")
    with patch("urllib.request.urlopen", fake_chat_urlopen):
        assert claude.ask("hello") == "claude-ok"
    assert captured["url"].endswith("/claude-cursor-full/v1/chat/completions")
    assert captured["payload"]["model"] == "claude-sonnet-4-6"
    print("provider profile tests passed")


if __name__ == "__main__":
    main()
