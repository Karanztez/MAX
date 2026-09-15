"""
cli.py — Cross-platform Terminal & Mobile CLI Interface for MAX AI Agent.
Works seamlessly on Linux, macOS, Windows, Android (Termux), Docker, and headless servers.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

# Bootstrap sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.ai_client import AIClient
from src.core.mcp_manager import MCPManager
from src.core.provider_profiles import default_profiles, normalize_profiles
from src.core.settings_store import SettingsStore
from src.core.skill_manager import SkillManager
from src.core.updater import APP_VERSION


# ─── ANSI Terminal Colors ───────────────────────────────────────────────────────
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def _supports_color() -> bool:
    """Check if stdout supports ANSI color codes."""
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.RESET}" if _supports_color() else text


def safe_print(*args: Any, **kwargs: Any) -> None:
    """Print safely without crashing on Windows cp874 or legacy terminal encoding."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
        sanitized = text.encode(encoding, errors="replace").decode(encoding)
        print(sanitized, **kwargs)


# ─── Terminal Application ───────────────────────────────────────────────────────
class MaxTerminalApp:
    def __init__(self) -> None:
        self.settings_store = SettingsStore()
        self.skill_manager = SkillManager()
        self.mcp_manager = MCPManager()
        self.profiles, self.selected_profile_id = self.settings_store.load_provider_settings(default_profiles())
        self.history: list[dict[str, Any]] = []
        self.active_profile = self._get_active_profile()

    def _get_active_profile(self) -> dict[str, Any]:
        for p in self.profiles:
            if p["id"] == self.selected_profile_id:
                return p
        return self.profiles[0] if self.profiles else default_profiles()[0]

    def _create_client(self) -> AIClient:
        p = self.active_profile
        return AIClient(
            api_key=p.get("api_key", ""),
            base_url=p.get("base_url", ""),
            model=p.get("model", ""),
            api_mode=p.get("api_mode", "chat_completions"),
            timeout=60,
        )

    def print_banner(self) -> None:
        p = self.active_profile
        tools_count = len(self.mcp_manager.get_all_tools()) if self.mcp_manager.enabled else 0
        banner = f"""
{color("╔═══════════════════════════════════════════════════════════════╗", Colors.CYAN)}
{color("║", Colors.CYAN)}  {color(f"MAX AI Agent v{APP_VERSION} (Terminal & Mobile Mode)", Colors.BOLD + Colors.GREEN)}          {color("║", Colors.CYAN)}
{color("║", Colors.CYAN)}  Platform: {color(f"{sys.platform} ({os.name})", Colors.YELLOW)}  •  Tools: {color(str(tools_count) + ' available', Colors.GREEN)}      {color("║", Colors.CYAN)}
{color("║", Colors.CYAN)}  Profile:  {color(p.get('name', 'Default'), Colors.BOLD)}  •  Model: {color(p.get('model', ''), Colors.CYAN)}  {color("║", Colors.CYAN)}
{color("╚═══════════════════════════════════════════════════════════════╝", Colors.CYAN)}
พิมพ์ {color('/help', Colors.BOLD)} เพื่อดูคำสั่งทั้งหมด หรือพิมพ์ข้อความเพื่อเริ่มคุยได้ทันที
พิมพ์ {color('/exit', Colors.RED)} เพื่อออกจากโปรแกรม
"""
        safe_print(banner)

    def handle_command(self, cmd: str) -> bool:
        """Handle slash commands. Returns True if command was handled."""
        parts = cmd.strip().split()
        if not parts:
            return True
        action = parts[0].lower()

        if action in {"/exit", "/quit", ":q"}:
            safe_print(color("\n👋 ขอบคุณที่ใช้งาน MAX AI แล้วพบกันใหม่ครับ!", Colors.GREEN))
            sys.exit(0)

        elif action in {"/clear", "/cls", "/reset"}:
            self.history.clear()
            safe_print(color("🧹 เคลียร์ประวัติการสนทนาเรียบร้อยแล้ว", Colors.GREEN))
            return True

        elif action == "/help":
            safe_print(f"""
{color("คำสั่งที่ใช้งานได้ (Terminal Commands):", Colors.BOLD)}
  {color('/help', Colors.CYAN)}                  - แสดงคำแนะนำการใช้งาน
  {color('/profiles', Colors.CYAN)}              - ดูรายชื่อ Provider Profiles ทั้งหมด
  {color('/profile <name>', Colors.CYAN)}        - สลับไปใช้ Profile ที่ต้องการ
  {color('/models', Colors.CYAN)}                - ดูรายชื่อโมเดลใน Profile ปัจจุบัน
  {color('/model <name>', Colors.CYAN)}          - เปลี่ยนโมเดลที่ใช้งาน
  {color('/tools', Colors.CYAN)}                 - แสดงรายการเครื่องมือทั้งหมด ({len(self.mcp_manager.get_all_tools())} tools)
  {color('/health', Colors.CYAN)}                - ทดสอบสถานะการเชื่อมต่อ API / Ping
  {color('/clear', Colors.CYAN)}                 - เคลียร์ประวัติการสนทนา
  {color('/exit', Colors.RED)}                  - ออกจากโปรแกรม
""")
            return True

        elif action == "/profiles":
            safe_print(color("\n📌 รายการ Provider Profiles:", Colors.BOLD))
            for p in self.profiles:
                is_active = p["id"] == self.selected_profile_id
                marker = color("▶ [ACTIVE]", Colors.GREEN + Colors.BOLD) if is_active else " "
                safe_print(f"  {marker} {p['name']} ({p.get('base_url', '')}) -> Model: {p.get('model', '')}")
            safe_print()
            return True

        elif action == "/profile":
            if len(parts) < 2:
                safe_print(color("กรุณาระบุชื่อโปรไฟล์ เช่น /profile Claude Native", Colors.YELLOW))
                return True
            target_name = " ".join(parts[1:]).strip().casefold()
            match = next((p for p in self.profiles if p["name"].casefold() == target_name or p["id"].casefold() == target_name), None)
            if match:
                self.selected_profile_id = match["id"]
                self.active_profile = match
                self.settings_store.save_provider_settings(self.profiles, self.selected_profile_id, remember=True)
                safe_print(color(f"✅ สลับไปใช้ Profile: {match['name']} (Model: {match['model']})", Colors.GREEN))
            else:
                safe_print(color(f"❌ ไม่พบ Profile '{' '.join(parts[1:])}'", Colors.RED))
            return True

        elif action == "/models":
            safe_print(color(f"\n🤖 รายชื่อโมเดลสำหรับ {self.active_profile['name']}:", Colors.BOLD))
            for m in self.active_profile.get("models", []):
                is_cur = m == self.active_profile.get("model")
                marker = color("▶", Colors.GREEN) if is_cur else " "
                safe_print(f"  {marker} {m}")
            safe_print()
            return True

        elif action == "/model":
            if len(parts) < 2:
                safe_print(color("กรุณาระบุชื่อโมเดล เช่น /model claude-sonnet-4-6", Colors.YELLOW))
                return True
            model_name = parts[1].strip()
            self.active_profile["model"] = model_name
            self.settings_store.save_provider_settings(self.profiles, self.selected_profile_id, remember=True)
            safe_print(color(f"✅ เปลี่ยนโมเดลเป็น: {model_name}", Colors.GREEN))
            return True

        elif action == "/tools":
            tools = self.mcp_manager.get_all_tools()
            safe_print(color(f"\n🛠 รายการเครื่องมือทั้งหมด ({len(tools)} เครื่องมือ):", Colors.BOLD))
            for t in tools:
                safe_print(f"  • {color(t.name, Colors.CYAN)}: {t.description}")
            safe_print()
            return True

        elif action == "/health":
            safe_print(color(f"⚡ กำลังทดสอบสถานะ {self.active_profile['name']}...", Colors.YELLOW))
            client = self._create_client()
            start = time.monotonic()
            try:
                ans = client.ask("ping", max_tokens=10)
                dur = (time.monotonic() - start) * 1000
                safe_print(color(f"🟢 ออนไลน์! ตอบสนองใน {dur:.0f}ms", Colors.GREEN))
            except Exception as ex:
                dur = (time.monotonic() - start) * 1000
                safe_print(color(f"🔴 ออฟไลน์ / เกิดข้อผิดพลาด ({dur:.0f}ms): {ex}", Colors.RED))
            return True

        return False

    def run_prompt_single(self, prompt: str) -> None:
        """Execute single prompt and exit."""
        client = self._create_client()
        tools = self.mcp_manager.get_openai_tools() if (self.mcp_manager.enabled and client.api_mode != "responses") else None

        if tools:
            def on_status(text: str) -> None:
                safe_print(color(f"⚙ {text}", Colors.DIM))

            _history, logs = client.chat_with_tools(
                prompt, history=[], tools=tools,
                tool_executor=self.mcp_manager.execute_tool, on_status=on_status
            )
            safe_print(_history[-1]["content"])
        else:
            ans = client.ask(prompt)
            safe_print(ans)

    def interactive_loop(self) -> None:
        """Main terminal interactive prompt loop."""
        self.print_banner()

        while True:
            try:
                prompt_label = f"\n{color('You', Colors.BOLD + Colors.CYAN)}: "
                user_input = input(prompt_label).strip()
                if not user_input:
                    continue

                if user_input.startswith("/"):
                    if self.handle_command(user_input):
                        continue

                # Run conversation
                client = self._create_client()
                tools = self.mcp_manager.get_openai_tools() if (self.mcp_manager.enabled and client.api_mode != "responses") else None

                safe_print(f"\n{color('AI', Colors.BOLD + Colors.GREEN)}: ", end="", flush=True)

                if tools:
                    def on_status(text: str) -> None:
                        safe_print(f"\n{color('⚙ ' + text, Colors.DIM)}", flush=True)

                    start_time = time.monotonic()
                    self.history, logs = client.chat_with_tools(
                        user_input, self.history, tools=tools,
                        tool_executor=self.mcp_manager.execute_tool, on_status=on_status
                    )
                    reply = self.history[-1]["content"]
                    elapsed = time.monotonic() - start_time
                    safe_print(f"\n{reply}")
                    safe_print(color(f"\n[เสร็จสิ้นใน {elapsed:.2f}s]", Colors.DIM))
                else:
                    start_time = time.monotonic()
                    def on_chunk(token: str) -> None:
                        try:
                            sys.stdout.write(token)
                            sys.stdout.flush()
                        except UnicodeEncodeError:
                            enc = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
                            sys.stdout.write(token.encode(enc, errors="replace").decode(enc))
                            sys.stdout.flush()

                    self.history = client.stream_chat(user_input, self.history, on_chunk=on_chunk)
                    elapsed = time.monotonic() - start_time
                    safe_print(color(f"\n\n[เสร็จสิ้นใน {elapsed:.2f}s]", Colors.DIM))

            except (KeyboardInterrupt, EOFError):
                safe_print(color("\n\n👋 ปิดการทำงาน", Colors.YELLOW))
                break
            except Exception as ex:
                safe_print(color(f"\n❌ ข้อผิดพลาด: {ex}", Colors.RED))


def run_cli(args: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="MAX AI Agent — Terminal & Mobile CLI")
    parser.add_argument("-p", "--prompt", type=str, help="รันคำสั่งเดียวแบบ Single-shot แล้วแสดงผลลัพธ์")
    parser.add_argument("-m", "--model", type=str, help="ระบุโมเดลที่ต้องการใช้งาน")
    parser.add_argument("-c", "--cli", action="store_true", help="เปิดโหมด Terminal Interactive CLI")
    parsed, remaining = parser.parse_known_args(args)

    app = MaxTerminalApp()
    if parsed.model:
        app.active_profile["model"] = parsed.model

    if parsed.prompt:
        app.run_prompt_single(parsed.prompt)
    elif remaining and not parsed.cli:
        app.run_prompt_single(" ".join(remaining))
    else:
        app.interactive_loop()


if __name__ == "__main__":
    run_cli()
