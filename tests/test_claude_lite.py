import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.ai_client import AIClient

API_KEY  = "ccsk-5a038c1d0145e630a8b4296893d08a4ea30c603c77cc9372b62cf621f331984a"
BASE_URL = "https://api.maxplus-ai.cc/claude-antigravity-full/v1"
MODELS   = [
    "claude-haiku-4-5-20251001",
    "claude-opus-4-5-20251101",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
]

print("=" * 60)
print("MaxPlus Claude Lite — Connection Test")
print("=" * 60)

# 1) GET /models
client = AIClient(api_key=API_KEY, base_url=BASE_URL, model=MODELS[0], timeout=20)
try:
    models = client.list_models()
    print(f"[PASS] GET /models -> {len(models)} models: {models}")
except Exception as ex:
    print(f"[FAIL] GET /models -> {ex}")
    models = MODELS

print()

# 2) Quick ask per model
for model in MODELS[:3]:       # test 3 models เพื่อไม่ให้นานเกิน
    c = AIClient(api_key=API_KEY, base_url=BASE_URL, model=model, timeout=30)
    try:
        ans = c.ask("Reply with exactly: PONG", max_tokens=16)
        print(f"[PASS] {model}: {ans!r}")
    except Exception as ex:
        print(f"[FAIL] {model}: {ex}")

print()
print("Done.")
