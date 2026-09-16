"""
chat_tab.py — Individual Chat Session tab handling messages, images, skills, and tools.
"""

import os
import sys
from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Optional, Union, TYPE_CHECKING

# Ensure workspace root is in sys.path when executed directly
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from PIL import Image, ImageTk, ImageGrab
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    from core.ai_client import AIClient
    from core.mcp_manager import MCPManager
    from core.skill_manager import SkillManager
    from ui.clipboard import img_to_b64, copy_image_to_clipboard, read_clipboard_text
    from ui.dialogs.crop_dialog import CropDialog
    from ui.dialogs.skill_picker_dialog import SkillPickerDialog
    from ui.themes import T, FONT, FONT_BOLD, FONT_TINY
    from ui.widgets.message_bubble import MessageBubble
    from ui.widgets.scrollable_frame import ScrollableFrame
    from ui.widgets.context_menu import attach_text_context_menu
except (ImportError, ModuleNotFoundError):
    from src.core.ai_client import AIClient  # type: ignore[no-redef]
    from src.core.mcp_manager import MCPManager  # type: ignore[no-redef]
    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]
    from src.ui.clipboard import img_to_b64, copy_image_to_clipboard, read_clipboard_text  # type: ignore[no-redef]
    from src.ui.dialogs.crop_dialog import CropDialog  # type: ignore[no-redef]
    from src.ui.dialogs.skill_picker_dialog import SkillPickerDialog  # type: ignore[no-redef]
    from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY  # type: ignore[no-redef]
    from src.ui.widgets.message_bubble import MessageBubble  # type: ignore[no-redef]
    from src.ui.widgets.scrollable_frame import ScrollableFrame  # type: ignore[no-redef]
    from src.ui.widgets.context_menu import attach_text_context_menu  # type: ignore[no-redef]



class ChatTab(tk.Frame):
    """หนึ่งแท็บ = หนึ่ง session สนทนา"""

    def __init__(self, parent: tk.Misc, tab_name: str = "Chat", api_key: str = "",
                 base_url: str = "https://api.maxplus-ai.cc/gemini-full/v1",
                 model: str = "gemini-3.8-flash", api_mode: str = "chat_completions",
                 profile_id: str = "", profile_name: str = "") -> None:
        super().__init__(parent, bg=T["bg"])
        self.tab_name = tab_name
        self.profile_id = profile_id
        self.profile_name = profile_name
        self.history: list = []
        self.ai = AIClient(api_key=api_key, base_url=base_url, model=model, api_mode=api_mode)
        self._pending_img: Optional["Image.Image"] = None
        self._thumb_ref = None
        self._bubbles: list[MessageBubble] = []
        self._last_ctrl_c = 0.0
        self.skill_manager = SkillManager()
        self.enabled_skills = self.skill_manager.default_ids()
        self._build()

    def _build(self) -> None:
        # compact system prompt bar
        self._system_frame = tk.Frame(self, bg=T["bg2"], padx=10, pady=3,
                                      highlightthickness=1, highlightbackground=T["border"])
        self._system_frame.pack(fill="x", padx=16, pady=(4, 4))
        self._system_label = tk.Label(self._system_frame, text="คำสั่งระบบ", bg=T["bg2"],
                                      fg=T["fg_dim"], font=FONT_TINY)
        self._system_label.pack(side="left", padx=(0, 8))
        self.sys_entry = tk.Entry(self._system_frame, bg=T["bg2"], fg=T["fg_dim"],
                                  insertbackground=T["fg"], font=FONT_TINY,
                                  relief="flat", bd=0)
        self.sys_entry.insert(0, "You are a helpful AI assistant")
        self.sys_entry.pack(fill="x", expand=True, side="left")
        attach_text_context_menu(self.sys_entry, is_editable=True)

        # scroll area
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=6)

        # bottom composer card (faint muted surface, opaque, Gemini card style)
        self._composer = tk.Frame(self, bg=T["composer_bg"], padx=14, pady=10,
                                  highlightthickness=1, highlightbackground=T["border"])
        self._composer.pack(fill="x", padx=16, pady=(8, 6))

        self._img_bar = tk.Frame(self._composer, bg=T["composer_bg"])
        self._thumb_lbl = tk.Label(self._img_bar, bg=T["composer_bg"])
        self._img_info = tk.Label(self._img_bar, bg=T["composer_bg"],
                                  fg=T["img_clr"], font=FONT)
        self._img_clr_btn = tk.Button(self._img_bar, text="✕",
                                      bg=T["composer_bg"], fg=T["err_hdr"],
                                      font=("Segoe UI", 10, "bold"),
                                      relief="flat", cursor="hand2",
                                      command=self._clear_img)
        self._crop_btn = tk.Button(self._img_bar, text="✂ ครอบภาพ", bg=T["bg_btn"],
                                   fg=T["fg"], font=FONT_TINY, relief="flat",
                                   padx=9, pady=4, cursor="hand2", command=self._open_crop)

        self.entry = tk.Text(self._composer, bg=T["composer_bg"], fg=T["fg"],
                             insertbackground=T["fg"], font=FONT,
                             relief="flat", bd=0, height=4, wrap=tk.WORD,
                             padx=4, pady=4, undo=True,
                             spacing1=2, spacing2=3)
        self.entry.pack(fill="x", expand=True)
        attach_text_context_menu(self.entry, is_editable=True, on_paste=self._on_paste)
        self.entry.bind("<Return>",       lambda e: (self._send_chat(), "break")[1])
        self.entry.bind("<Shift-Return>", lambda _: None)
        self.entry.bind("<Control-v>", self._on_paste)
        self.entry.bind("<Control-V>", self._on_paste)
        self.entry.bind("<<Paste>>", self._on_paste)
        self.entry.bind("<Control-c>", self._remember_ctrl_c, add="+")
        self.entry.bind("<Control-C>", self._remember_ctrl_c, add="+")
        self.entry.bind("<Control-a>", self._ctrl_a)
        self.entry.bind("<Control-A>", self._ctrl_a)
        self.entry.bind("<Control-Alt-a>", lambda _e: self._open_crop() or "break")

        self._actions = tk.Frame(self._composer, bg=T["composer_bg"])
        self._actions.pack(fill="x", pady=(8, 0))
        self._add_img_btn = tk.Button(self._actions, text="🖼",
                                      bg=T["bg_btn"], fg=T["fg"], font=FONT_TINY,
                                      activebackground=T["bg3"], activeforeground=T["fg"],
                                      relief="flat", padx=9, pady=5,
                                      command=self._choose_image, cursor="hand2")
        self._add_img_btn.pack(side="left")
        self._screen_btn = tk.Button(
            self._actions, text="✂", bg=T["bg_btn"], fg=T["fg"],
            activebackground=T["bg3"], activeforeground=T["fg"],
            font=FONT_TINY, relief="flat", padx=9, pady=5,
            command=self._capture_screen,
            cursor="hand2",
        )
        self._screen_btn.pack(side="left", padx=(5, 0))
        self._skills_btn = tk.Button(
            self._actions, text="🪶" if not self.enabled_skills else f"🪶 {len(self.enabled_skills)}",
            bg=T["bg_btn"], fg=T["accent"],
            activebackground=T["bg3"], activeforeground=T["accent_hover"],
            font=FONT_TINY, relief="flat", padx=9, pady=5,
            command=self._open_skill_picker, cursor="hand2",
        )
        self._skills_btn.pack(side="left", padx=(5, 0))
        self._clear_btn = tk.Button(self._actions, text="🗑", bg=T["composer_bg"], fg=T["fg_dim"],
                                    activebackground=T["bg3"], activeforeground=T["fg"],
                                    font=FONT_TINY, relief="flat", padx=9, pady=5,
                                    command=self._clear_history, cursor="hand2")
        self._clear_btn.pack(side="left", padx=(5, 0))
        self._btn_send = tk.Button(self._actions, text="ส่ง  ➜",
                                   bg=T["accent"], fg="#ffffff", font=FONT_BOLD,
                                   activebackground=T["accent_hover"], activeforeground="#ffffff",
                                   relief="flat", padx=18, pady=6,
                                   command=self._send_chat, cursor="hand2")
        self._btn_send.pack(side="right")
        self._ask_btn = tk.Button(self._actions, text="ถามครั้งเดียว", bg=T["bg_btn"], fg=T["fg"],
                                  activebackground=T["bg3"], activeforeground=T["fg"],
                                  font=FONT_TINY, relief="flat", padx=12, pady=6,
                                  command=self._send_ask, cursor="hand2")
        self._ask_btn.pack(side="right", padx=(0, 7))

        self.status_var = tk.StringVar(
            value="พร้อมใช้งาน  •  Ctrl+V วางข้อความหรือภาพ  •  Ctrl+C → Ctrl+A เลือกพื้นที่หน้าจอ  •  ปิดหน้าต่างเพื่อซ่อนลง Tray")
        self._status_label = tk.Label(self, textvariable=self.status_var, bg=T["bg"],
                                      fg=T["fg_dim"], font=FONT_TINY, anchor="w")
        self._status_label.pack(fill="x", padx=19, pady=(0, 7))

        self.entry.focus_set()

    # ── skills ────────────────────────────────────────────────────────────
    def _open_skill_picker(self) -> None:
        self.skill_manager.refresh()
        available = set(self.skill_manager.skills)
        self.enabled_skills.intersection_update(available)
        SkillPickerDialog(self, self.skill_manager, self.enabled_skills,
                          self._set_enabled_skills)

    def _set_enabled_skills(self, enabled: set[str]) -> None:
        self.enabled_skills = set(enabled)
        self._skills_btn.configure(text="🪶" if not self.enabled_skills else f"🪶 {len(self.enabled_skills)}")
        names = [self.skill_manager.skills[item].name for item in sorted(self.enabled_skills)
                 if item in self.skill_manager.skills]
        self.status_var.set("Skills: " + (", ".join(names) if names else "ปิดทั้งหมด"))

    def _effective_system_prompt(self) -> str:
        top = self.winfo_toplevel()
        proj_name = getattr(top, "project_name", "MAX")
        proj_path = getattr(top, "project_path", os.getcwd())
        model_name = getattr(self.ai, "model", "default")

        project_context = (
            f"[Context: Working in Project '{proj_name}' at '{proj_path}', Model: '{model_name}']\n"
            "Use the available file and command tools for requested code changes. Relative paths are resolved "
            "from this project directory. After editing, read the changed file or run an appropriate check; "
            "only report completion when the tool result confirms the change was written successfully."
        )
        base_prompt = self.sys_entry.get().strip()
        full_system = f"{project_context}\n{base_prompt}" if base_prompt else project_context
        return self.skill_manager.compose_system_prompt(full_system, self.enabled_skills)

    # ── bubbles ────────────────────────────────────────────────────────────
    def _add_bubble(self, role: str, content: str,
                    bg_card: str, hdr_color: str,
                    img: Optional["Image.Image"] = None,
                    is_thinking: bool = False) -> MessageBubble:
        b = MessageBubble(
            self.scroll.inner,
            role,
            content,
            bg_card,
            hdr_color,
            img=img,
            is_thinking=is_thinking,
            on_open_media=self._on_open_media,
        )
        self._bubbles.append(b)
        self.after(60, self.scroll.scroll_bottom)
        return b

    def _on_open_media(self, file_path: str, media_type: str = "image", prompt: str = "") -> None:
        """Forward media open request to MainWindow to open dedicated media tab."""
        top = self.winfo_toplevel()
        open_media_tab = getattr(top, "open_media_tab", None)
        if callable(open_media_tab):
            open_media_tab(file_path, media_type=media_type, prompt=prompt)

    def _check_and_auto_open_media(self, content: str, logs: Optional[list[str]] = None) -> None:
        """Auto open newly generated media file in a new viewer tab."""
        full_text = content
        if logs:
            full_text += "\n" + "\n".join(logs)
        try:
            from ui.widgets.message_bubble import extract_media_items
        except (ImportError, ModuleNotFoundError):
            from src.ui.widgets.message_bubble import extract_media_items  # type: ignore[no-redef]

        items = extract_media_items(full_text)
        if items:
            latest = items[-1]
            top = self.winfo_toplevel()
            open_media_tab = getattr(top, "open_media_tab", None)
            if callable(open_media_tab):
                self.after(200, lambda: open_media_tab(latest["path"], media_type=latest["type"]))

    # ── image clipboard ────────────────────────────────────────────────────
    def _capture_screen(self) -> None:
        start_capture = getattr(self.winfo_toplevel(), "_start_screen_capture", None)
        if callable(start_capture):
            start_capture()

    def _try_grab_image(self) -> Optional["Image.Image"]:
        """พยายามอ่านภาพจาก clipboard ด้วยหลายวิธี"""
        if not _PIL_OK:
            return None
        try:
            clip = ImageGrab.grabclipboard()
            if isinstance(clip, Image.Image):
                return clip
            if isinstance(clip, list):
                for p in clip:
                    try:
                        return Image.open(p)
                    except Exception:
                        continue
        except Exception as ex:
            self.status_var.set(f"grabclipboard err: {ex}")
        try:
            import win32clipboard  # type: ignore[import-untyped]
            import struct
            win32clipboard.OpenClipboard()
            try:
                CF_DIB = 8
                if win32clipboard.IsClipboardFormatAvailable(CF_DIB):
                    data = win32clipboard.GetClipboardData(CF_DIB)
                    w, h = struct.unpack_from('<ii', data, 4)
                    h = abs(h)
                    bpp = struct.unpack_from('<H', data, 14)[0]
                    offset = 40
                    if bpp <= 8:
                        offset += 4 * (1 << bpp)
                    raw = data[offset:]
                    if bpp == 32:
                        img = Image.frombytes('RGBA', (w, h), raw, 'raw', 'BGRA', 0, -1)
                    else:
                        img = Image.frombytes('RGB', (w, h), raw, 'raw', 'BGR', 0, -1)
                    return img
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            pass
        return None

    def _choose_image(self) -> None:
        """Choose an image file; clipboard images use Ctrl+V."""
        if not _PIL_OK:
            self.status_var.set("ไม่พบ Pillow — ติดตั้งด้วย pip install Pillow ก่อนเพิ่มรูปภาพ")
            return
        path = filedialog.askopenfilename(
            title="เพิ่มรูปภาพ",
            initialdir=os.getcwd(),
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"),
                       ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with Image.open(path) as source:
                self._set_img(source.convert("RGBA") if source.mode in ("RGBA", "LA") else source.convert("RGB"))
        except Exception as ex:
            self.status_var.set(f"เปิดรูปภาพไม่สำเร็จ: {ex}")

    def _on_paste(self, e: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        """Paste either an image attachment or external Unicode text."""
        img = self._try_grab_image()
        if img is not None:
            self._set_img(img.copy())
            return "break"
        text = read_clipboard_text(self)
        if text is None:
            self.status_var.set("Clipboard ไม่มีข้อความหรือรูปภาพที่รองรับ")
            return "break"
        if not text:
            return "break"
        try:
            self.entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
        self.entry.insert(tk.INSERT, text)
        self.entry.see(tk.INSERT)
        self.entry.focus_set()
        self.status_var.set(f"วางข้อความแล้ว {len(text):,} ตัวอักษร")
        return "break"

    def _remember_ctrl_c(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._last_ctrl_c = time.monotonic()

    def _ctrl_a(self, _event: tk.Event) -> str:  # type: ignore[type-arg]
        if time.monotonic() - self._last_ctrl_c <= 1.4:
            self._last_ctrl_c = 0.0
            root = self.winfo_toplevel()
            if hasattr(root, "_start_screen_capture"):
                root._start_screen_capture()  # type: ignore[attr-defined]
            return "break"
        self.entry.tag_add(tk.SEL, "1.0", "end-1c")
        self.entry.mark_set(tk.INSERT, "1.0")
        self.entry.see(tk.INSERT)
        return "break"

    def _open_crop(self) -> None:
        if self._pending_img is None:
            self.status_var.set("เพิ่มหรือวางรูปภาพก่อนเปิดโหมดครอป")
            return
        CropDialog(self, self._pending_img, self._set_cropped_img)

    def _set_cropped_img(self, img: "Image.Image") -> None:
        """Keep a crop ready to send and expose it to every clipboard-aware app."""
        self._set_img(img)
        try:
            copy_image_to_clipboard(img)
            w, h = img.size
            self.status_var.set(
                f"ครอปแล้ว {w} × {h} px • คัดลอกรูปแล้ว กด Ctrl+V ในแชทอื่นได้ทันที"
            )
        except Exception as ex:
            self.status_var.set(f"ครอปภาพแล้ว แต่คัดลอกไป Clipboard ไม่สำเร็จ: {ex}")

    def _set_img(self, img: "Image.Image") -> None:
        self._pending_img = img
        thumb = img.copy(); thumb.thumbnail((72, 72))
        self._thumb_ref = ImageTk.PhotoImage(thumb)
        self._thumb_lbl.config(image=self._thumb_ref)
        self._img_bar.pack(fill="x", before=self.entry, pady=(0, 8))
        self._thumb_lbl.pack(side="left", padx=(0, 4), pady=2)
        w, h = img.size
        self._img_info.config(text=f"รูปภาพพร้อมส่ง  •  {w} × {h} px")
        self._img_info.pack(side="left", padx=(6, 8))
        self._crop_btn.pack(side="left", padx=(0, 4))
        self._img_clr_btn.pack(side="right", padx=4)
        self.status_var.set(f"เพิ่มรูปภาพแล้ว {w} × {h} px  •  กด ✂ เพื่อปรับขอบเขตภาพ")

    def _clear_img(self) -> None:
        self._pending_img = None; self._thumb_ref = None
        self._thumb_lbl.pack_forget()
        self._img_info.pack_forget()
        self._crop_btn.pack_forget()
        self._img_clr_btn.pack_forget()
        self._img_bar.pack_forget()
        self.status_var.set("นำรูปภาพออกแล้ว")

    def _pop_b64(self) -> Optional[str]:
        if self._pending_img is None:
            return None
        b64 = img_to_b64(self._pending_img)
        self.after(0, self._clear_img)
        return b64

    # ── helpers ────────────────────────────────────────────────────────────
    def _get_input(self) -> str:
        t = self.entry.get("1.0", tk.END).strip()
        self.entry.delete("1.0", tk.END)
        return t

    def _build_content(self, text: str, b64: Optional[str]) -> Union[str, list[dict[str, Any]]]:
        if b64 is None:
            return text
        return [
            {"type": "text",      "text": text or "อธิบายภาพนี้ให้หน่อย"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]

    def _clear_history(self) -> None:
        self.history = []; self._bubbles.clear()
        for w in self.scroll.inner.winfo_children():
            w.destroy()
        self._clear_img()
        self.status_var.set("History cleared")

    # ── send chat ──────────────────────────────────────────────────────────
    def _send_chat(self) -> None:
        msg = self._get_input()
        snap = self._pending_img
        b64 = self._pop_b64()
        if not msg and b64 is None:
            return
        user_text = msg if msg else "(ส่งภาพ)"
        self._add_bubble("You", user_text, T["bg_user"], T["user_hdr"], img=snap)
        thinking = self._add_bubble("AI", "", T["bg_ai"], T["ai_hdr"], is_thinking=True)
        self.status_var.set("กำลังคิดและวิเคราะห์...")
        content = self._build_content(msg, b64)
        system = self._effective_system_prompt()
        threading.Thread(target=self._run_chat, args=(content, thinking, system), daemon=True).start()

    def _run_chat(self, content: Union[str, list[dict[str, Any]]], thinking: MessageBubble, system: str) -> None:
        self.ai.system_prompt = system
        start_time = time.monotonic()
        try:
            mcp: Optional[MCPManager] = getattr(self.winfo_toplevel(), "mcp_manager", None)
            tools = mcp.get_openai_tools() if (mcp and mcp.enabled) else None

            if tools and mcp:
                def on_status(text: str) -> None:
                    if "->" in text or "ผลลัพธ์" in text:
                        self.after(0, lambda: thinking.add_step("ผลลัพธ์เครื่องมือ", text, status="done"))
                    elif "เรียกใช้เครื่องมือ" in text:
                        self.after(0, lambda: thinking.add_step(text, "", status="running"))
                    else:
                        self.after(0, lambda: thinking.update_thinking_status(text))
                    self.after(0, lambda: self.status_var.set(text))

                self.history, logs = self.ai.chat_with_tools(
                    content, self.history, tools=tools,
                    tool_executor=mcp.execute_tool, on_status=on_status
                )
                reply = self.history[-1]["content"]
                role_title = "AI 🛠" if logs else "AI"
            else:
                def on_chunk(token: str) -> None:
                    self.after(0, lambda t=token: thinking.append_stream_chunk(t))

                self.history = self.ai.stream_chat(
                    content, self.history, on_chunk=on_chunk
                )
                reply = self.history[-1]["content"]
                role_title = "AI"

            elapsed = time.monotonic() - start_time
            self.after(0, lambda: thinking.finish_processing(reply, role_title, elapsed))
            self.after(0, lambda: self._check_and_auto_open_media(reply, logs if 'logs' in locals() else None))
            self.after(0, lambda: self.status_var.set(f"เสร็จสิ้น ({elapsed:.1f}s)"))
        except Exception as ex:
            err = str(ex)
            elapsed = time.monotonic() - start_time
            self.after(0, lambda: thinking.add_step("เกิดข้อผิดพลาด", err, status="error"))
            self.after(0, lambda: thinking.finish_processing(err, "❌ Error", elapsed))
            self.after(0, lambda: self.status_var.set(f"Error: {err}"))

    # ── ask single-turn ────────────────────────────────────────────────────
    def _send_ask(self) -> None:
        msg = self._get_input()
        snap = self._pending_img
        b64 = self._pop_b64()
        if not msg and b64 is None:
            return
        user_text = msg if msg else "(ส่งภาพ)"
        self._add_bubble("You (Ask)", user_text, T["bg_user"], T["user_hdr"], img=snap)
        thinking = self._add_bubble("AI", "", T["bg_ai"], T["ai_hdr"], is_thinking=True)
        self.status_var.set("กำลังคิดและวิเคราะห์...")
        content = self._build_content(msg, b64)
        system = self._effective_system_prompt()
        threading.Thread(target=self._run_ask, args=(content, thinking, system), daemon=True).start()

    def _run_ask(self, content: Union[str, list[dict[str, Any]]], thinking: MessageBubble, system: str) -> None:
        start_time = time.monotonic()
        try:
            client = AIClient(api_key=self.ai.api_key, base_url=self.ai.base_url,
                              model=self.ai.model, api_mode=self.ai.api_mode,
                              system_prompt=system, timeout=self.ai.timeout)
            mcp: Optional[MCPManager] = getattr(self.winfo_toplevel(), "mcp_manager", None)
            tools = mcp.get_openai_tools() if (mcp and mcp.enabled) else None

            if tools and mcp:
                def on_status(text: str) -> None:
                    if "->" in text or "ผลลัพธ์" in text:
                        self.after(0, lambda: thinking.add_step("ผลลัพธ์เครื่องมือ", text, status="done"))
                    elif "เรียกใช้เครื่องมือ" in text:
                        self.after(0, lambda: thinking.add_step(text, "", status="running"))
                    else:
                        self.after(0, lambda: thinking.update_thinking_status(text))
                    self.after(0, lambda: self.status_var.set(text))

                hist, logs = client.chat_with_tools(
                    content, [], tools=tools, tool_executor=mcp.execute_tool, on_status=on_status
                )
                ans = hist[-1]["content"]
                role_title = "AI 🛠" if logs else "AI"
            else:
                def on_chunk(token: str) -> None:
                    self.after(0, lambda t=token: thinking.append_stream_chunk(t))

                ans = client.stream_ask(content, on_chunk=on_chunk)
                role_title = "AI"

            elapsed = time.monotonic() - start_time
            self.after(0, lambda: thinking.finish_processing(ans, role_title, elapsed))
            self.after(0, lambda: self._check_and_auto_open_media(ans, logs if 'logs' in locals() else None))
            self.after(0, lambda: self.status_var.set(f"เสร็จสิ้น ({elapsed:.1f}s)"))
        except Exception as ex:
            err = str(ex)
            elapsed = time.monotonic() - start_time
            self.after(0, lambda: thinking.add_step("เกิดข้อผิดพลาด", err, status="error"))
            self.after(0, lambda: thinking.finish_processing(err, "❌ Error", elapsed))
            self.after(0, lambda: self.status_var.set(f"Error: {err}"))


    # ── theme ──────────────────────────────────────────────────────────────
    def apply_theme(self) -> None:
        self.configure(bg=T["bg"])
        self.scroll.apply_theme()
        self._system_frame.configure(bg=T["bg2"], highlightbackground=T["border"])
        self._system_label.configure(bg=T["bg2"], fg=T["fg_dim"])
        self._skills_btn.configure(bg=T["bg_btn"], fg=T["accent"],
                                   activebackground=T["bg3"])
        self.sys_entry.configure(bg=T["bg2"], fg=T["fg_dim"], insertbackground=T["fg"])
        self._composer.configure(bg=T["composer_bg"], highlightbackground=T["border"])
        self._img_bar.configure(bg=T["composer_bg"])
        self._thumb_lbl.configure(bg=T["composer_bg"])
        self._img_info.configure(bg=T["composer_bg"], fg=T["img_clr"])
        self._img_clr_btn.configure(bg=T["composer_bg"], fg=T["err_hdr"])
        self._crop_btn.configure(bg=T["bg_btn"], fg=T["fg"])
        self.entry.configure(bg=T["composer_bg"], fg=T["fg"], insertbackground=T["fg"])
        self._actions.configure(bg=T["composer_bg"])
        self._add_img_btn.configure(bg=T["bg_btn"], fg=T["fg"], activebackground=T["bg3"])
        self._screen_btn.configure(bg=T["bg_btn"], fg=T["fg"], activebackground=T["bg3"])
        self._ask_btn.configure(bg=T["bg_btn"], fg=T["fg"], activebackground=T["bg3"])
        self._clear_btn.configure(bg=T["composer_bg"], fg=T["fg_dim"], activebackground=T["bg3"])
        self._btn_send.configure(bg=T["accent"], activebackground=T["accent_hover"])
        self._status_label.configure(bg=T["bg"], fg=T["fg_dim"])
        for b in self._bubbles:
            b.apply_theme()
