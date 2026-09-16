"""
src/ui/dialogs/update_dialog.py — Modern Minimalist Update Dialog for MAX.
"""

import os
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from typing import Optional

try:
    from core.updater import UpdateInfo, APP_VERSION, download_file, is_frozen_exe, apply_exe_update_and_restart, is_newer_version
    from core.settings_store import SettingsStore
    from ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_HDR, FONT_MONO
except (ImportError, ModuleNotFoundError):
    from src.core.updater import UpdateInfo, APP_VERSION, download_file, is_frozen_exe, apply_exe_update_and_restart, is_newer_version  # type: ignore[no-redef]
    from src.core.settings_store import SettingsStore  # type: ignore[no-redef]
    from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_HDR, FONT_MONO  # type: ignore[no-redef]


class UpdateDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, info: UpdateInfo, settings_store: Optional[SettingsStore] = None) -> None:
        super().__init__(parent)
        self.info = info
        self.settings_store = settings_store or SettingsStore()
        self._is_downloading = False
        self._temp_dest: Optional[str] = None

        self.title("อัปเดต MAX")
        self.geometry("520x460")
        self.configure(bg=T["bg"])
        self.resizable(False, False)
        top = parent.winfo_toplevel()
        if isinstance(top, tk.Wm):
            self.transient(top)
        self.grab_set()

        # Center dialog relative to parent
        try:
            self.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            dw = 520
            dh = 460
            x = px + max(0, (pw - dw) // 2)
            y = py + max(0, (ph - dh) // 2)
            self.geometry(f"{dw}x{dh}+{x}+{y}")
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self) -> None:
        # Container padding
        container = tk.Frame(self, bg=T["bg"], padx=24, pady=20)
        container.pack(fill="both", expand=True)

        # Header: Title + Version Badges
        hdr_frame = tk.Frame(container, bg=T["bg"])
        hdr_frame.pack(fill="x", pady=(0, 14))

        is_newer = is_newer_version(self.info.tag_name, APP_VERSION)
        title_text = "🪶 มีเวอร์ชันใหม่พร้อมให้อัปเดต" if is_newer else "🔄 ติดตั้งเวอร์ชันล่าสุดใหม่ (Reinstall Latest Build)"

        title_lbl = tk.Label(
            hdr_frame,
            text=title_text,
            font=FONT_HDR,
            bg=T["bg"],
            fg=T["fg"],
            anchor="w",
        )
        title_lbl.pack(anchor="w")

        ver_frame = tk.Frame(hdr_frame, bg=T["bg"])
        ver_frame.pack(fill="x", pady=(4, 0))

        cur_lbl = tk.Label(
            ver_frame,
            text=f"เวอร์ชันปัจจุบัน: v{APP_VERSION}",
            font=FONT_TINY,
            bg=T["bg"],
            fg=T["sub"],
        )
        cur_lbl.pack(side="left")

        if is_newer:
            arrow_lbl = tk.Label(
                ver_frame,
                text="  ➜  ",
                font=FONT_TINY,
                bg=T["bg"],
                fg=T["accent"],
            )
            arrow_lbl.pack(side="left")

            new_lbl = tk.Label(
                ver_frame,
                text=f"เวอร์ชันใหม่: {self.info.tag_name}",
                font=FONT_BOLD,
                bg=T["bg"],
                fg=T["accent"],
            )
            new_lbl.pack(side="left")
        else:
            status_tag = tk.Label(
                ver_frame,
                text=f"  (Build ล่าสุด: {self.info.tag_name})",
                font=FONT_TINY,
                bg=T["bg"],
                fg=T["accent"],
            )
            status_tag.pack(side="left")

        # Release Title
        if self.info.title and self.info.title != self.info.tag_name:
            rel_title = tk.Label(
                container,
                text=self.info.title,
                font=FONT_BOLD,
                bg=T["bg"],
                fg=T["fg"],
                anchor="w",
                wraplength=470,
            )
            rel_title.pack(fill="x", pady=(0, 6))

        # Changelog card
        log_card = tk.Frame(
            container,
            bg=T["bg2"],
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground=T["border"],
        )
        log_card.pack(fill="both", expand=True, pady=(0, 14))

        log_hdr = tk.Label(
            log_card,
            text="รายละเอียดการปรับปรุง (Changelog):",
            font=FONT_TINY,
            bg=T["bg2"],
            fg=T["sub"],
            anchor="w",
        )
        log_hdr.pack(fill="x", pady=(0, 4))

        self._text = tk.Text(
            log_card,
            bg=T["bg_ai"],
            fg=T["fg"],
            font=FONT,
            wrap="word",
            relief="flat",
            padx=8,
            pady=6,
            highlightthickness=0,
            height=7,
        )
        scroll = ttk.Scrollbar(log_card, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)

        body_text = self.info.body.strip() if self.info.body else "ไม่มีรายละเอียดบันทึกการเปลี่ยนแปลง"
        self._text.insert("1.0", body_text)
        self._text.configure(state="disabled")

        # Download Progress Area (Hidden initially)
        self._progress_frame = tk.Frame(container, bg=T["bg"])
        self._progress_bar = ttk.Progressbar(self._progress_frame, orient="horizontal", mode="determinate")
        self._progress_bar.pack(fill="x", pady=(0, 4))

        self._status_lbl = tk.Label(
            self._progress_frame,
            text="กำลังเตรียมดาวน์โหลด...",
            font=FONT_TINY,
            bg=T["bg"],
            fg=T["sub"],
            anchor="w",
        )
        self._status_lbl.pack(fill="x")

        # Bottom Action Buttons
        btn_bar = tk.Frame(container, bg=T["bg"])
        btn_bar.pack(fill="x", side="bottom")

        # Left: Skip version button
        self._skip_btn = tk.Button(
            btn_bar,
            text="ข้ามเวอร์ชันนี้",
            bg=T["bg2"],
            fg=T["sub"],
            activebackground=T["bg3"],
            activeforeground=T["fg"],
            font=FONT_TINY,
            relief="flat",
            padx=12,
            pady=5,
            command=self._on_skip,
            cursor="hand2",
        )
        self._skip_btn.pack(side="left")

        # Right buttons: Later & Update Now
        self._later_btn = tk.Button(
            btn_bar,
            text="ไว้ทีหลัง",
            bg=T["bg2"],
            fg=T["fg"],
            activebackground=T["bg3"],
            activeforeground=T["fg"],
            font=FONT,
            relief="flat",
            padx=14,
            pady=5,
            command=self.destroy,
            cursor="hand2",
        )
        self._later_btn.pack(side="right", padx=(8, 0))

        if is_frozen_exe() and self.info.download_url:
            update_text = "⚡ อัปเดตทันที"
            update_cmd = self._on_start_update
        else:
            update_text = "🌐 ดาวน์โหลดบน GitHub"
            update_cmd = self._on_open_browser

        self._update_btn = tk.Button(
            btn_bar,
            text=update_text,
            bg=T["accent"],
            fg="#ffffff" if T["bg"] == "#1e1f20" else "#ffffff",
            activebackground=T["accent_hover"],
            activeforeground="#ffffff",
            font=FONT_BOLD,
            relief="flat",
            padx=18,
            pady=5,
            command=update_cmd,
            cursor="hand2",
        )
        self._update_btn.pack(side="right")

    def _on_skip(self) -> None:
        """Save skipped version to store and close dialog."""
        tag = self.info.tag_name or self.info.version
        if tag:
            self.settings_store.save_skipped_version(tag)
        self.destroy()

    def _on_open_browser(self) -> None:
        """Open release page in default browser."""
        webbrowser.open(self.info.html_url)
        self.destroy()

    def _on_start_update(self) -> None:
        """Begin downloading the executable update in background."""
        if self._is_downloading or not self.info.download_url:
            return
        self._is_downloading = True
        self._update_btn.configure(state="disabled", text="กำลังดาวน์โหลด...")
        self._skip_btn.configure(state="disabled")
        self._later_btn.configure(state="disabled")

        self._progress_frame.pack(fill="x", pady=(0, 14), before=self._skip_btn.master)
        self._progress_bar["value"] = 0

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self) -> None:
        try:
            fd, tmp_path = tempfile.mkstemp(suffix="_MAX_new.exe")
            os.close(fd)
            self._temp_dest = tmp_path

            def _on_progress(downloaded: int, total: int) -> None:
                if total > 0:
                    pct = (downloaded / total) * 100
                    mb_cur = downloaded / (1024 * 1024)
                    mb_tot = total / (1024 * 1024)
                    msg = f"ดาวน์โหลด: {mb_cur:.1f} MB / {mb_tot:.1f} MB ({pct:.0f}%)"
                else:
                    mb_cur = downloaded / (1024 * 1024)
                    pct = 0
                    msg = f"ดาวน์โหลด: {mb_cur:.1f} MB..."

                self.after(0, lambda: self._update_ui_progress(pct, msg))

            if not self.info.download_url:
                raise ValueError("ไม่พบ URL สำหรับดาวน์โหลดไฟล์อัปเดต")

            download_file(self.info.download_url, tmp_path, progress_callback=_on_progress)

            # Ready to apply
            self.after(0, self._on_download_complete)

        except Exception as ex:
            self.after(0, lambda: self._on_download_error(str(ex)))

    def _update_ui_progress(self, pct: float, msg: str) -> None:
        self._progress_bar["value"] = pct
        self._status_lbl.configure(text=msg)

    def _on_download_error(self, err_msg: str) -> None:
        self._is_downloading = False
        self._progress_frame.pack_forget()
        self._update_btn.configure(state="normal", text="ลองอีกครั้ง")
        self._skip_btn.configure(state="normal")
        self._later_btn.configure(state="normal")
        messagebox.showerror("อัปเดตล้มเหลว", f"เกิดข้อผิดพลาดในการดาวน์โหลด:\n{err_msg}", parent=self)

    def _on_download_complete(self) -> None:
        if not self._temp_dest or not os.path.exists(self._temp_dest):
            self._on_download_error("ไม่พบไฟล์ที่ดาวน์โหลด")
            return

        self._status_lbl.configure(text="ดาวน์โหลดเสร็จสิ้น กำลังรีสตาร์ตเพื่อติดตั้ง...")
        self.update()

        try:
            apply_exe_update_and_restart(self._temp_dest)
        except Exception as ex:
            messagebox.showerror(
                "ติดตั้งอัปเดตล้มเหลว",
                f"ไม่สามารถติดตั้งอัปเดตอัตโนมัติ:\n{ex}\n\nกรุณาดาวน์โหลดไฟล์จาก GitHub ด้วยตนเอง",
                parent=self
            )
            webbrowser.open(self.info.html_url)
            self.destroy()
