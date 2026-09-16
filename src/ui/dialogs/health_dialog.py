"""
health_dialog.py — Dialog for probing API health, model availability, and latency.
"""

import json
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.error
import urllib.request
from typing import Any, Optional

try:
    from ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_TITLE, FONT_MONO
except (ImportError, ModuleNotFoundError):
    from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_TITLE, FONT_MONO  # type: ignore[no-redef]


class HealthCheckDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, profiles: list[dict[str, Any]], active_profile_id: str) -> None:
        super().__init__(parent)
        self._profiles = profiles
        self._active_id = active_profile_id
        self._is_running = False
        self._results: list[dict[str, Any]] = []

        self.title("⚡ ตรวจสอบสถานะ API / Health Check")
        self.geometry("780x560")
        self.minsize(680, 480)
        self.configure(bg=T["bg"])
        self.transient(parent.winfo_toplevel())

        self._build_ui()
        self.after(200, self._start_test)

    def _build_ui(self) -> None:
        container = tk.Frame(self, bg=T["bg"], padx=20, pady=16)
        container.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(container, bg=T["bg"])
        header.pack(fill="x", pady=(0, 10))

        tk.Label(header, text="⚡ ตรวจสอบสถานะ API & โมเดล", font=FONT_TITLE,
                 bg=T["bg"], fg=T["fg"]).pack(side="left")

        self._start_btn = tk.Button(
            header, text="▶ เริ่มทดสอบใหม่", command=self._start_test,
            bg=T["accent"], fg="#ffffff", activebackground=T["accent_hover"],
            activeforeground="#ffffff", font=FONT_BOLD, relief="flat",
            padx=14, pady=6, cursor="hand2"
        )
        self._start_btn.pack(side="right")

        # Controls bar
        ctrl_bar = tk.Frame(container, bg=T["bg2"], padx=12, pady=8,
                            highlightthickness=1, highlightbackground=T["border"])
        ctrl_bar.pack(fill="x", pady=(0, 12))

        tk.Label(ctrl_bar, text="เลือก Pool / โปรไฟล์:", font=FONT_TINY,
                 bg=T["bg2"], fg=T["fg_dim"]).pack(side="left", padx=(0, 8))

        profile_names = [p["name"] for p in self._profiles]
        initial_name = next((p["name"] for p in self._profiles if p["id"] == self._active_id), profile_names[0] if profile_names else "")
        self._profile_var = tk.StringVar(value=initial_name)
        self._profile_box = ttk.Combobox(ctrl_bar, textvariable=self._profile_var,
                                         values=profile_names, state="readonly", font=FONT, width=28)
        self._profile_box.pack(side="left", padx=(0, 12))
        self._profile_box.bind("<<ComboboxSelected>>", lambda _e: self._start_test())

        self._status_lbl = tk.Label(ctrl_bar, text="พร้อมทดสอบ", font=FONT_TINY,
                                    bg=T["bg2"], fg=T["sub"])
        self._status_lbl.pack(side="left", fill="x", expand=True)

        # Results area
        results_frame = tk.Frame(container, bg=T["bg2"],
                                 highlightthickness=1, highlightbackground=T["border"])
        results_frame.pack(fill="both", expand=True)

        # Canvas + Scrollbar for results
        self._canvas = tk.Canvas(results_frame, bg=T["bg2"], bd=0, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self._canvas.yview)
        self._list_frame = tk.Frame(self._canvas, bg=T["bg2"], padx=10, pady=10)

        self._canvas_window = self._canvas.create_window((0, 0), window=self._list_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

        self._list_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Footer
        footer = tk.Frame(container, bg=T["bg"])
        footer.pack(fill="x", pady=(12, 0))

        self._summary_var = tk.StringVar(value="")
        tk.Label(footer, textvariable=self._summary_var, font=FONT_BOLD,
                 bg=T["bg"], fg=T["fg"]).pack(side="left")

        tk.Button(footer, text="📋 คัดลอกรายงาน", command=self._copy_report,
                  bg=T["bg_btn"], fg=T["fg"], activebackground=T["bg3"], activeforeground=T["fg"],
                  relief="flat", font=FONT, padx=12, pady=5, cursor="hand2").pack(side="right", padx=(8, 0))

        tk.Button(footer, text="ปิด", command=self.destroy,
                  bg=T["bg_btn"], fg=T["fg"], activebackground=T["bg3"], activeforeground=T["fg"],
                  relief="flat", font=FONT, padx=12, pady=5, cursor="hand2").pack(side="right")

    def _on_frame_configure(self, _event: object = None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: Any) -> None:
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _get_selected_profile(self) -> Optional[dict[str, Any]]:
        name = self._profile_var.get()
        return next((p for p in self._profiles if p["name"] == name), None)

    def _start_test(self) -> None:
        if self._is_running:
            return
        profile = self._get_selected_profile()
        if not profile:
            return

        self._is_running = True
        self._start_btn.configure(state="disabled", text="กำลังทดสอบ...")
        self._status_lbl.configure(text=f"กำลังเชื่อมต่อ {profile['base_url']}...")
        self._summary_var.set("")

        for child in self._list_frame.winfo_children():
            child.destroy()

        self._results.clear()
        threading.Thread(target=self._run_probe_thread, args=(profile,), daemon=True).start()

    def _run_probe_thread(self, profile: dict[str, Any]) -> None:
        base_url = str(profile.get("base_url", "")).rstrip("/")
        api_key = str(profile.get("api_key", "")).strip()
        models = list(profile.get("models", []))
        if not models:
            models = ["claude-sonnet-4-6"]

        # Step 1: Probe GET /models
        self._update_status(f"กำลังตรวจสอบรายการโมเดล (GET {base_url}/models)...")
        models_url = f"{base_url}/models"
        server_models = []
        try:
            req = urllib.request.Request(
                models_url,
                headers={"Authorization": f"Bearer {api_key}", "x-api-key": api_key}
            )
            t0 = time.monotonic()
            with urllib.request.urlopen(req, timeout=12) as resp:
                elapsed = time.monotonic() - t0
                data = json.loads(resp.read().decode("utf-8"))
                server_models = [m.get("id") or m.get("name") for m in data.get("data", [])]
                self._add_row("GET /models", "online", f"พบ {len(server_models)} โมเดลบน Server", elapsed)
        except urllib.error.HTTPError as ex:
            err = ex.read().decode("utf-8", errors="replace")
            self._add_row("GET /models", "offline" if ex.code == 503 else "error", f"HTTP {ex.code}: {err[:80]}", 0.0)
        except Exception as ex:
            self._add_row("GET /models", "error", str(ex)[:80], 0.0)

        # Step 2: Probe each model
        total = len(models)
        for idx, model_name in enumerate(models, 1):
            self._update_status(f"กำลังทดสอบโมเดล [{idx}/{total}] {model_name}...")
            self._probe_single_model(base_url, api_key, model_name, profile.get("api_mode", "chat_completions"))

        self._finish_probe()

    def _probe_single_model(self, base_url: str, api_key: str, model_name: str, api_mode: str) -> None:
        if api_mode == "responses":
            url = f"{base_url}/responses"
            payload: dict[str, Any] = {
                "model": model_name,
                "input": [{"role": "user", "content": [{"type": "input_text", "text": "ping"}]}],
                "max_output_tokens": 16,
            }
        else:
            url = f"{base_url}/chat/completions"
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 16,
            }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=18) as resp:
                elapsed = time.monotonic() - t0
                self._add_row(model_name, "online", "ตอบกลับปกติ (พร้อมใช้งาน)", elapsed)
        except urllib.error.HTTPError as ex:
            elapsed = time.monotonic() - t0
            err_body = ex.read().decode("utf-8", errors="replace")
            if ex.code == 503:
                status = "offline"
                msg = "HTTP 503 (Server ปิดปรับปรุงชั่วคราว / Down)"
            elif ex.code == 400:
                status = "error"
                msg = f"HTTP 400 ({err_body[:60]})"
            elif ex.code == 401 or ex.code == 403:
                status = "error"
                msg = f"HTTP {ex.code} (API Key ไม่ถูกต้อง / ไม่มีสิทธิ์)"
            else:
                status = "error"
                msg = f"HTTP {ex.code}: {err_body[:60]}"
            self._add_row(model_name, status, msg, elapsed)
        except Exception as ex:
            elapsed = time.monotonic() - t0
            self._add_row(model_name, "error", str(ex)[:60], elapsed)

    def _update_status(self, text: str) -> None:
        self.after(0, lambda: self._status_lbl.configure(text=text))

    def _add_row(self, name: str, status: str, detail: str, elapsed: float) -> None:
        self._results.append({"name": name, "status": status, "detail": detail, "elapsed": elapsed})
        self.after(0, lambda: self._render_row(name, status, detail, elapsed))

    def _render_row(self, name: str, status: str, detail: str, elapsed: float) -> None:
        row = tk.Frame(self._list_frame, bg=T["bg"], pady=6, padx=10,
                       highlightthickness=1, highlightbackground=T["border"])
        row.pack(fill="x", pady=(0, 6))

        if status == "online":
            badge_text = "🟢 ออนไลน์"
            badge_color = "#34a853"
        elif status == "offline":
            badge_text = "🔴 ออฟไลน์ (503)"
            badge_color = "#ea4335"
        else:
            badge_text = "🟡 ข้อผิดพลาด"
            badge_color = "#fbbc04"

        # Model name & badge
        name_lbl = tk.Label(row, text=name, font=FONT_BOLD, bg=T["bg"], fg=T["fg"], anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True)

        time_str = f"({elapsed:.1f}s)" if elapsed > 0 else ""
        tk.Label(row, text=time_str, font=FONT_TINY, bg=T["bg"], fg=T["fg_dim"]).pack(side="left", padx=(0, 10))

        status_lbl = tk.Label(row, text=badge_text, font=FONT_TINY, bg=T["bg"], fg=badge_color)
        status_lbl.pack(side="right", padx=(8, 0))

        detail_lbl = tk.Label(row, text=detail, font=FONT_TINY, bg=T["bg"], fg=T["fg_dim"], anchor="e")
        detail_lbl.pack(side="right")

    def _finish_probe(self) -> None:
        def done() -> None:
            self._is_running = False
            self._start_btn.configure(state="normal", text="▶ เริ่มทดสอบใหม่")
            self._status_lbl.configure(text="การทดสอบเสร็จสมบูรณ์")

            online_count = sum(1 for r in self._results if r["status"] == "online" and r["name"] != "GET /models")
            offline_count = sum(1 for r in self._results if r["status"] == "offline")
            error_count = sum(1 for r in self._results if r["status"] == "error" and r["name"] != "GET /models")

            self._summary_var.set(f"สรุป: 🟢 {online_count} ออนไลน์  |  🔴 {offline_count} ออฟไลน์ (503)  |  🟡 {error_count} ข้อผิดพลาด")

        self.after(0, done)

    def _copy_report(self) -> None:
        if not self._results:
            return
        lines = [f"=== รายงานสถานะ API Pool ({self._profile_var.get()}) ==="]
        for r in self._results:
            symbol = "🟢" if r["status"] == "online" else ("🔴" if r["status"] == "offline" else "🟡")
            lines.append(f"{symbol} {r['name']} ({r['elapsed']:.1f}s): {r['detail']}")
        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("คัดลอกสำเร็จ", "คัดลอกรายงานสถานะ API ลง Clipboard แล้ว", parent=self)
