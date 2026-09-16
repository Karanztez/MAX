"""
src/ui/main_window.py — MaxPlus AI Main Window and Application Runner
"""

import importlib
import os
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Optional

try:
    from PIL import Image, ImageTk, ImageGrab, ImageDraw, ImageFont  # type: ignore[import-untyped]
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    pystray = importlib.import_module("pystray")
    _TRAY_OK = True
except (ImportError, Exception):
    pystray = None
    _TRAY_OK = False

try:
    from core.provider_profiles import default_profiles, normalize_profiles
    from core.settings_store import SettingsStore
    from core.mcp_manager import MCPManager
    from core.updater import check_github_release, is_newer_version, APP_VERSION, UpdateInfo
    from ui.themes import T, DARK, LIGHT, FONT, FONT_TINY, FONT_TITLE, FONT_HDR
    from ui.chat_tab import ChatTab
    from ui.tabs.media_tab import MediaViewerTab
    from ui.tabs.team_room_tab import AgentTeamTab
    from ui.capture.screen_crop import ScreenCropOverlay
    from ui.dialogs.settings_dialog import SettingsDialog
    from ui.dialogs.mcp_dialog import MCPManagerDialog
    from ui.dialogs.update_dialog import UpdateDialog
    from ui.dialogs.health_dialog import HealthCheckDialog
    from core.mcp.builtins.workspace_tools import set_workspace_ui_dispatcher
except (ImportError, ModuleNotFoundError):
    from src.core.provider_profiles import default_profiles, normalize_profiles  # type: ignore[no-redef]
    from src.core.settings_store import SettingsStore  # type: ignore[no-redef]
    from src.core.mcp_manager import MCPManager  # type: ignore[no-redef]
    from src.core.updater import check_github_release, is_newer_version, APP_VERSION, UpdateInfo  # type: ignore[no-redef]
    from src.ui.themes import T, DARK, LIGHT, FONT, FONT_TINY, FONT_TITLE, FONT_HDR  # type: ignore[no-redef]
    from src.ui.chat_tab import ChatTab  # type: ignore[no-redef]
    from src.ui.tabs.media_tab import MediaViewerTab  # type: ignore[no-redef]
    from src.ui.tabs.team_room_tab import AgentTeamTab  # type: ignore[no-redef]
    from src.ui.capture.screen_crop import ScreenCropOverlay  # type: ignore[no-redef]
    from src.ui.dialogs.settings_dialog import SettingsDialog  # type: ignore[no-redef]
    from src.ui.dialogs.mcp_dialog import MCPManagerDialog  # type: ignore[no-redef]
    from src.ui.dialogs.update_dialog import UpdateDialog  # type: ignore[no-redef]
    from src.ui.dialogs.health_dialog import HealthCheckDialog  # type: ignore[no-redef]
    from src.core.mcp.builtins.workspace_tools import set_workspace_ui_dispatcher  # type: ignore[no-redef]



def _project_name() -> str:
    """ดึงชื่อโปรเจกต์จาก CWD"""
    return os.path.basename(os.path.abspath(os.getcwd()))


class MaxPlusGUI(tk.Tk):
    _is_dark: bool = True
    _tabs: list[Any]

    def __init__(self) -> None:
        super().__init__()
        self.project_path = os.path.abspath(os.getcwd())
        self.project_name = os.path.basename(self.project_path)
        self.title(f"MAX v{APP_VERSION}")
        self.geometry("1100x800")
        self.configure(bg=T["bg"])
        self.resizable(True, True)
        self.minsize(700, 540)
        self._tabs = []
        self._snipping = False
        self._last_capture_request = 0.0
        self._global_last_c = 0.0
        self._key_c_down = False
        self._key_a_down = False
        self._tray = None
        self._tray_queue: queue.Queue[str] = queue.Queue()
        self.settings_store = SettingsStore()
        self.mcp_manager = MCPManager()
        set_workspace_ui_dispatcher(self._handle_workspace_tool)
        self.profiles, self.selected_profile_id = self.settings_store.load_provider_settings(default_profiles())
        self.api_key = self._active_profile()["api_key"]
        self._changing_provider = False
        self._load_app_icon()
        self._build_ui()
        self._new_tab()   # open first tab
        self.bind("<Control-v>", self._route_paste)
        self.bind("<Control-V>", self._route_paste)
        self.bind("<Control-c>", self._route_ctrl_c)
        self.bind("<Control-C>", self._route_ctrl_c)
        self.bind("<Control-a>", self._route_ctrl_a)
        self.bind("<Control-A>", self._route_ctrl_a)
        self.bind("<Control-Alt-a>", lambda _e: self._start_screen_capture() or "break")
        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self._setup_tray()
        self.after(40, self._poll_global_shortcut)
        self.after(100, self._poll_tray_queue)
        threading.Thread(target=self._check_update_background, daemon=True).start()

    def _get_asset_path(self, rel_path: str) -> str:
        import sys
        base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        return os.path.join(base, rel_path)

    def _load_app_icon(self) -> None:
        self._app_icon_img = None
        self._app_icon_photo = None
        self._header_logo_photo = None
        if not _PIL_OK:
            return
        try:
            # 1. App icon & Taskbar icon (from max_icon.png or icon.png)
            icon_path = None
            for cand in ["max_icon.png", "icon.png", "feather.png"]:
                p = self._get_asset_path(os.path.join("src", "assets", cand))
                if os.path.exists(p):
                    icon_path = p
                    break
                p_root = self._get_asset_path(cand)
                if os.path.exists(p_root):
                    icon_path = p_root
                    break

            if icon_path and os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA")
                self._app_icon_img = img
                self._app_icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._app_icon_photo)  # type: ignore

            # 2. Header logo (from max_logo.png or max_icon.png)
            logo_path = None
            for cand in ["max_logo.png", "max_icon.png", "icon.png"]:
                p = self._get_asset_path(os.path.join("src", "assets", cand))
                if os.path.exists(p):
                    logo_path = p
                    break

            if logo_path and os.path.exists(logo_path):
                logo_img = Image.open(logo_path).convert("RGBA")
                # Scale smoothly to 26px height preserving aspect ratio
                aspect = logo_img.width / max(1, logo_img.height)
                target_h = 24
                target_w = max(16, int(target_h * aspect))
                logo_resized = logo_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                self._header_logo_photo = ImageTk.PhotoImage(logo_resized)

            # 3. Windows ICO for taskbar/titlebar
            icon_ico = self._get_asset_path(os.path.join("src", "assets", "icon.ico"))
            if not os.path.exists(icon_ico):
                icon_ico = self._get_asset_path("icon.ico")
            if os.path.exists(icon_ico):
                try:
                    self.iconbitmap(icon_ico)
                except Exception:
                    pass
        except Exception:
            pass


    def _choose_project_folder(self) -> None:
        chosen = filedialog.askdirectory(
            initialdir=self.project_path,
            title="เลือกโฟลเดอร์โปรเจกต์ (Select Working Project Directory)"
        )
        if chosen:
            self.project_path = os.path.abspath(chosen)
            self.project_name = os.path.basename(self.project_path)
            self.title(f"MAX v{APP_VERSION}")
            self._proj_btn.configure(text=f"📁 {self.project_name}")
            tab = self._current_tab()
            if tab is not None:
                tab.status_var.set(f"สลับโปรเจกต์: {self.project_name} ({self.project_path})")

    # ── top toolbar ────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        # Compact unified toolbar
        self._toolbar = tk.Frame(self, bg=T["bg"], pady=6)
        self._toolbar.pack(fill="x", padx=14)

        # Left: App title + Interactive Project folder picker + Tab controls
        self._toolbar_left = tk.Frame(self._toolbar, bg=T["bg"])
        self._toolbar_left.pack(side="left")

        if self._header_logo_photo is not None:
            self._logo_lbl = tk.Label(self._toolbar_left, image=self._header_logo_photo, bg=T["bg"])
            self._logo_lbl.pack(side="left", padx=(0, 10))
            self._title_lbl = None
        else:
            self._logo_lbl = None
            self._title_lbl = tk.Label(self._toolbar_left, text="🪶 MAX",
                                       bg=T["bg"], fg=T["fg"], font=FONT_HDR)
            self._title_lbl.pack(side="left", padx=(0, 8))

        self._proj_btn = tk.Button(
            self._toolbar_left, text=f"📁 {self.project_name}",
            bg=T["bg2"], fg=T["accent"], activebackground=T["bg3"], activeforeground=T["accent_hover"],
            font=FONT_TINY, relief="flat", padx=8, pady=3,
            command=self._choose_project_folder, cursor="hand2"
        )
        self._proj_btn.pack(side="left", padx=(0, 8))

        self._add_tab_btn = tk.Button(
            self._toolbar_left, text="＋",
            bg=T["bg2"], fg=T["fg"], activebackground=T["bg3"], activeforeground=T["fg"],
            font=FONT_TINY, relief="flat", padx=7, pady=2,
            command=self._new_tab, cursor="hand2"
        )
        self._add_tab_btn.pack(side="left", padx=(0, 2))

        self._close_tab_btn = tk.Button(
            self._toolbar_left, text="✕",
            bg=T["bg2"], fg=T["err_hdr"], activebackground=T["bg3"], activeforeground=T["err_hdr"],
            font=FONT_TINY, relief="flat", padx=7, pady=2,
            command=self._close_tab, cursor="hand2"
        )
        self._close_tab_btn.pack(side="left", padx=(0, 6))

        self._team_btn = tk.Button(
            self._toolbar_left, text="👥 Team Room",
            bg=T["bg2"], fg=T["accent"], activebackground=T["bg3"], activeforeground=T["accent_hover"],
            font=FONT_TINY, relief="flat", padx=8, pady=2,
            command=self._new_team_room_tab, cursor="hand2"
        )
        self._team_btn.pack(side="left")

        # Right: Provider & Model Comboboxes + Action buttons
        self._toolbar_right = tk.Frame(self._toolbar, bg=T["bg"])
        self._toolbar_right.pack(side="right")

        self._theme_btn = tk.Button(
            self._toolbar_right, text="☀" if self._is_dark else "🌙",
            bg=T["bg2"], fg=T["fg"], activebackground=T["bg3"], activeforeground=T["fg"],
            font=FONT_TINY, relief="flat", padx=8, pady=3,
            command=self._toggle_theme, cursor="hand2"
        )
        self._theme_btn.pack(side="right", padx=(4, 0))

        self._settings_btn = tk.Button(
            self._toolbar_right, text="⚙", bg=T["bg2"], fg=T["fg"],
            activebackground=T["bg3"], activeforeground=T["fg"],
            font=("Segoe UI Symbol", 11), relief="flat", padx=8, pady=2,
            command=self._open_settings, cursor="hand2",
        )
        self._settings_btn.pack(side="right", padx=(4, 0))

        self._mcp_btn = tk.Button(
            self._toolbar_right, text="🛠 MCP", bg=T["bg2"], fg=T["fg"],
            activebackground=T["bg3"], activeforeground=T["fg"],
            font=FONT_TINY, relief="flat", padx=8, pady=3,
            command=self._open_mcp_manager, cursor="hand2",
        )
        self._mcp_btn.pack(side="right", padx=(4, 0))

        self._health_btn = tk.Button(
            self._toolbar_right, text="⚡ เช็คสถานะ", bg=T["bg2"], fg=T["accent"],
            activebackground=T["bg3"], activeforeground=T["accent_hover"],
            font=FONT_TINY, relief="flat", padx=8, pady=3,
            command=self._open_health_check, cursor="hand2",
        )
        self._health_btn.pack(side="right", padx=(4, 0))

        active = self._active_profile()
        self.model_var = tk.StringVar(value=active["model"])
        self._model_box = ttk.Combobox(self._toolbar_right, textvariable=self.model_var,
                                       values=active["models"],
                                       width=18, state="readonly", font=FONT_TINY)
        self._model_box.pack(side="right", padx=(4, 0))
        self.model_var.trace_add("write", self._on_model_change)

        self.provider_var = tk.StringVar(value=active["name"])
        self._provider_box = ttk.Combobox(self._toolbar_right, textvariable=self.provider_var,
                                          values=[p["name"] for p in self.profiles], width=16,
                                          state="readonly", font=FONT_TINY)
        self._provider_box.pack(side="right")
        self.provider_var.trace_add("write", self._on_provider_change)

        # Style & Notebook
        style = ttk.Style(self)
        self._apply_notebook_style(style)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_switched)

    # ── tabs ───────────────────────────────────────────────────────────────
    def _new_tab(self) -> None:
        chat_count = sum(1 for t in self._tabs if isinstance(t, ChatTab)) + 1
        profile = self._active_profile()
        tab = ChatTab(self.notebook, tab_name=f"Chat {chat_count}", api_key=profile["api_key"],
                      base_url=profile["base_url"], model=profile["model"],
                      api_mode=profile["api_mode"],
                      profile_id=profile["id"], profile_name=profile["name"])
        self._tabs.append(tab)
        self.notebook.add(tab, text=f"  Chat {chat_count}  ")
        self.notebook.select(tab)

    def _new_team_room_tab(self) -> None:
        team_count = sum(1 for t in self._tabs if isinstance(t, AgentTeamTab)) + 1
        tab_title = f"👥 Team {team_count}" if team_count > 1 else "👥 Team Room"
        tab = AgentTeamTab(
            self.notebook,
            tab_name=tab_title,
            profiles=self.profiles,
            default_profile_id=self.selected_profile_id,
        )
        self._tabs.append(tab)
        self.notebook.add(tab, text=f" {tab_title} ")
        self.notebook.select(tab)

    def _handle_workspace_tool(self, action: str, args: dict[str, Any]) -> str:
        """Handle AI requests to create a new Tab or Team Room with explicit user confirmation."""
        result_holder: list[str] = []
        done_event = threading.Event()

        def _gui_action() -> None:
            try:
                if action == "create_chat_tab":
                    tab_name = str(args.get("tab_name") or "New Chat").strip()
                    reason = str(args.get("reason") or "แยกเซสชันการทำงาน").strip()
                    sys_prompt = str(args.get("system_prompt") or "").strip()

                    # 1. Ask explicit user confirmation
                    allowed = messagebox.askyesno(
                        "AI ขออนุญาตสร้างแท็บใหม่",
                        f"🤖 AI ต้องการสร้างแท็บสนทนาใหม่: '{tab_name}'\n"
                        f"📌 เหตุผล: {reason}\n\n"
                        f"คุณอนุญาตให้สร้างแท็บนี้หรือไม่?\n"
                        f"(หลังจากสร้าง ระบบจะเลือกแท็บนี้ให้คุณตั้งค่าผู้ให้บริการและโมเดลเอง)",
                        parent=self,
                    )
                    if not allowed:
                        result_holder.append(f"ผู้ใช้ไม่อนุญาตให้สร้างแท็บ '{tab_name}'")
                        return

                    # 2. Create tab
                    profile = self._active_profile()
                    chat_count = sum(1 for t in self._tabs if isinstance(t, ChatTab)) + 1
                    actual_name = tab_name if tab_name else f"Chat {chat_count}"
                    tab = ChatTab(
                        self.notebook,
                        tab_name=actual_name,
                        api_key=profile["api_key"],
                        base_url=profile["base_url"],
                        model=profile["model"],
                        api_mode=profile["api_mode"],
                        profile_id=profile["id"],
                        profile_name=profile["name"],
                    )
                    if sys_prompt:
                        tab.sys_entry.delete(0, "end")
                        tab.sys_entry.insert(0, sys_prompt)

                    self._tabs.append(tab)
                    self.notebook.add(tab, text=f"  {actual_name}  ")
                    self.notebook.select(tab)

                    tab.status_var.set("สร้างแท็บตามคำขอแล้ว — กรุณาเลือกผู้ให้บริการและโมเดลด้านบนตามต้องการ")
                    result_holder.append(
                        f"สร้างแท็บ '{actual_name}' สำเร็จแล้ว และเปิดให้ผู้ใช้เลือกผู้ให้บริการและโมเดลสำหรับแท็บนี้ด้วยตนเองเรียบร้อยแล้ว"
                    )

                elif action == "create_team_room":
                    team_name = str(args.get("team_name") or "👥 Team Room").strip()
                    reason = str(args.get("reason") or "ระดมทีม AI ช่วยงาน").strip()
                    goal = str(args.get("goal") or "").strip()

                    # 1. Ask explicit user confirmation
                    allowed = messagebox.askyesno(
                        "AI ขออนุญาตสร้างห้องทีม AI",
                        f"🤖 AI ต้องการสร้างห้องทีม (Multi-Agent Team Room): '{team_name}'\n"
                        f"📌 เหตุผล/เป้าหมาย: {reason}\n\n"
                        f"คุณอนุญาตให้สร้างห้องทีมนี้หรือไม่?\n"
                        f"(ระบบจะเปิดหน้าต่างตั้งค่าสมาชิก เพื่อให้คุณเลือกผู้ให้บริการและโมเดลของแต่ละบทบาทด้วยตนเอง)",
                        parent=self,
                    )
                    if not allowed:
                        result_holder.append(f"ผู้ใช้ไม่อนุญาตให้สร้างห้องทีม '{team_name}'")
                        return

                    # 2. Create Team Room tab
                    team_count = sum(1 for t in self._tabs if isinstance(t, AgentTeamTab)) + 1
                    actual_name = team_name if team_name else f"👥 Team {team_count}"
                    tab = AgentTeamTab(
                        self.notebook,
                        tab_name=actual_name,
                        profiles=self.profiles,
                        default_profile_id=self.selected_profile_id,
                    )
                    if goal and hasattr(tab, "entry"):
                        tab.entry.insert(0, goal)

                    self._tabs.append(tab)
                    self.notebook.add(tab, text=f" {actual_name} ")
                    self.notebook.select(tab)

                    # Open team configuration dialog so user configures models/providers themselves!
                    tab._open_team_config()

                    result_holder.append(
                        f"สร้างห้องทีม '{actual_name}' สำเร็จ และเปิดหน้าต่างให้ผู้ใช้ตั้งค่าสมาชิก/ผู้ให้บริการ/โมเดลเรียบร้อยแล้ว"
                    )
                else:
                    result_holder.append(f"Unknown workspace tool action: {action}")
            except Exception as ex:
                result_holder.append(f"เกิดข้อผิดพลาดในการสร้างแท็บหรือห้องทีม: {ex}")
            finally:
                done_event.set()

        self.after(0, _gui_action)
        # Wait for user confirmation in modal
        done_event.wait(timeout=120)
        return result_holder[0] if result_holder else "การดำเนินการหมดเวลา (ผู้ใช้ยังไม่ได้ตอบรับ)"

    def _on_tab_switched(self, _event: object = None) -> None:
        tab = self._current_tab()
        if tab is None:
            return
        # Sync top-bar provider & model comboboxes to reflect this tab's independent settings
        profile = next((p for p in self.profiles if p["id"] == getattr(tab, "profile_id", "")), None)
        if not profile:
            profile = self._active_profile()
        self._changing_provider = True
        self.selected_profile_id = profile["id"]
        self.provider_var.set(profile["name"])
        self._model_box.configure(values=profile["models"])
        self.model_var.set(tab.ai.model)
        self._changing_provider = False

    def open_media_tab(
        self,
        file_path: str,
        title: Optional[str] = None,
        media_type: str = "image",
        prompt: str = "",
    ) -> Optional[MediaViewerTab]:
        """Open a dedicated viewer tab for an image or video."""
        if not file_path or not os.path.exists(file_path):
            return None

        resolved_path = str(Path(file_path).resolve())
        compare_key = resolved_path.lower() if sys.platform == "win32" else resolved_path
        for t in self._tabs:
            tab_path = getattr(t, "file_path", None)
            if tab_path:
                tab_resolved = str(Path(tab_path).resolve())
                if (tab_resolved.lower() if sys.platform == "win32" else tab_resolved) == compare_key:
                    self.notebook.select(t)
                    return t

        def _on_close_media(m_tab: MediaViewerTab) -> None:
            if m_tab in self._tabs:
                idx = self._tabs.index(m_tab)
                self.notebook.forget(idx)
                self._tabs.remove(m_tab)
                m_tab.destroy()

        tab = MediaViewerTab(
            self.notebook,
            file_path=resolved_path,
            title=title,
            media_type=media_type,
            prompt=prompt,
            on_close=_on_close_media,
        )
        self._tabs.append(tab)

        base_name = os.path.basename(resolved_path)
        icon = "🎨" if media_type == "image" else "🎬"
        tab_label = f" {icon} {base_name[:18]} "

        self.notebook.add(tab, text=tab_label)
        self.notebook.select(tab)
        return tab

    def _close_tab(self) -> None:
        if len(self._tabs) <= 1:
            return   # เหลืออย่างน้อย 1 แท็บ
        try:
            idx = self.notebook.index("current")
            closed_tab = self._tabs[idx]
        except Exception:
            return

        self.notebook.forget(idx)
        self._tabs.pop(idx)
        closed_tab.destroy()

        # Rename only remaining ChatTabs to keep numbering consistent
        chat_idx = 1
        for t in self._tabs:
            if isinstance(t, ChatTab):
                self.notebook.tab(t, text=f"  Chat {chat_idx}  ")
                chat_idx += 1

    def _current_tab(self) -> Optional[ChatTab]:
        try:
            idx = self.notebook.index("current")
            t = self._tabs[idx]
            return t if isinstance(t, ChatTab) else None
        except Exception:
            return None

    def _route_paste(self, event: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        tab = self._current_tab()
        if tab is None:
            return None
        # Editable widgets other than the composer keep their normal native paste.
        # The composer has its own binding, which runs before this toplevel binding.
        widget = getattr(event, "widget", None)
        if widget is tab.entry:
            return None
        if isinstance(widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)):
            return None
        return tab._on_paste(event)

    def _route_ctrl_c(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        tab = self._current_tab()
        if tab is not None:
            tab._last_ctrl_c = time.monotonic()

    def _route_ctrl_a(self, _event: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        tab = self._current_tab()
        if tab is not None and time.monotonic() - tab._last_ctrl_c <= 1.4:
            tab._last_ctrl_c = 0.0
            self._start_screen_capture()
            return "break"
        return None

    # ── API settings ──────────────────────────────────────────────────────
    def _active_profile(self) -> dict[str, Any]:
        return next((p for p in self.profiles if p["id"] == self.selected_profile_id),
                    self.profiles[0])

    def _apply_active_profile(self) -> None:
        profile = self._active_profile()
        self.api_key = profile["api_key"]
        for tab in self._tabs:
            if isinstance(tab, ChatTab):
                tab.ai.api_key = profile["api_key"]
                tab.ai.base_url = profile["base_url"].rstrip("/")
                tab.ai.api_mode = profile["api_mode"]
                tab.ai.model = profile["model"]

    def _open_settings(self) -> None:
        SettingsDialog(self, self.profiles, self.selected_profile_id,
                       self.settings_store.has_saved_key(), self._save_api_settings)

    def _open_mcp_manager(self) -> None:
        MCPManagerDialog(self, self.mcp_manager, on_update=self._on_mcp_updated)

    def _open_health_check(self) -> None:
        HealthCheckDialog(self, self.profiles, self.selected_profile_id)

    def _on_mcp_updated(self) -> None:
        count = len(self.mcp_manager.get_all_tools())
        state_str = f"Tools: {count}" if self.mcp_manager.enabled else "Tools: ปิด"
        tab = self._current_tab()
        if tab:
            tab.status_var.set(f"MCP {state_str}")

    def _save_api_settings(self, profiles: list[dict[str, Any]], selected_id: str,
                           remember: bool) -> bool:
        self.profiles = normalize_profiles(profiles)
        self.selected_profile_id = selected_id
        if not any(p["id"] == selected_id for p in self.profiles):
            self.selected_profile_id = self.profiles[0]["id"]
        profile = self._active_profile()
        self._changing_provider = True
        self.provider_var.set(profile["name"])
        self._provider_box.configure(values=[p["name"] for p in self.profiles])
        self._model_box.configure(values=profile["models"])
        self.model_var.set(profile["model"])
        self._changing_provider = False
        self._apply_active_profile()
        try:
            self.settings_store.save_provider_settings(self.profiles, self.selected_profile_id, remember)
        except Exception as ex:
            tab = self._current_tab()
            if tab is not None:
                tab.status_var.set(f"ใช้โปรไฟล์ใน session นี้แล้ว แต่จดจำไม่ได้: {ex}")
            messagebox.showerror("บันทึก API ไม่สำเร็จ",
                                 f"ใช้ key ใน session นี้ได้ แต่บันทึกลงเครื่องไม่สำเร็จ:\n{ex}",
                                 parent=self)
            return False
        for tab in self._tabs:
            suffix = " · บันทึกลงเครื่องแล้ว" if remember else " · ใช้เฉพาะ session นี้"
            tab.status_var.set(f"ใช้ {profile['name']} · {profile['model']}{suffix}")
        return True

    # ── screen capture + background mode ─────────────────────────────────
    def _start_screen_capture(self) -> None:
        now = time.monotonic()
        if self._snipping or now - self._last_capture_request < 0.6:
            return
        if not _PIL_OK:
            tab = self._current_tab()
            if tab is not None:
                tab.status_var.set("ไม่พบ Pillow จึงยังจับภาพหน้าจอไม่ได้")
            return
        self._snipping = True
        self._last_capture_request = now
        self._was_visible_before_snip = self.state() != "withdrawn"
        self.withdraw()
        self.update_idletasks()
        try:
            import ctypes
            ctypes.windll.dwmapi.DwmFlush()
        except Exception:
            pass
        # Let the desktop compositor repaint the area previously occupied by
        # this window before taking the screenshot.
        self.after(500, self._capture_screen)

    def _capture_screen(self) -> None:
        try:
            try:
                import ctypes
                ctypes.windll.dwmapi.DwmFlush()
            except Exception:
                pass
            screenshot = ImageGrab.grab()
            ScreenCropOverlay(self, screenshot, self._screen_crop_done, self._screen_crop_cancelled)
        except Exception as ex:
            self._snipping = False
            self._show_window()
            tab = self._current_tab()
            if tab is not None:
                tab.status_var.set(f"จับภาพหน้าจอไม่สำเร็จ: {ex}")

    def _screen_crop_done(self, image: "Image.Image") -> None:
        self._snipping = False
        self._show_window()
        tab = self._current_tab()
        if tab is not None:
            tab._set_cropped_img(image)

    def _screen_crop_cancelled(self) -> None:
        self._snipping = False
        if getattr(self, "_was_visible_before_snip", True):
            self._show_window()

    def _poll_global_shortcut(self) -> None:
        """Detect Ctrl+C then Ctrl+A globally, plus the direct Ctrl+Alt+A hotkey."""
        try:
            import ctypes
            key = ctypes.windll.user32.GetAsyncKeyState
            ctrl = bool(key(0x11) & 0x8000)
            alt = bool(key(0x12) & 0x8000)
            c_down = bool(key(0x43) & 0x8000)
            a_down = bool(key(0x41) & 0x8000)
            if ctrl and c_down and not self._key_c_down:
                self._global_last_c = time.monotonic()
            if ctrl and a_down and not self._key_a_down:
                if alt or time.monotonic() - self._global_last_c <= 1.5:
                    self._global_last_c = 0.0
                    self._start_screen_capture()
            self._key_c_down, self._key_a_down = c_down, a_down
        except Exception:
            pass
        try:
            if self.winfo_exists():
                self.after(40, self._poll_global_shortcut)
        except Exception:
            pass

    def _setup_tray(self) -> None:
        import sys
        maxplus_gui = sys.modules.get("maxplus_gui")
        tray_ok = getattr(maxplus_gui, "_TRAY_OK", _TRAY_OK) if maxplus_gui is not None else _TRAY_OK
        tray_mod: Any = pystray
        if not (tray_ok and _PIL_OK and tray_mod is not None):
            return
        if self._app_icon_img is not None:
            icon_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            aspect = self._app_icon_img.width / max(1, self._app_icon_img.height)
            h = 54
            w = max(16, min(54, int(h * aspect)))
            feather_tray = self._app_icon_img.resize((w, h), Image.Resampling.LANCZOS)
            x = (64 - w) // 2
            y = (64 - h) // 2
            icon_image.paste(feather_tray, (x, y), feather_tray)
        else:
            icon_image = Image.new("RGBA", (64, 64), "#11151d")
            draw = ImageDraw.Draw(icon_image)
            draw.rounded_rectangle((5, 5, 59, 59), radius=14, fill="#7c8cff")
            draw.text((19, 18), "M", fill="white", stroke_width=1, stroke_fill="white")
        menu = tray_mod.Menu(
            tray_mod.MenuItem("เปิด MAX", lambda _i, _m: self._tray_queue.put("show"), default=True),
            tray_mod.MenuItem("จับภาพหน้าจอ", lambda _i, _m: self._tray_queue.put("capture")),
            tray_mod.MenuItem("ออก", lambda _i, _m: self._tray_queue.put("exit")),
        )
        self._tray = tray_mod.Icon("MaxPlusAI", icon_image, "MAX", menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _poll_tray_queue(self) -> None:
        try:
            while True:
                action = self._tray_queue.get_nowait()
                if action == "show": self._show_window()
                elif action == "capture": self._start_screen_capture()
                elif action == "exit": self._quit_app(); return
        except queue.Empty:
            pass
        except Exception:
            pass
        try:
            if self.winfo_exists():
                self.after(100, self._poll_tray_queue)
        except Exception:
            pass

    def _show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _hide_to_tray(self) -> None:
        if self._tray is not None:
            self.withdraw()
            tab = self._current_tab()
            if tab is not None:
                tab.status_var.set("ทำงานเบื้องหลังแล้ว • Ctrl+C แล้ว Ctrl+A เพื่อเลือกพื้นที่หน้าจอ")
        else:
            self.iconify()

    def _quit_app(self) -> None:
        if hasattr(self, "mcp_manager"):
            try:
                self.mcp_manager.disconnect_all()
            except Exception:
                pass
        if self._tray is not None:
            try:
                self._tray.stop()
            except Exception:
                pass
            self._tray = None
        self.quit()
        self.destroy()

    # ── model change ───────────────────────────────────────────────────────
    def _on_model_change(self, *_: object) -> None:
        if self._changing_provider:
            return
        model = self.model_var.get()
        if not model:
            return
        self._active_profile()["model"] = model
        tab = self._current_tab()
        if tab is not None:
            tab.ai.model = model
            tab.status_var.set(f"สลับ Model: {model}")

    def _on_provider_change(self, *_: object) -> None:
        if self._changing_provider:
            return
        name = self.provider_var.get()
        profile = next((p for p in self.profiles if p["name"] == name), None)
        if profile is None:
            return
        self.selected_profile_id = profile["id"]
        self._changing_provider = True
        self._model_box.configure(values=profile["models"])
        self.model_var.set(profile["model"])
        self._changing_provider = False

        tab = self._current_tab()
        if tab is not None:
            tab.profile_id = profile["id"]
            tab.profile_name = profile["name"]
            tab.ai.api_key = profile["api_key"]
            tab.ai.base_url = profile["base_url"].rstrip("/")
            tab.ai.api_mode = profile["api_mode"]
            tab.ai.model = profile["model"]
            tab.status_var.set(f"ใช้ {profile['name']} · {profile['model']}")

    # ── theme ──────────────────────────────────────────────────────────────
    def _toggle_theme(self) -> None:
        self._is_dark = not self._is_dark
        src = DARK if self._is_dark else LIGHT
        T.clear()
        T.update(src)

        self._theme_btn.configure(text="☀" if self._is_dark else "🌙")
        self.configure(bg=T["bg"])
        self._toolbar.configure(bg=T["bg"])
        self._toolbar_left.configure(bg=T["bg"])
        self._toolbar_right.configure(bg=T["bg"])
        if isinstance(self._logo_lbl, tk.Label):
            self._logo_lbl.configure(bg=T["bg"])
        if isinstance(self._title_lbl, tk.Label):
            self._title_lbl.configure(bg=T["bg"], fg=T["fg"])
        self._proj_btn.configure(bg=T["bg2"], fg=T["accent"], activebackground=T["bg3"])
        self._add_tab_btn.configure(bg=T["bg2"], fg=T["fg"], activebackground=T["bg3"])
        self._close_tab_btn.configure(bg=T["bg2"], fg=T["err_hdr"], activebackground=T["bg3"])
        if hasattr(self, "_team_btn") and isinstance(self._team_btn, tk.Button):
            self._team_btn.configure(bg=T["bg2"], fg=T["accent"], activebackground=T["bg3"], activeforeground=T["accent_hover"])
        self._theme_btn.configure(bg=T["bg2"], fg=T["fg"], activebackground=T["bg3"])
        self._settings_btn.configure(bg=T["bg2"], fg=T["fg"], activebackground=T["bg3"])
        self._mcp_btn.configure(bg=T["bg2"], fg=T["fg"], activebackground=T["bg3"])
        if isinstance(getattr(self, "_health_btn", None), tk.Button):
            self._health_btn.configure(bg=T["bg2"], fg=T["accent"], activebackground=T["bg3"], activeforeground=T["accent_hover"])

        # update notebook style
        style = ttk.Style(self)
        self._apply_notebook_style(style)

        for tab in self._tabs:
            if hasattr(tab, "apply_theme"):
                tab.apply_theme()

    def _check_update_background(self) -> None:
        """Check for updates in background on startup and show popup if new."""
        time.sleep(1.5)
        try:
            info = check_github_release()
            if info and is_newer_version(info.tag_name, APP_VERSION):
                skipped = self.settings_store.load_skipped_version()
                if info.tag_name != skipped and info.version != skipped:
                    self.after(500, lambda: self._show_update_dialog(info))
        except Exception:
            pass

    def _show_update_dialog(self, info: UpdateInfo) -> None:
        """Display the update dialog."""
        try:
            UpdateDialog(self, info, self.settings_store)
        except Exception:
            pass

    def check_updates_manual(self) -> None:
        """Check for updates manually (ignoring skip list)."""
        tab = self._current_tab()
        if tab is not None:
            tab.status_var.set("กำลังตรวจสอบเวอร์ชันล่าสุดจาก GitHub...")
        try:
            info = check_github_release()
            if info and is_newer_version(info.tag_name, APP_VERSION):
                if tab is not None:
                    tab.status_var.set(f"พบเวอร์ชันใหม่: {info.tag_name}")
                self._show_update_dialog(info)
            elif info:
                if tab is not None:
                    tab.status_var.set(f"คุณใช้งานเวอร์ชันล่าสุดแล้ว (v{APP_VERSION})")
                messagebox.showinfo(
                    "อัปเดต MAX",
                    f"คุณกำลังใช้งาน MAX เวอร์ชันล่าสุด (v{APP_VERSION}) แล้ว",
                    parent=self
                )
            else:
                if tab is not None:
                    tab.status_var.set("ไม่สามารถดึงข้อมูลเวอร์ชันจาก GitHub ได้")
                messagebox.showwarning(
                    "ตรวจสอบอัปเดต",
                    "ไม่สามารถเชื่อมต่อ GitHub Releases ได้ในขณะนี้\nกรุณาลองใหม่อีกครั้ง",
                    parent=self
                )
        except Exception as ex:
            if tab is not None:
                tab.status_var.set(f"ตรวจสอบอัปเดตล้มเหลว: {ex}")
            messagebox.showerror("ตรวจหาอัปเดตล้มเหลว", f"เกิดข้อผิดพลาด:\n{ex}", parent=self)

    def _apply_notebook_style(self, style: ttk.Style) -> None:
        try:
            style.theme_use("clam")
        except Exception:
            style.theme_use("default")

        style.configure(
            "TNotebook",
            background=T["tab_bg"],
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=T["tab_bg"],
            foreground=T["fg"],
            padding=[16, 8],
            font=FONT,
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", T["tab_sel"]), ("active", T["bg2"])],
            foreground=[("selected", T["accent"]), ("!selected", T["fg_dim"])],
        )
        style.configure(
            "TScrollbar",
            background=T["bg2"],
            troughcolor=T["bg"],
            borderwidth=0,
        )
        style.configure(
            "TCombobox",
            fieldbackground=T["bg2"],
            background=T["bg2"],
            foreground=T["fg"],
            arrowcolor=T["fg"],
            darkcolor=T["border"],
            lightcolor=T["border"],
            bordercolor=T["border"],
            padding=5,
            font=FONT,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", T["bg2"]), ("disabled", T["bg"])],
            background=[("readonly", T["bg2"]), ("active", T["bg3"])],
            foreground=[("readonly", T["fg"]), ("disabled", T["fg_dim"])],
            selectbackground=[("readonly", T["bg2"])],
            selectforeground=[("readonly", T["fg"])],
            arrowcolor=[("readonly", T["fg"]), ("active", T["accent"])],
        )
        self.option_add("*TCombobox*Listbox.background", T["bg2"])
        self.option_add("*TCombobox*Listbox.foreground", T["fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", T["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")


def main() -> None:
    import signal
    import sys

    if not _PIL_OK:
        print("[warn] Pillow ไม่ได้ติดตั้ง — ฟีเจอร์วางภาพถูกปิด")
        print("       pip install Pillow")

    app = MaxPlusGUI()

    # Python 3.14: Ctrl+C ใน tkinter mainloop เป็น C-level → ต้องใช้ signal
    def _sigint(_sig: int, _frame: object) -> None:
        app._quit_app()

    signal.signal(signal.SIGINT, _sigint)

    # ให้ tkinter poll SIGINT ทุก 200ms (Python 3.14 workaround)
    def _poll() -> None:
        try:
            if app.winfo_exists():
                app.after(200, _poll)
        except Exception:
            pass
    _poll()

    app.mainloop()
    sys.exit(0)


if __name__ == "__main__":
    main()
