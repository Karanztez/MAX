"""
cli.py — Cross-platform Terminal & Mobile CLI Interface for MAX AI Agent.
Works seamlessly on Linux, macOS, Windows, Android (Termux), Docker, and headless servers.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

# Bootstrap sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from core.ai_client import AIClient
    from core.mcp_manager import MCPManager, set_web_permission_handler
    from core.provider_profiles import default_profiles, normalize_profiles, new_custom_profile
    from core.settings_store import SettingsStore
    from core.skill_manager import SkillManager
    from core.updater import (
        APP_VERSION,
        check_github_release,
        is_newer_version,
        is_frozen_exe,
        download_file,
        apply_exe_update_and_restart,
    )
except (ImportError, ModuleNotFoundError):
    from src.core.ai_client import AIClient  # type: ignore[no-redef]
    from src.core.mcp_manager import MCPManager, set_web_permission_handler  # type: ignore[no-redef]
    from src.core.provider_profiles import default_profiles, normalize_profiles, new_custom_profile  # type: ignore[no-redef]
    from src.core.settings_store import SettingsStore  # type: ignore[no-redef]
    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]
    from src.core.updater import (  # type: ignore[no-redef]
        APP_VERSION,
        check_github_release,
        is_newer_version,
        is_frozen_exe,
        download_file,
        apply_exe_update_and_restart,
    )


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
        set_web_permission_handler(self._handle_web_permission)
        self.is_first_run = not self.settings_store.has_saved_key()
        self.profiles, self.selected_profile_id = self.settings_store.load_provider_settings(default_profiles())
        self.history: list[dict[str, Any]] = []
        self.active_profile = self._get_active_profile()

    def _handle_web_permission(self, domain: str, url: str, action: str) -> bool:
        """Interactive prompt in CLI to grant, deny, or whitelist web access."""
        safe_print(color(f"\n🔒 [ความปลอดภัย] AI ร้องขอการเข้าถึงเว็บไซต์ภายนอก", Colors.BOLD + Colors.YELLOW))
        safe_print(f"• กิจกรรม: {action}")
        safe_print(f"• URL: {url}")
        safe_print(f"• โดเมน: {color(domain, Colors.CYAN + Colors.BOLD)}")
        safe_print(color("กรุณาเลือกการอนุญาต:", Colors.BOLD))
        safe_print(f"  [1] {color('ยอมรับครั้งนี้ (Allow once)', Colors.GREEN)}")
        safe_print(f"  [2] {color('ไม่อนุญาต (Deny / Cancel)', Colors.RED)}")
        safe_print(f"  [3] {color(f'ยอมรับเว็บนี้เสมอ (Always allow {domain})', Colors.CYAN)}")
        safe_print(f"  [4] {color('อนุญาตทุกเว็บตลอดไป (Always allow all)', Colors.HEADER)}")

        try:
            choice = input(color("\nเลือก [1-4 / y / n] (ค่าเริ่มต้น 1): ", Colors.BOLD + Colors.CYAN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False

        if choice in {"2", "n", "no", "deny"}:
            safe_print(color(f"❌ ปฏิเสธการเข้าถึง {domain}\n", Colors.RED))
            return False
        elif choice in {"3", "always", "whitelist"}:
            self.settings_store.add_allowed_domain(domain)
            safe_print(color(f"✅ บันทึก '{domain}' ในรายการที่อนุญาตเสมอเรียบร้อยแล้ว\n", Colors.GREEN))
            return True
        elif choice in {"4", "all"}:
            self.settings_store.save_web_security_settings(policy="allow_all")
            safe_print(color(f"✅ เปิดโหมดอนุญาตทุกเว็บตลอดไป (Allow all domains) เรียบร้อยแล้ว\n", Colors.GREEN))
            return True
        else:
            safe_print(color(f"✅ อนุญาตการเข้าถึง {domain} ชั่วคราว (ครั้งนี้)\n", Colors.GREEN))
            return True

    def _get_active_profile(self) -> dict[str, Any]:
        for p in self.profiles:
            if p["id"] == self.selected_profile_id:
                return p
        return self.profiles[0] if self.profiles else default_profiles()[0]

    def _save_profiles(self) -> None:
        self.settings_store.save_provider_settings(
            self.profiles, self.selected_profile_id, remember=True
        )

    def _ensure_credentials(self) -> bool:
        """Prompt user for Base URL or API Key directly in CLI if missing."""
        p = self.active_profile

        # 1. Check Base URL
        if not p.get("base_url", "").strip():
            safe_print(color(f"\n🌐 ยังไม่ได้ระบุ Base URL สำหรับโปรไฟล์ [{p.get('name', 'Custom')}]", Colors.YELLOW))
            new_url = input(f"{color('กรุณากรอก Base URL', Colors.BOLD)}: ").strip()
            if new_url:
                p["base_url"] = new_url
                self._save_profiles()
                safe_print(color(f"✅ บันทึก Base URL: {new_url}", Colors.GREEN))

        # 2. Check API Key
        env_key = os.environ.get("MAXPLUS_API_KEY", "").strip()
        if not p.get("api_key", "").strip() and not env_key:
            safe_print(color(f"\n🔑 ไม่พบ API Key สำหรับโปรไฟล์ [{p.get('name', 'Default')}]", Colors.YELLOW))
            safe_print(color("  (คุณสามารถกด Enter เพื่อข้ามหากเซิร์ฟเวอร์ไม่จำเป็นต้องใช้ Key)", Colors.DIM))
            new_key = input(f"{color('กรุณากรอก API Key', Colors.BOLD)}: ").strip()
            if new_key:
                p["api_key"] = new_key
                self._save_profiles()
                safe_print(color("✅ บันทึก API Key เรียบร้อยแล้ว", Colors.GREEN))

        return True

    def _create_client(self) -> AIClient:
        p = self.active_profile
        return AIClient(
            api_key=p.get("api_key", ""),
            base_url=p.get("base_url", ""),
            model=p.get("model", ""),
            api_mode=p.get("api_mode", "chat_completions"),
            timeout=60,
        )

    def interactive_setup(self, is_first_time: bool = False) -> None:
        """Numbered 1-2-3-4 interactive setup for Provider, Model, Base URL, and API Key."""
        title = "✨ ยินดีต้อนรับสู่ MAX AI — ตั้งค่าเริ่มต้นใช้งาน" if is_first_time else "⚙️ ตั้งค่าผู้ให้บริการและโมเดล (Provider & Model Setup)"
        safe_print(color(f"\n{'='*65}", Colors.CYAN))
        safe_print(color(f"  {title}", Colors.BOLD + Colors.GREEN))
        safe_print(color(f"{'='*65}\n", Colors.CYAN))

        # ─── Step 1: Select Provider ──────────────────────────────────────────
        safe_print(color("📌 ขั้นตอนที่ 1: เลือกผู้ให้บริการ AI (พิมพ์หมายเลข 1-N หรือชื่อ):", Colors.BOLD))
        for idx, p in enumerate(self.profiles, 1):
            is_active = p["id"] == self.selected_profile_id
            marker = color("▶ [เลือกอยู่]", Colors.GREEN) if is_active else "  "
            safe_print(f"  [{idx}] {p['name']} ({p.get('base_url', '')}) {marker}")
        safe_print(f"  [+] เพิ่ม Custom Provider ใหม่")

        while True:
            choice = input(color(f"\nเลือกผู้ให้บริการ [1-{len(self.profiles)} / +]: ", Colors.BOLD + Colors.CYAN)).strip()
            if not choice:
                # Keep current
                break
            if choice == "+":
                new_p = new_custom_profile(len(self.profiles) + 1)
                custom_name = input("ตั้งชื่อ Provider ใหม่: ").strip() or new_p["name"]
                new_p["name"] = custom_name
                custom_url = input("ระบุ Base URL (เช่น https://api.openai.com/v1): ").strip()
                if custom_url:
                    new_p["base_url"] = custom_url
                self.profiles.append(new_p)
                self.selected_profile_id = new_p["id"]
                self.active_profile = new_p
                safe_print(color(f"✅ เพิ่ม Provider '{custom_name}' เรียบร้อยแล้ว", Colors.GREEN))
                break
            elif choice.isdigit():
                val = int(choice)
                if 1 <= val <= len(self.profiles):
                    self.active_profile = self.profiles[val - 1]
                    self.selected_profile_id = self.active_profile["id"]
                    safe_print(color(f"✅ เลือก Provider: {self.active_profile['name']}", Colors.GREEN))
                    break
                else:
                    safe_print(color(f"❌ หมายเลขต้องอยู่ระหว่าง 1 ถึง {len(self.profiles)}", Colors.RED))
            else:
                # Match by name
                match = next((p for p in self.profiles if p["name"].casefold() == choice.casefold()), None)
                if match:
                    self.active_profile = match
                    self.selected_profile_id = match["id"]
                    safe_print(color(f"✅ เลือก Provider: {match['name']}", Colors.GREEN))
                    break
                else:
                    safe_print(color(f"❌ ไม่พบตัวเลือก '{choice}' กรุณาระบุใหม่", Colors.RED))

        # ─── Step 2: Select Model ─────────────────────────────────────────────
        models = self.active_profile.get("models", [])
        if not models:
            models = ["gemini-3.8-flash"]
            self.active_profile["models"] = models

        safe_print(color(f"\n🤖 ขั้นตอนที่ 2: เลือกโมเดลสำหรับ [{self.active_profile['name']}] (พิมพ์หมายเลข 1-N หรือชื่อโมเดล):", Colors.BOLD))
        cur_model = self.active_profile.get("model", "")
        for idx, m in enumerate(models, 1):
            is_cur = (m == cur_model)
            marker = color("▶ [เลือกอยู่]", Colors.GREEN) if is_cur else "  "
            safe_print(f"  [{idx}] {m} {marker}")
        safe_print(f"  [+] กำหนดชื่อโมเดลใหม่เอง")

        while True:
            m_choice = input(color(f"\nเลือกโมเดล [1-{len(models)} / + / ชื่อโมเดล]: ", Colors.BOLD + Colors.CYAN)).strip()
            if not m_choice:
                break
            if m_choice == "+":
                custom_m = input("กรุณากรอกชื่อโมเดลที่ต้องการ: ").strip()
                if custom_m:
                    if custom_m not in models:
                        models.insert(0, custom_m)
                    self.active_profile["model"] = custom_m
                    safe_print(color(f"✅ เลือกโมเดล: {custom_m}", Colors.GREEN))
                    break
            elif m_choice.isdigit():
                val = int(m_choice)
                if 1 <= val <= len(models):
                    self.active_profile["model"] = models[val - 1]
                    safe_print(color(f"✅ เลือกโมเดล: {self.active_profile['model']}", Colors.GREEN))
                    break
                else:
                    safe_print(color(f"❌ หมายเลขต้องอยู่ระหว่าง 1 ถึง {len(models)}", Colors.RED))
            else:
                if m_choice not in models:
                    models.insert(0, m_choice)
                self.active_profile["model"] = m_choice
                safe_print(color(f"✅ เลือกโมเดล: {m_choice}", Colors.GREEN))
                break

        # ─── Step 3: Base URL & API Key Check ─────────────────────────────────
        safe_print(color(f"\n🔑 ขั้นตอนที่ 3: ตรวจสอบการเชื่อมต่อและ API Key", Colors.BOLD))
        cur_url = self.active_profile.get("base_url", "")
        url_input = input(f"🌐 Base URL [{cur_url}] (กด Enter เพื่อคงเดิม): ").strip()
        if url_input:
            self.active_profile["base_url"] = url_input

        cur_key = self.active_profile.get("api_key", "")
        masked_key = (cur_key[:6] + "..." + cur_key[-4:]) if len(cur_key) > 10 else ("(ตั้งค่าแล้ว)" if cur_key else "(ยังไม่มี)")
        key_input = input(f"🔑 API Key [{masked_key}] (กด Enter เพื่อคงเดิม): ").strip()
        if key_input:
            self.active_profile["api_key"] = key_input

        # Save all settings securely
        self._save_profiles()
        safe_print(color("\n✨ บันทึกการตั้งค่าทั้งหมดเรียบร้อยแล้ว พร้อมใช้งานทันที!\n", Colors.BOLD + Colors.GREEN))

    def check_and_perform_update(self) -> None:
        """Check for updates from GitHub Releases and perform self-update."""
        safe_print(color(f"\n🔍 กำลังตรวจสอบการอัปเดตจาก GitHub ({APP_VERSION})...", Colors.YELLOW))
        info = check_github_release()
        if not info:
            safe_print(color("❌ ไม่สามารถเชื่อมต่อกับ GitHub API ได้ในขณะนี้ กรุณาลองใหม่อีกครั้ง", Colors.RED))
            return

        if not is_newer_version(info.version, APP_VERSION):
            safe_print(color(f"✅ คุณกำลังใช้งาน MAX AI เวอร์ชันล่าสุดแล้ว (v{APP_VERSION})", Colors.GREEN))
            return

        safe_print(color(f"\n🚀 พบเวอร์ชันใหม่: {info.tag_name} (เวอร์ชันปัจจุบัน: v{APP_VERSION})", Colors.BOLD + Colors.GREEN))
        safe_print(color(f"หัวข้อ: {info.title}", Colors.BOLD))
        if info.body.strip():
            safe_print(color("\n📝 บันทึกการเปลี่ยนแปลง (Changelog):", Colors.BOLD))
            safe_print(color("-" * 50, Colors.DIM))
            safe_print(info.body.strip())
            safe_print(color("-" * 50, Colors.DIM))

        prompt = input(color(f"\n⚡ คุณต้องการอัปเดตเป็น {info.tag_name} ทันทีหรือไม่? [Y/n]: ", Colors.BOLD + Colors.CYAN)).strip().lower()
        if prompt not in {"", "y", "yes"}:
            safe_print(color("ยกเลิกการอัปเดต", Colors.YELLOW))
            return

        # Handle update depending on runtime mode
        if is_frozen_exe():
            if not info.download_url:
                safe_print(color("❌ ไม่พบไฟล์ .exe สำหรับดาวน์โหลดใน Release ล่าสุด", Colors.RED))
                safe_print(color(f"กรุณาดาวน์โหลดด้วยตนเองที่: {info.html_url}", Colors.CYAN))
                return

            safe_print(color(f"\n⬇️ กำลังดาวน์โหลด {info.asset_name or 'MaxPlusAI.exe'}...", Colors.CYAN))
            temp_dir = tempfile.mkdtemp()
            temp_exe = os.path.join(temp_dir, "MaxPlusAI_new.exe")

            def on_progress(downloaded: int, total: int) -> None:
                if total > 0:
                    pct = int(downloaded / total * 100)
                    mb_down = downloaded / (1024 * 1024)
                    mb_total = total / (1024 * 1024)
                    bar = "█" * (pct // 5) + "░" * (20 - (pct // 5))
                    sys.stdout.write(f"\r  [{bar}] {pct}% ({mb_down:.1f}MB/{mb_total:.1f}MB)")
                    sys.stdout.flush()

            try:
                download_file(info.download_url, temp_exe, progress_callback=on_progress)
                safe_print(color("\n\n✅ ดาวน์โหลดเสร็จสิ้น กำลังสลับไฟล์และรีสตาร์ตโปรแกรม...", Colors.GREEN))
                time.sleep(1)
                apply_exe_update_and_restart(temp_exe)
            except Exception as ex:
                safe_print(color(f"\n❌ การอัปเดตล้มเหลว: {ex}", Colors.RED))
        else:
            # Source / Git / Pip Mode
            safe_print(color("\n🔄 กำลังอัปเดตซอร์สโค้ด...", Colors.CYAN))
            is_git = (Path(_ROOT) / ".git").exists()
            if is_git:
                try:
                    res = subprocess.run(["git", "pull", "origin", "main"], cwd=_ROOT, capture_output=True, text=True)
                    if res.returncode == 0:
                        safe_print(color(res.stdout, Colors.DIM))
                        safe_print(color("📦 กำลังอัปเดต Dependencies...", Colors.CYAN))
                        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=_ROOT, capture_output=True)
                        safe_print(color(f"\n✨ อัปเดต MAX AI เป็น {info.tag_name} เรียบร้อยแล้ว!", Colors.BOLD + Colors.GREEN))
                        safe_print(color("กรุณารันคำสั่ง 'max' หรือรีสตาร์ตโปรแกรมเพื่อเริ่มใช้งานเวอร์ชันใหม่", Colors.YELLOW))
                        return
                    else:
                        safe_print(color(f"Git pull error: {res.stderr}", Colors.RED))
                except Exception as ex:
                    safe_print(color(f"Git update failed: {ex}", Colors.RED))

            # Pip fallback
            try:
                safe_print(color("📦 กำลังอัปเดตผ่าน pip...", Colors.CYAN))
                res = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "git+https://github.com/Karanztez/MAX.git"], capture_output=True, text=True)
                if res.returncode == 0:
                    safe_print(color(f"\n✨ อัปเดต MAX AI สำเร็จแล้ว! กรุณารีสตาร์ตคำสั่ง max", Colors.BOLD + Colors.GREEN))
                else:
                    safe_print(color(f"Pip update error: {res.stderr}", Colors.RED))
            except Exception as ex:
                safe_print(color(f"Update failed: {ex}", Colors.RED))

    def print_banner(self) -> None:
        p = self.active_profile
        tools_count = len(self.mcp_manager.get_all_tools()) if self.mcp_manager.enabled else 0
        banner = f"""
{color("╔═══════════════════════════════════════════════════════════════╗", Colors.CYAN)}
{color("║", Colors.CYAN)}  {color(f"MAX AI Agent v{APP_VERSION} (Terminal & Mobile Mode)", Colors.BOLD + Colors.GREEN)}          {color("║", Colors.CYAN)}
{color("║", Colors.CYAN)}  Platform: {color(f"{sys.platform} ({os.name})", Colors.YELLOW)}  •  Tools: {color(str(tools_count) + ' available', Colors.GREEN)}      {color("║", Colors.CYAN)}
{color("║", Colors.CYAN)}  Profile:  {color(p.get('name', 'Default'), Colors.BOLD)}  •  Model: {color(p.get('model', ''), Colors.CYAN)}  {color("║", Colors.CYAN)}
{color("╚═══════════════════════════════════════════════════════════════╝", Colors.CYAN)}
พิมพ์ {color('/help', Colors.BOLD)} เพื่อดูคำสั่งทั้งหมด | {color('/setup', Colors.BOLD)} เพื่อสลับผู้ให้บริการ/โมเดล (1-2-3-4)
พิมพ์ {color('/update', Colors.BOLD)} เพื่อตรวจหาอัปเดตเวอร์ชัน | {color('/exit', Colors.RED)} เพื่อออก
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

        elif action in {"/update", "/upgrade"}:
            self.check_and_perform_update()
            return True

        elif action in {"/setup", "/config", "/wizard"}:
            self.interactive_setup(is_first_time=False)
            return True

        elif action == "/key":
            if len(parts) > 1:
                key_val = parts[1].strip()
            else:
                cur_key = self.active_profile.get("api_key", "")
                masked = (cur_key[:6] + "..." + cur_key[-4:]) if len(cur_key) > 10 else cur_key
                key_val = input(f"กรุณากรอก API Key ใหม่สำหรับ [{self.active_profile['name']}] (ปัจจุบัน: {masked}): ").strip()

            if key_val:
                self.active_profile["api_key"] = key_val
                self._save_profiles()
                safe_print(color("✅ บันทึก API Key เรียบร้อยแล้ว", Colors.GREEN))
            return True

        elif action in {"/baseurl", "/url"}:
            if len(parts) > 1:
                url_val = parts[1].strip()
            else:
                url_val = input(f"กรุณากรอก Base URL ใหม่สำหรับ [{self.active_profile['name']}] (ปัจจุบัน: {self.active_profile.get('base_url')}): ").strip()
            if url_val:
                self.active_profile["base_url"] = url_val
                self._save_profiles()
                safe_print(color(f"✅ บันทึก Base URL: {url_val}", Colors.GREEN))
            return True

        elif action in {"/export", "/download", "/zip"}:
            target_path = parts[1].strip() if len(parts) > 1 else "."
            custom_name = parts[2].strip() if len(parts) > 2 else ""
            safe_print(color(f"📦 กำลังบีบอัดและส่งออกโฟลเดอร์ '{target_path}' ไปยัง Download...", Colors.YELLOW))
            res = self.mcp_manager.execute_tool("export_to_download", {"source_path": target_path, "output_name": custom_name})
            safe_print(color(f"\n{res}", Colors.GREEN if not res.startswith("Error") else Colors.RED))
            return True

        elif action in {"/image", "/img", "/generate_image"}:
            prompt_text = " ".join(parts[1:]).strip()
            if not prompt_text:
                prompt_text = input("🎨 กรุณากรอกคำบรรยายภาพ (Prompt): ").strip()
            if prompt_text:
                safe_print(color(f"🎨 กำลังสร้างรูปภาพตามคำสั่ง: \"{prompt_text}\"...", Colors.YELLOW))
                res = self.mcp_manager.execute_tool("generate_image", {"prompt": prompt_text})
                safe_print(color(f"\n{res}", Colors.GREEN if not res.startswith("Error") else Colors.RED))
            return True

        elif action in {"/video", "/vid", "/generate_video"}:
            prompt_text = " ".join(parts[1:]).strip()
            if not prompt_text:
                prompt_text = input("🎬 กรุณากรอกคำบรรยายคลิปวิดีโอ (Prompt): ").strip()
            if prompt_text:
                safe_print(color(f"🎬 กำลังสร้างวิดีโอตามคำสั่ง: \"{prompt_text}\" (อาจใช้เวลาประมาณ 10-30 วินาที)...", Colors.YELLOW))
                res = self.mcp_manager.execute_tool("generate_video", {"prompt": prompt_text})
                safe_print(color(f"\n{res}", Colors.GREEN if not res.startswith("Error") else Colors.RED))
            return True

        elif action in {"/security", "/domains", "/web"}:
            sec = self.settings_store.load_web_security_settings()
            sub = parts[1].lower() if len(parts) > 1 else ""

            if sub == "allow" and len(parts) > 2:
                dom = parts[2].strip().lower()
                self.settings_store.add_allowed_domain(dom)
                safe_print(color(f"✅ เพิ่มโดเมน '{dom}' เข้า Whitelist เรียบร้อยแล้ว", Colors.GREEN))
                return True
            elif sub == "deny" and len(parts) > 2:
                dom = parts[2].strip().lower()
                self.settings_store.add_denied_domain(dom)
                safe_print(color(f"🚫 เพิ่มโดเมน '{dom}' เข้า Denylist เรียบร้อยแล้ว", Colors.RED))
                return True
            elif sub in {"policy", "mode"} and len(parts) > 2:
                new_pol = parts[2].strip().lower()
                if new_pol in {"ask", "allow_all", "deny_all"}:
                    self.settings_store.save_web_security_settings(policy=new_pol)
                    safe_print(color(f"✅ เปลี่ยนนโยบายความปลอดภัยเป็น: {new_pol}", Colors.GREEN))
                else:
                    safe_print(color("❌ นโยบายต้องเป็น 'ask', 'allow_all', หรือ 'deny_all'", Colors.RED))
                return True

            policy_str = sec.get("policy", "ask")
            allowed_list = sec.get("allowed_domains", [])
            denied_list = sec.get("denied_domains", [])

            safe_print(color("\n🔒 นโยบายความปลอดภัยการเข้าถึงเว็บไซต์ (Web Access Security):", Colors.BOLD))
            safe_print(f"• โหมดปัจจุบัน (Policy): {color(policy_str, Colors.CYAN + Colors.BOLD)} (ตัวเลือก: ask / allow_all / deny_all)")
            safe_print(color(f"\n🌐 โดเมนที่อนุญาต (Allowed Whitelist: {len(allowed_list)} โดเมน):", Colors.BOLD))
            for d in allowed_list:
                is_def = d in self.settings_store.DEFAULT_TRUSTED_DOMAINS
                tag = color("[ค่าเริ่มต้น]", Colors.DIM) if is_def else color("[ผู้ใช้กำหนด]", Colors.GREEN)
                safe_print(f"  • {d} {tag}")

            if denied_list:
                safe_print(color(f"\n🚫 โดเมนที่ถูกบล็อก (Denylist: {len(denied_list)} โดเมน):", Colors.BOLD))
                for d in denied_list:
                    safe_print(f"  • {d} {color('[บล็อก]', Colors.RED)}")

            safe_print(f"""
{color('คำสั่งจัดการความปลอดภัย:', Colors.BOLD)}
  {color('/security policy <ask|allow_all|deny_all>', Colors.CYAN)} - สลับโหมดความปลอดภัย
  {color('/security allow <domain>', Colors.CYAN)}               - เพิ่มโดเมนเข้า Whitelist
  {color('/security deny <domain>', Colors.CYAN)}                - บล็อกโดเมนไม่ให้ AI เข้าถึง
""")
            return True

        elif action in {"/skills", "/skill"}:
            sub = parts[1].lower() if len(parts) > 1 else "list"

            if sub in {"install", "add"} and len(parts) > 2:
                src_target = parts[2].strip()
                custom_sid = parts[3].strip() if len(parts) > 3 else ""
                safe_print(color(f"📦 กำลังติดตั้ง Skill จาก: {src_target}...", Colors.YELLOW))
                res = self.mcp_manager.execute_tool("install_skill", {"source": src_target, "skill_id": custom_sid})
                safe_print(color(f"{res}", Colors.GREEN if "สำเร็จ" in res or "✅" in res else Colors.RED))
                return True

            elif sub in {"remove", "delete", "rm"} and len(parts) > 2:
                target_sid = parts[2].strip()
                safe_print(color(f"🗑️ กำลังลบ Skill: {target_sid}...", Colors.YELLOW))
                res = self.mcp_manager.execute_tool("remove_skill", {"skill_id": target_sid})
                safe_print(color(f"{res}", Colors.GREEN if "สำเร็จ" in res or "🗑️" in res else Colors.RED))
                return True

            elif sub in {"list", "ls", "all"}:
                res = self.mcp_manager.execute_tool("list_skills", {})
                safe_print(color(f"\n{res}", Colors.CYAN))
                safe_print(f"""
{color('คำสั่งจัดการ Skill:', Colors.BOLD)}
  {color('/skill install <owner/repo | url | skill_name>', Colors.CYAN)} - ติดตั้ง Skill อัตโนมัติจาก GitHub / URL
  {color('/skill remove <skill_id>', Colors.CYAN)}                     - ลบ Skill ออกจากระบบ
  {color('/skills', Colors.CYAN)}                                       - ดูรายการ Skill ทั้งหมด
""")
                return True
            else:
                res = self.mcp_manager.execute_tool("list_skills", {})
                safe_print(color(f"\n{res}", Colors.CYAN))
                return True

        elif action == "/help":
            safe_print(f"""
{color("คำสั่งที่ใช้งานได้ (Terminal Commands):", Colors.BOLD)}
  {color('/setup', Colors.CYAN)}                  - ตัวช่วยเลือกผู้ให้บริการ & โมเดล (โหมด 1-2-3-4)
  {color('/security', Colors.CYAN)}               - ตรวจสอบ/จัดการสิทธิ์การเข้าถึงเว็บไซต์ (Web Security)
  {color('/skills', Colors.CYAN)}                 - แสดงรายการ ทักษะ (Skills) ที่ติดตั้งอยู่ในระบบ
  {color('/skill install <source>', Colors.CYAN)}  - ติดตั้ง Skill ใหม่จาก GitHub / URL อัตโนมัติ
  {color('/skill remove <id>', Colors.CYAN)}       - ลบ Skill ออกจากระบบ
  {color('/image <prompt>', Colors.CYAN)}        - สร้างรูปภาพ AI (Flux / Turbo / DALL-E) บันทึกลงเครื่อง
  {color('/video <prompt>', Colors.CYAN)}        - สร้างคลิปวิดีโอ AI (Wan2.1 / MP4) บันทึกลงเครื่อง
  {color('/export [path]', Colors.CYAN)}          - บีบอัดและส่งออกโปรเจกต์ไปยังโฟลเดอร์ Download ของมือถือ/เครื่อง
  {color('/update', Colors.CYAN)}                 - ตรวจสอบและอัปเดตเวอร์ชันโปรแกรมอัตโนมัติ
  {color('/key <api_key>', Colors.CYAN)}          - กรอกหรือแก้ไข API Key ทันทีในแชท
  {color('/baseurl <url>', Colors.CYAN)}          - กรอกหรือแก้ไข Base URL ทันทีในแชท
  {color('/profiles', Colors.CYAN)}              - ดูรายชื่อ Provider Profiles ทั้งหมด
  {color('/profile [name|number]', Colors.CYAN)} - สลับ Profile ด้วยชื่อหรือหมายเลข
  {color('/models', Colors.CYAN)}                - ดูรายชื่อโมเดลใน Profile ปัจจุบัน
  {color('/model [name|number]', Colors.CYAN)}   - เปลี่ยนโมเดลที่ใช้งาน
  {color('/tools', Colors.CYAN)}                 - แสดงรายการเครื่องมือทั้งหมด ({len(self.mcp_manager.get_all_tools())} tools)
  {color('/health', Colors.CYAN)}                - ทดสอบสถานะการเชื่อมต่อ API / Ping
  {color('/clear', Colors.CYAN)}                 - เคลียร์ประวัติการสนทนา
  {color('/exit', Colors.RED)}                  - ออกจากโปรแกรม
""")
            return True

        elif action == "/profiles":
            safe_print(color("\n📌 รายการ Provider Profiles:", Colors.BOLD))
            for idx, p in enumerate(self.profiles, 1):
                is_active = p["id"] == self.selected_profile_id
                marker = color("▶ [ACTIVE]", Colors.GREEN + Colors.BOLD) if is_active else " "
                safe_print(f"  [{idx}] {marker} {p['name']} ({p.get('base_url', '')}) -> Model: {p.get('model', '')}")
            safe_print()
            return True

        elif action == "/profile":
            if len(parts) < 2:
                # Interactive switch
                self.interactive_setup(is_first_time=False)
                return True
            target = " ".join(parts[1:]).strip()
            if target.isdigit():
                val = int(target)
                if 1 <= val <= len(self.profiles):
                    match = self.profiles[val - 1]
                else:
                    safe_print(color(f"❌ หมายเลขโปรไฟล์ต้องอยู่ระหว่าง 1 ถึง {len(self.profiles)}", Colors.RED))
                    return True
            else:
                match = next(
                    (p for p in self.profiles
                     if p["name"].casefold() == target.casefold()
                     or p["id"].casefold() == target.casefold()
                     or target.casefold() in p["name"].casefold()
                     or target.casefold() in p["id"].casefold()),
                    None
                )

            if match:
                self.selected_profile_id = match["id"]
                self.active_profile = match
                self._save_profiles()
                safe_print(color(f"✅ สลับไปใช้ Profile: {match['name']} (Model: {match['model']})", Colors.GREEN))
            else:
                safe_print(color(f"❌ ไม่พบ Profile '{target}'", Colors.RED))
            return True

        elif action == "/models":
            safe_print(color(f"\n🤖 รายชื่อโมเดลสำหรับ {self.active_profile['name']}:", Colors.BOLD))
            for idx, m in enumerate(self.active_profile.get("models", []), 1):
                is_cur = m == self.active_profile.get("model")
                marker = color("▶", Colors.GREEN) if is_cur else " "
                safe_print(f"  [{idx}] {marker} {m}")
            safe_print()
            return True

        elif action == "/model":
            models = self.active_profile.get("models", [])
            if len(parts) < 2:
                # Print numbered list and prompt
                safe_print(color(f"\n🤖 กรุณาเลือกโมเดลสำหรับ {self.active_profile['name']}:", Colors.BOLD))
                for idx, m in enumerate(models, 1):
                    is_cur = m == self.active_profile.get("model")
                    marker = color("▶", Colors.GREEN) if is_cur else " "
                    safe_print(f"  [{idx}] {marker} {m}")
                m_in = input(color("\nพิมพ์หมายเลขหรือชื่อโมเดล: ", Colors.BOLD + Colors.CYAN)).strip()
                if not m_in:
                    return True
                target = m_in
            else:
                target = parts[1].strip()

            if target.isdigit():
                val = int(target)
                if 1 <= val <= len(models):
                    model_name = models[val - 1]
                else:
                    safe_print(color(f"❌ หมายเลขต้องอยู่ระหว่าง 1 ถึง {len(models)}", Colors.RED))
                    return True
            else:
                model_name = target
                if model_name not in models:
                    models.insert(0, model_name)

            self.active_profile["model"] = model_name
            self._save_profiles()
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
            self._ensure_credentials()
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
        self._ensure_credentials()
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
        if self.is_first_run:
            self.interactive_setup(is_first_time=True)

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

                # Ensure API credentials exist before sending request
                self._ensure_credentials()

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
    parser.add_argument("-P", "--provider", type=str, help="ระบุผู้ให้บริการ AI (เช่น 'China Town', 'Native', 'Claude', 'Grok')")
    parser.add_argument("-m", "--model", type=str, help="ระบุโมเดลที่ต้องการใช้งาน")
    parser.add_argument("-c", "--cli", action="store_true", help="เปิดโหมด Terminal Interactive CLI")
    parser.add_argument("-u", "--update", action="store_true", help="ตรวจหาและอัปเดตเวอร์ชันโปรแกรม")
    parser.add_argument("-s", "--setup", action="store_true", help="เปิดหน้าต่างตั้งค่า Provider และ Model")
    parsed, remaining = parser.parse_known_args(args)

    app = MaxTerminalApp()

    if parsed.provider:
        target_p = parsed.provider.strip()
        match = next(
            (p for p in app.profiles
             if p["name"].casefold() == target_p.casefold()
             or p["id"].casefold() == target_p.casefold()
             or target_p.casefold() in p["name"].casefold()
             or target_p.casefold() in p["id"].casefold()),
            None,
        )
        if match:
            app.selected_profile_id = match["id"]
            app.active_profile = match
        else:
            safe_print(color(f"⚠️ ไม่พบ Provider '{target_p}', ใช้งาน: {app.active_profile['name']}", Colors.YELLOW))

    if parsed.model:
        app.active_profile["model"] = parsed.model
        if parsed.model not in app.active_profile.get("models", []):
            app.active_profile.setdefault("models", []).insert(0, parsed.model)

    if parsed.update:
        app.check_and_perform_update()
        return

    if parsed.setup:
        app.interactive_setup(is_first_time=False)
        return

    if parsed.prompt:
        app.run_prompt_single(parsed.prompt)
    elif remaining and not parsed.cli:
        app.run_prompt_single(" ".join(remaining))
    else:
        app.interactive_loop()


if __name__ == "__main__":
    run_cli()
