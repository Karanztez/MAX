import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.ai_client import AIClient
    from core.provider_profiles import CLAUDE_MODELS, default_profiles, normalize_profiles
except ImportError:
    from src.core.ai_client import AIClient  # type: ignore[no-redef]
    from src.core.provider_profiles import CLAUDE_MODELS, default_profiles, normalize_profiles  # type: ignore[no-redef]


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class TestProviderProfiles(unittest.TestCase):
    def test_responses_api_function_tool_payload_and_result(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout=0):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return _Response({
                "output": [{
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_1",
                    "name": "write_file",
                    "arguments": '{"path":"app.py","content":"ok"}',
                }]
            })

        client = AIClient(
            api_key="secret",
            base_url="https://api.openai.com/v1",
            model="gpt-test",
            api_mode="responses",
        )
        tools = [{
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write a project file",
                "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
            },
        }]
        with patch("urllib.request.urlopen", fake_urlopen):
            result = client._call_response([{"role": "user", "content": "edit app.py"}], tools=tools)

        self.assertEqual(captured["payload"]["tools"][0]["name"], "write_file")
        self.assertNotIn("function", captured["payload"]["tools"][0])
        self.assertEqual(result["tool_calls"][0]["id"], "call_1")
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "write_file")

    def test_provider_profiles(self) -> None:
        profiles = default_profiles()
        native_p = next(p for p in profiles if p["id"] == "maxplus-claude-native")
        cursor_p = next(p for p in profiles if p["id"] == "maxplus-claude-cursor")
        anti_p = next(p for p in profiles if p["id"] == "maxplus-claude-antigravity")

        self.assertTrue(native_p["base_url"].endswith("/claude-native/v1"))
        self.assertIn("claude-fable-5-1", native_p["models"])
        self.assertTrue(cursor_p["base_url"].endswith("/claude-cursor-full/v1"))
        self.assertIn("claude-fable-5-1", cursor_p["models"])
        self.assertTrue(anti_p["base_url"].endswith("/claude-antigravity-full/v1"))
        self.assertIn("claude-opus-4-6-thinking", anti_p["models"])

        duplicate = normalize_profiles([profiles[0], {**profiles[0], "id": "copy"}])
        self.assertNotEqual(duplicate[0]["name"], duplicate[1]["name"])

        captured = {}

        def fake_urlopen(request, timeout=0):
            captured["url"] = request.full_url
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return _Response({"output": [{"content": [{"type": "output_text", "text": "ok"}]}]})

        client = AIClient(
            api_key="secret",
            base_url="https://api.openai.com/v1",
            model="gpt-6-astra",
            api_mode="responses",
        )
        with patch("urllib.request.urlopen", fake_urlopen):
            answer = client.ask([
                {"type": "text", "text": "describe"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
            ])
        self.assertEqual(answer, "ok")
        self.assertTrue(captured["url"].endswith("/responses"))
        self.assertEqual(captured["payload"]["input"][0]["content"][1]["type"], "input_image")
        self.assertNotIn("temperature", captured["payload"])

        def fake_chat_urlopen(request, timeout=0):
            captured["url"] = request.full_url
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return _Response({"choices": [{"message": {"content": "claude-ok"}}]})

        claude = AIClient(
            api_key="secret",
            base_url=cursor_p["base_url"],
            model="claude-sonnet-4-6",
            api_mode="chat_completions",
        )
        with patch("urllib.request.urlopen", fake_chat_urlopen):
            self.assertEqual(claude.ask("hello"), "claude-ok")
        self.assertTrue(captured["url"].endswith("/claude-cursor-full/v1/chat/completions"))
        self.assertEqual(captured["payload"]["model"], "claude-sonnet-4-6")


if __name__ == "__main__":
    unittest.main()
