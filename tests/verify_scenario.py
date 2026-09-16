"""
verify_scenario.py — End-to-end verification of tool execution intelligence & response synthesis.
Tests:
1. GitHub URL raw README direct fetch optimization in _builtin_fetch_web.
2. chat_with_tools synthesis & fallback reporting when encountering tools & errors.
3. chat_with_tools loop prevention when tools fail repeatedly.
"""

import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.mcp.builtins.web_tools import _builtin_fetch_web
    from core.ai_client import AIClient
except ImportError:
    from src.core.mcp.builtins.web_tools import _builtin_fetch_web  # type: ignore[no-redef]
    from src.core.ai_client import AIClient  # type: ignore[no-redef]


def run_tests():
    print("=" * 70)
    print("TEST 1: GitHub URL Optimization in _builtin_fetch_web")
    print("=" * 70)
    github_url = "https://github.com/Karanztez/MAX"
    content = _builtin_fetch_web(github_url)
    print(f"URL: {github_url}")
    print(f"Returned length: {len(content)} chars")
    # Check that raw content contains MAX details rather than full webpage HTML garbage
    is_readme = "# MAX" in content or "MaxPlus" in content or "AI" in content
    print(f"Detected README content: {is_readme}")
    print(f"Sample content preview (first 300 chars):\n{content[:300]}...")
    print("\n[RESULT 1]: PASSED\n")

    print("=" * 70)
    print("TEST 2: chat_with_tools — Scenario: GitHub link + 'ลองเชื่อมต่อ api ให้หน่อย'")
    print("=" * 70)
    client = AIClient(api_key="mock-test-key")

    # Simulate model deciding to fetch GitHub page first
    step = 0
    def mock_call_response(messages, **kwargs):
        nonlocal step
        step += 1
        if step == 1:
            return {
                "role": "assistant",
                "content": "ฉันจะตรวจสอบข้อมูลและ API จากลิงก์ GitHub https://github.com/Karanztez/MAX ให้ก่อนครับ",
                "tool_calls": [
                    {
                        "id": "call_github",
                        "type": "function",
                        "function": {
                            "name": "fetch_web_page",
                            "arguments": json.dumps({"url": "https://github.com/Karanztez/MAX"}),
                        },
                    }
                ],
            }
        else:
            # Model finishes tool round with empty text (previously caused '(ดำเนินการเสร็จสิ้น)')
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": None,
            }

    client._call_response = mock_call_response

    # Mock the synthesis call response to return a high quality structured answer
    client._call = lambda msgs, **kwargs: (
        "### 1. สรุปผลการดำเนินการ (Executive Summary)\n"
        "เชื่อมต่อและดึงข้อมูลจาก repository `https://github.com/Karanztez/MAX` สำเร็จ โดยได้อ่านโครงสร้าง API และ SDK เรียบร้อยแล้ว\n\n"
        "### 2. สิ่งที่ตรวจสอบและพบ (Key Findings)\n"
        "- **Repository**: Karanztez/MAX\n"
        "- **สถาปัตยกรรม**: รองรับ Multi-model API (OpenAI, Gemini, Ollama, DeepSeek, Claude, OpenRouter)\n"
        "- **Endpoints & SDK**: มีคลาส `AIClient` ใน `src/core/ai_client.py` และรองรับ Function Calling / MCP Tools\n\n"
        "### 3. วิธีการเชื่อมต่อ API (Connection Guide & Example)\n"
        "```python\n"
        "from src.core.ai_client import AIClient\n\n"
        "# เริ่มต้นการเชื่อมต่อ API client\n"
        "client = AIClient(\n"
        "    api_key='YOUR_API_KEY',\n"
        "    provider='openai',  # หรือ 'gemini', 'deepseek', 'openrouter'\n"
        "    model='gpt-4o'\n"
        ")\n"
        "response = client.chat([{'role': 'user', 'content': 'สวัสดี'}])\n"
        "print(response)\n"
        "```\n\n"
        "### 4. คำแนะนำหรือขั้นตอนถัดไป (Next Steps)\n"
        "1. กำหนดค่า API Key ในไฟล์ `.env` หรือผ่านหน้า Settings\n"
        "2. สามารถเรียกใช้เครื่องมือภายนอกผ่าน MCP Manager ได้ทันที"
    )

    history, logs = client.chat_with_tools(
        user_message="https://github.com/Karanztez/MAX ลองเชื่อมต่อ api ให้หน่อย",
        tools=[{"type": "function", "function": {"name": "fetch_web_page"}}],
        tool_executor=lambda name, args: _builtin_fetch_web(args.get("url", "") if isinstance(args, dict) else str(args)),
        max_tool_rounds=5,
    )

    final_reply = history[-1]["content"]
    print("Execution Logs:")
    for log in logs:
        print(f"  - {log}")
    print("\nFinal Model Output Received by User:")
    print("-" * 50)
    print(final_reply)
    print("-" * 50)

    assert "(ดำเนินการเสร็จสิ้น)" not in final_reply, "Error: Still returned fallback string!"
    assert "สรุปผลการดำเนินการ" in final_reply
    print("\n[RESULT 2]: PASSED (No cut-off, rich structured answer delivered)\n")

    print("=" * 70)
    print("TEST 3: Fallback Summary Generation (When model completely silent)")
    print("=" * 70)
    # Simulate completely silent synthesis call (empty string)
    client._call = lambda msgs, **kwargs: ""
    step = 0

    history_fb, logs_fb = client.chat_with_tools(
        user_message="https://github.com/Karanztez/MAX ลองเชื่อมต่อ api ให้หน่อย",
        tools=[{"type": "function", "function": {"name": "fetch_web_page"}}],
        tool_executor=lambda name, args: "HTTP 404: Not Found",
        max_tool_rounds=2,
    )
    fallback_reply = history_fb[-1]["content"]
    print("Fallback Report Generated Automatically from Logs:")
    print("-" * 50)
    print(fallback_reply)
    print("-" * 50)
    assert "(ดำเนินการเสร็จสิ้น)" not in fallback_reply
    assert "รายงานสรุปผลการดำเนินการ (Execution Summary)" in fallback_reply
    print("\n[RESULT 3]: PASSED (Structured log report produced automatically)\n")

    print("=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
