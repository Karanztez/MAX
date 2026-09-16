"""
settings_dialog.py — Dialog for configuring Provider Profiles, API Keys, and Endpoints.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Optional

try:
    from core.provider_profiles import normalize_profile, normalize_profiles, new_custom_profile, default_profiles
    from core.updater import check_github_release, is_newer_version, APP_VERSION
    from ui.clipboard import read_clipboard_text
    from ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_TITLE
    from ui.widgets.context_menu import attach_text_context_menu
    from ui.dialogs.health_dialog import HealthCheckDialog
    from ui.dialogs.update_dialog import UpdateDialog
except (ImportError, ModuleNotFoundError):
    from src.core.provider_profiles import normalize_profile, normalize_profiles, new_custom_profile, default_profiles  # type: ignore[no-redef]
    from src.core.updater import check_github_release, is_newer_version, APP_VERSION  # type: ignore[no-redef]
    from src.ui.clipboard import read_clipboard_text  # type: ignore[no-redef]
    from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_TITLE  # type: ignore[no-redef]
    from src.ui.widgets.context_menu import attach_text_context_menu  # type: ignore[no-redef]
    from src.ui.dialogs.health_dialog import HealthCheckDialog  # type: ignore[no-redef]
    from src.ui.dialogs.update_dialog import UpdateDialog  # type: ignore[no-redef]


class SettingsDialog(tk.Toplevel):
    MODE_LABELS = {
        "OpenAI Chat Completions": "chat_completions",
        "OpenAI Responses": "responses",
    }

    def __init__(self, parent: tk.Misc, profiles: list[dict[str, Any]], selected_id: str,
                 remembered: bool,
                 on_save: Any) -> None:
        super().__init__(parent)
        self._on_save = on_save
        self._profiles = normalize_profiles(profiles)
        self._loading = False
        self._index = next((i for i, p in enumerate(self._profiles)
                            if p["id"] == selected_id), 0)
        self.title("Settings")
        self.geometry("850x610")
        self.minsize(760, 560)
        self.configure(bg=T["bg"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        body = tk.Frame(self, bg=T["bg"], padx=22, pady=18)
        body.pack(fill="both", expand=True)
        header = tk.Frame(body, bg=T["bg"])
        header.pack(fill="x")
        tk.Label(header, text="Provider Profiles", bg=T["bg"], fg=T["fg"],
                 font=FONT_TITLE).pack(side="left", anchor="w")
        self._save_btn = tk.Button(
            header, text="💾  บันทึก API", command=self._save,
            bg=T["accent"], fg="#ffffff", activebackground=T["accent_hover"],
            activeforeground="#ffffff", relief="flat", font=FONT_BOLD,
            padx=20, pady=8, cursor="hand2",
        )
        self._save_btn.pack(side="right")
        tk.Label(body, text="แยก URL, API key และโมเดลได้หลายชุด เช่น Claude, Gemini, GPT และ Codex",
                 bg=T["bg"], fg=T["fg_dim"], font=FONT_TINY).pack(anchor="w", pady=(3, 14))

        content = tk.Frame(body, bg=T["bg"])
        content.pack(fill="both", expand=True)
        sidebar = tk.Frame(content, bg=T["bg2"], padx=8, pady=8,
                           highlightthickness=1, highlightbackground=T["border"])
        sidebar.pack(side="left", fill="y", padx=(0, 14))
        self._profile_list = tk.Listbox(
            sidebar, width=25, bg=T["bg2"], fg=T["fg"], selectbackground=T["accent"],
            selectforeground="#ffffff", relief="flat", bd=0, highlightthickness=0,
            exportselection=False, font=FONT,
        )
        self._profile_list.pack(fill="both", expand=True)
        self._profile_list.bind("<<ListboxSelect>>", self._select_profile)
        list_actions = tk.Frame(sidebar, bg=T["bg2"])
        list_actions.pack(fill="x", pady=(8, 0))
        tk.Button(list_actions, text="＋", command=self._add_profile, bg=T["bg_btn"], fg=T["fg"],
                  activebackground=T["bg3"], activeforeground=T["fg"], relief="flat",
                  font=FONT_BOLD, cursor="hand2").pack(side="left", fill="x", expand=True)
        tk.Button(list_actions, text="−", command=self._delete_profile, bg=T["bg_btn"], fg=T["err_hdr"],
                  activebackground=T["bg3"], activeforeground=T["fg"], relief="flat",
                  font=FONT_BOLD, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(6, 0))
        tk.Button(sidebar, text="↺ คืนค่า Preset เริ่มต้น", command=self._reset_defaults,
                  bg=T["bg_btn"], fg=T["sub"], activebackground=T["bg3"], activeforeground=T["fg"],
                  relief="flat", font=FONT_TINY, cursor="hand2", pady=4).pack(fill="x", pady=(6, 0))

        editor = tk.Frame(content, bg=T["bg"])
        editor.pack(side="left", fill="both", expand=True)
        self._name_var = tk.StringVar()
        self._url_var = tk.StringVar()
        self._key_var = tk.StringVar()
        self._mode_var = tk.StringVar()
        self._model_var = tk.StringVar()

        self._field(editor, "ชื่อโปรไฟล์", self._name_var)
        self._field(editor, "BASE URL (ลงท้ายที่ /v1)", self._url_var)
        tk.Label(editor, text="API KEY", bg=T["bg"], fg=T["fg_dim"], font=FONT_TINY).pack(anchor="w", pady=(0, 5))
        key_row = tk.Frame(editor, bg=T["bg2"], padx=10, pady=7,
                           highlightthickness=1, highlightbackground=T["border"])
        key_row.pack(fill="x", pady=(0, 10))
        self._key_entry = tk.Entry(key_row, textvariable=self._key_var, show="●", bg=T["bg2"],
                                   fg=T["fg"], insertbackground=T["fg"], relief="flat", bd=0, font=FONT)
        self._key_entry.pack(side="left", fill="x", expand=True)
        attach_text_context_menu(self._key_entry, is_editable=True, on_paste=lambda _e: self._paste_key())
        self._key_entry.bind("<Control-v>", self._paste_key)
        self._key_entry.bind("<Control-V>", self._paste_key)
        self._key_entry.bind("<Control-KeyPress>", self._key_control_shortcut)
        self._key_entry.bind("<Shift-Insert>", self._paste_key)
        self._showing = False
        self._paste_btn = tk.Button(key_row, text="⎘", command=self._paste_key,
                                    bg=T["bg2"], fg=T["accent"], activebackground=T["bg3"],
                                    activeforeground=T["fg"], relief="flat", bd=0,
                                    font=("Segoe UI Symbol", 12), cursor="hand2")
        self._paste_btn.pack(side="right", padx=(8, 0))
        self._eye_btn = tk.Button(key_row, text="◉", command=self._toggle_key,
                                  bg=T["bg2"], fg=T["fg_dim"], activebackground=T["bg3"],
                                  activeforeground=T["fg"], relief="flat", bd=0,
                                  font=("Segoe UI Symbol", 12), cursor="hand2")
        self._eye_btn.pack(side="right", padx=(8, 0))

        tk.Label(editor, text="รูปแบบ API", bg=T["bg"], fg=T["fg_dim"], font=FONT_TINY).pack(anchor="w", pady=(0, 5))
        self._mode_box = ttk.Combobox(editor, textvariable=self._mode_var,
                                      values=list(self.MODE_LABELS), state="readonly", font=FONT)
        self._mode_box.pack(fill="x", pady=(0, 10))
        self._field(editor, "โมเดลที่เลือก", self._model_var)
        tk.Label(editor, text="รายการโมเดล (หนึ่งชื่อต่อบรรทัด หรือคั่นด้วย comma)",
                 bg=T["bg"], fg=T["fg_dim"], font=FONT_TINY).pack(anchor="w", pady=(0, 5))
        self._models_text = tk.Text(editor, height=6, bg=T["bg2"], fg=T["fg"],
                                    insertbackground=T["fg"], relief="flat", bd=0,
                                    highlightthickness=1, highlightbackground=T["border"], font=FONT)
        self._models_text.pack(fill="both", expand=True)

        self._remember_var = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text="บันทึก API key ลงเครื่องนี้ (เข้ารหัส)", variable=self._remember_var,
                       bg=T["bg"], fg=T["fg"], activebackground=T["bg"],
                       activeforeground=T["fg"], selectcolor=T["bg3"],
                       font=FONT, cursor="hand2").pack(anchor="w", pady=(12, 0))

        footer = tk.Frame(body, bg=T["bg"])
        footer.pack(fill="x", side="bottom", pady=(12, 0))
        self._save_status_var = tk.StringVar(value="")
        tk.Label(footer, textvariable=self._save_status_var, bg=T["bg"], fg=T["ai_hdr"],
                 font=FONT_TINY).pack(side="left")

        self._update_check_btn = tk.Button(
            footer, text=f"🔄 ตรวจหาอัปเดต (v{APP_VERSION})", command=self._check_updates_click,
            bg=T["bg2"], fg=T["sub"], activebackground=T["bg3"], activeforeground=T["fg"],
            relief="flat", font=FONT_TINY, padx=10, pady=5, cursor="hand2"
        )
        self._update_check_btn.pack(side="left", padx=(10, 0))

        self._health_check_btn = tk.Button(
            footer, text="⚡ เช็คสถานะ API", command=self._open_health_check,
            bg=T["bg2"], fg=T["accent"], activebackground=T["bg3"], activeforeground=T["accent_hover"],
            relief="flat", font=FONT_TINY, padx=10, pady=5, cursor="hand2"
        )
        self._health_check_btn.pack(side="left", padx=(10, 0))

        tk.Button(footer, text="ยกเลิก", command=self.destroy, bg=T["bg_btn"], fg=T["fg"],
                  activebackground=T["bg3"], activeforeground=T["fg"], relief="flat",
                  font=FONT, padx=14, pady=7, cursor="hand2").pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Control-s>", lambda _e: self._save() or "break")
        self.bind("<Control-S>", lambda _e: self._save() or "break")
        self.bind("<Control-KeyPress>", self._window_control_shortcut)
        self._refresh_list()

    def _open_health_check(self) -> None:
        self._commit_editor()
        selected_id = self._profiles[self._index]["id"]
        HealthCheckDialog(self, self._profiles, selected_id)

    def _check_updates_click(self) -> None:
        parent = self.master
        if hasattr(parent, "check_updates_manual"):
            parent.check_updates_manual()
        else:
            info = check_github_release()
            if info and is_newer_version(info.tag_name, APP_VERSION):
                UpdateDialog(self, info)
            else:
                messagebox.showinfo("อัปเดต MAX", f"คุณกำลังใช้งาน MAX เวอร์ชันล่าสุด (v{APP_VERSION}) แล้ว", parent=self)


    def _field(self, parent: tk.Misc, label: str, variable: tk.StringVar) -> None:
        tk.Label(parent, text=label, bg=T["bg"], fg=T["fg_dim"], font=FONT_TINY).pack(anchor="w", pady=(0, 5))
        ent = tk.Entry(parent, textvariable=variable, bg=T["bg2"], fg=T["fg"],
                       insertbackground=T["fg"], relief="flat", bd=0,
                       highlightthickness=1, highlightbackground=T["border"],
                       font=FONT)
        ent.pack(fill="x", ipady=7, pady=(0, 10))
        attach_text_context_menu(ent, is_editable=True)

    def _refresh_list(self) -> None:
        self._loading = True
        self._profile_list.delete(0, tk.END)
        for profile in self._profiles:
            self._profile_list.insert(tk.END, profile["name"])
        self._index = min(max(self._index, 0), len(self._profiles) - 1)
        self._profile_list.selection_set(self._index)
        self._profile_list.activate(self._index)
        self._load_editor(self._index)
        self._loading = False

    def _load_editor(self, index: int) -> None:
        profile = self._profiles[index]
        self._name_var.set(profile["name"])
        self._url_var.set(profile["base_url"])
        self._key_var.set(profile["api_key"])
        label = next((name for name, mode in self.MODE_LABELS.items()
                      if mode == profile["api_mode"]), "OpenAI Chat Completions")
        self._mode_var.set(label)
        self._model_var.set(profile["model"])
        self._models_text.delete("1.0", tk.END)
        self._models_text.insert("1.0", "\n".join(profile["models"]))

    def _commit_editor(self) -> None:
        if not self._profiles:
            return
        profile = dict(self._profiles[self._index])
        profile.update({
            "name": self._name_var.get(), "base_url": self._url_var.get(),
            "api_key": self._key_var.get(),
            "api_mode": self.MODE_LABELS.get(self._mode_var.get(), "chat_completions"),
            "model": self._model_var.get(), "models": self._models_text.get("1.0", tk.END),
        })
        self._profiles[self._index] = normalize_profile(profile)

    def _select_profile(self, _event: object = None) -> None:
        if self._loading:
            return
        selected = self._profile_list.curselection()
        if not selected or selected[0] == self._index:
            return
        self._commit_editor()
        self._index = selected[0]
        self._load_editor(self._index)

    def _add_profile(self) -> None:
        self._commit_editor()
        self._profiles.append(new_custom_profile(len(self._profiles) + 1))
        self._index = len(self._profiles) - 1
        self._refresh_list()

    def _delete_profile(self) -> None:
        if len(self._profiles) <= 1:
            return
        self._profiles.pop(self._index)
        self._index = min(self._index, len(self._profiles) - 1)
        self._refresh_list()

    def _reset_defaults(self) -> None:
        """Reset profiles to standard official presets while preserving entered API keys."""
        from copy import deepcopy
        defaults = default_profiles()
        existing_keys = {p.get("id"): p.get("api_key", "") for p in self._profiles if p.get("api_key")}
        existing_keys.update({str(p.get("base_url")).strip().rstrip("/"): p.get("api_key", "") for p in self._profiles if p.get("api_key")})

        new_profiles = deepcopy(defaults)
        for p in new_profiles:
            if p.get("id") in existing_keys:
                p["api_key"] = existing_keys[p["id"]]
            elif str(p.get("base_url")).strip().rstrip("/") in existing_keys:
                p["api_key"] = existing_keys[str(p.get("base_url")).strip().rstrip("/")]

        self._profiles = new_profiles
        self._index = 0
        self._refresh_list()
        messagebox.showinfo("คืนค่า Preset สำเร็จ", "โหลดโปรไฟล์เริ่มต้นครบทุก Pool (Chinese Specials, Grok Heavy, Claude Cursor, Claude Antigravity, Gemini, OpenAI) แล้ว", parent=self)

    def _toggle_key(self) -> None:
        self._showing = not self._showing
        self._key_entry.configure(show="" if self._showing else "●")
        self._eye_btn.configure(text="◌" if self._showing else "◉")

    def _paste_key(self, _event: object = None) -> str:
        """Paste clipboard text into the masked API-key entry reliably."""
        value = read_clipboard_text(self)
        if value is None:
            self.bell()
            return "break"
        try:
            self._key_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
        self._key_entry.insert(tk.INSERT, value.strip())
        self._key_entry.icursor(tk.END)
        self._key_entry.focus_set()
        return "break"

    def _key_control_shortcut(self, event: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        if getattr(event, "keycode", 0) == 86 or str(getattr(event, "keysym", "")).lower() == "v":
            return self._paste_key(event)
        return None

    def _window_control_shortcut(self, event: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        if getattr(event, "keycode", 0) == 83 or str(getattr(event, "keysym", "")).lower() == "s":
            self._save()
            return "break"
        return None

    def _save(self) -> None:
        self._commit_editor()
        selected_id = self._profiles[self._index]["id"]
        active = self._profiles[self._index]
        if not active["base_url"] or not active["model"]:
            self._save_status_var.set("กรุณากรอก Base URL และโมเดล")
            return
        self._save_btn.configure(state="disabled", text="กำลังบันทึก…")
        try:
            saved = self._on_save(self._profiles, selected_id, self._remember_var.get())
        except Exception as ex:
            saved = False
            messagebox.showerror("บันทึก API ไม่สำเร็จ", str(ex), parent=self)
        if saved is False:
            self._save_btn.configure(state="normal", text="บันทึก API")
            self._save_status_var.set("บันทึกไม่สำเร็จ")
            return
        self._save_status_var.set("บันทึก API แล้ว ✓")
        self.after(450, self.destroy)
