"""
src/ui/widgets/message_bubble.py — Antigravity-style agentic message bubble widget with collapsible thinking & tool execution process.
"""

import os
import re
import time
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Optional, TYPE_CHECKING, Any

try:
    from PIL import Image, ImageTk  # type: ignore[import-untyped]
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

from src.ui.themes import (
    T,
    FONT,
    FONT_BOLD,
    FONT_TINY,
    FONT_MONO,
    FONT_HDR,
    FONT_H1,
    FONT_H2,
    FONT_H3,
    FONT_CODE_INLINE,
    FONT_QUOTE,
)


_FEATHER_ICON_PHOTO = None


def _get_feather_icon() -> Optional[Any]:
    global _FEATHER_ICON_PHOTO
    if _FEATHER_ICON_PHOTO is not None:
        return _FEATHER_ICON_PHOTO
    if not _PIL_OK:
        return None
    try:
        import sys
        base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
        candidates = [
            os.path.join(base, "src", "assets", "max_icon.png"),
            os.path.join(base, "src", "assets", "icon.png"),
            os.path.join(base, "src", "assets", "feather.png"),
            os.path.join(base, "icon.png"),
        ]
        for path in candidates:
            if os.path.exists(path):
                img = Image.open(path).convert("RGBA")
                aspect = img.width / max(1, img.height)
                h = 18
                w = max(12, int(h * aspect))
                resized = img.resize((w, h), Image.Resampling.LANCZOS)
                _FEATHER_ICON_PHOTO = ImageTk.PhotoImage(resized)
                return _FEATHER_ICON_PHOTO
    except Exception:
        pass
    return None


def _format_badge_text(role: str, has_icon: bool = False) -> str:
    """Format role into MAX badges with icon or emoji."""
    if "Error" in role:
        return f"⚠️ {role}"
    if role.startswith("You"):
        return "👤 คุณ"
    if "🛠" in role:
        return "MAX  [Agent Tools]" if has_icon else "🪶 MAX  [Agent Tools]"
    if role.startswith("AI"):
        return "MAX" if has_icon else "🪶 MAX"
    return role


_SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class MessageBubble(tk.Frame):
    def __init__(self, parent: tk.Widget, role: str, content: str,
                 bg_card: str, hdr_color: str,
                 img: Optional["Image.Image"] = None,
                 is_thinking: bool = False) -> None:
        super().__init__(
            parent,
            bg=bg_card,
            padx=16,
            pady=12,
            highlightthickness=1,
            highlightbackground=T["border"],
        )
        self._content = content
        self._bg_card = bg_card
        self._hdr_color = hdr_color
        self._role_raw = role
        self._role_kind = "error" if "Error" in role else ("user" if role.startswith("You") else "ai")
        self._save_btns: list[tk.Button] = []
        self._thumb_ref = None
        self._steps: list[dict[str, Any]] = []
        self._is_thinking = is_thinking
        self._start_time = time.monotonic() if is_thinking else 0.0
        self._process_expanded = False
        self._spinner_idx = 0
        self._thinking_text = "กำลังคิดและประมวลผล..."
        self.pack(fill="x", padx=16, pady=(0, 10))

        # Header bar
        self._hdr_frame = tk.Frame(self, bg=bg_card)
        self._hdr_frame.pack(fill="x", pady=(0, 6))

        # Role icon & badge
        icon_photo = _get_feather_icon() if (role.startswith("AI") or "🛠" in role) else None
        self._role_icon_lbl = tk.Label(self._hdr_frame, bg=bg_card)
        if icon_photo:
            self._role_icon_lbl.configure(image=icon_photo)
            self._role_icon_lbl.pack(side="left", padx=(0, 4))

        badge_text = _format_badge_text(role, has_icon=icon_photo is not None)
        self._role_lbl = tk.Label(
            self._hdr_frame,
            text=badge_text,
            bg=bg_card,
            fg=hdr_color,
            font=FONT_HDR,
        )
        self._role_lbl.pack(side="left")

        # Copy button (Sleek flat style)
        self._copy_btn = tk.Button(
            self._hdr_frame,
            text="📋 คัดลอก",
            bg=T["bg_btn"],
            fg=T["fg"],
            activebackground=T["bg3"],
            activeforeground=T["fg"],
            font=FONT_TINY,
            relief="flat",
            padx=9,
            pady=2,
            cursor="hand2",
            command=self._copy,
        )
        self._copy_btn.pack(side="right")

        # Image thumbnail (if provided)
        if img is not None and _PIL_OK:
            try:
                thumb = img.copy()
                thumb.thumbnail((260, 200))
                self._thumb_ref = ImageTk.PhotoImage(thumb)
                self._img_label = tk.Label(
                    self,
                    image=self._thumb_ref,
                    bg=bg_card,
                    relief="flat",
                    bd=0,
                )
                self._img_label.pack(anchor="w", pady=(2, 6))
            except Exception:
                pass

        # ── Antigravity Process / Thinking Accordion ─────────────────────────
        self._process_container = tk.Frame(self, bg=bg_card)

        self._process_header_btn = tk.Button(
            self._process_container,
            text="⠋ กำลังคิดและประมวลผล...",
            font=FONT_TINY,
            bg=T.get("bg2", "#282a2c"),
            fg=T.get("sub", "#9aa0a6"),
            activebackground=T.get("bg3", "#333538"),
            activeforeground=T.get("fg", "#ffffff"),
            relief="flat",
            anchor="w",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._toggle_process,
        )
        if is_thinking:
            self._process_container.pack(fill="x", pady=(0, 6))
            self._process_header_btn.pack(fill="x", pady=(0, 4))
            self.after(90, self._animate_spinner)

        self._steps_frame = tk.Frame(self._process_container, bg=T.get("bg2", "#282a2c"), padx=10, pady=8,
                                     highlightthickness=1, highlightbackground=T.get("border", "#3c4043"))
        # Initially collapsed if finished, expanded if active thinking

        # ── Body Text (Blog-style typography) ────────────────────────────────
        self.body = tk.Text(
            self,
            bg=bg_card,
            fg=T["fg"],
            font=FONT,
            wrap=tk.WORD,
            relief="flat",
            bd=0,
            padx=2,
            pady=4,
            cursor="arrow",
            spacing1=3,
            spacing2=4,
            spacing3=4,
            state="normal",
        )
        self._configure_tags()
        self.body.insert("1.0", content)
        self._apply_markdown_tags(content)
        self.body.configure(state="disabled")
        self.body.pack(fill="x", expand=True)
        self.body.bind("<Key>", self._guard)
        self._add_save_buttons(content)
        self.after(10, self._fit)

    def _configure_tags(self) -> None:
        """Setup text tags for blog and markdown elements."""
        self.body.tag_configure("h1", font=FONT_H1, foreground=T["accent"], spacing1=10, spacing3=4)
        self.body.tag_configure("h2", font=FONT_H2, foreground=T["fg"], spacing1=8, spacing3=3)
        self.body.tag_configure("h3", font=FONT_H3, foreground=T["fg"], spacing1=6, spacing3=2)
        self.body.tag_configure("bold", font=FONT_BOLD)
        self.body.tag_configure("quote", font=FONT_QUOTE, foreground=T["quote_fg"], lmargin1=16, lmargin2=16)
        self.body.tag_configure("bullet", lmargin1=12, lmargin2=26)
        self.body.tag_configure(
            "code_block",
            font=FONT_MONO,
            background=T["code_bg"],
            foreground=T["code_fg"],
            lmargin1=14,
            lmargin2=14,
            spacing1=4,
            spacing3=4,
        )
        self.body.tag_configure(
            "inline_code",
            font=FONT_CODE_INLINE,
            background=T["code_bg"],
            foreground=T["code_fg"],
        )

    def _apply_markdown_tags(self, text: str) -> None:
        """Scan text and apply typography tags for headers, quotes, lists, and code."""
        # Code blocks (```...```)
        for match in re.finditer(r"```(?:\w+)?\n[\s\S]*?```", text):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.body.tag_add("code_block", start, end)

        # Headings and list bullets line by line
        lines = text.split("\n")
        idx = 0
        for line in lines:
            line_len = len(line)
            line_start = f"1.0+{idx}c"
            line_end = f"1.0+{idx + line_len}c"
            trimmed = line.strip()

            if trimmed.startswith("# "):
                self.body.tag_add("h1", line_start, line_end)
            elif trimmed.startswith("## "):
                self.body.tag_add("h2", line_start, line_end)
            elif trimmed.startswith("### "):
                self.body.tag_add("h3", line_start, line_end)
            elif trimmed.startswith("> "):
                self.body.tag_add("quote", line_start, line_end)
            elif trimmed.startswith("- ") or trimmed.startswith("* ") or re.match(r"^\d+\.\s", trimmed):
                self.body.tag_add("bullet", line_start, line_end)

            idx += line_len + 1

        # Bold (**text**)
        for match in re.finditer(r"\*\*(.+?)\*\*", text):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.body.tag_add("bold", start, end)

        # Inline code (`text`)
        for match in re.finditer(r"`([^`\n]+)`", text):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.body.tag_add("inline_code", start, end)

    def _fit(self) -> None:
        self.body.configure(state="normal")
        self.body.update_idletasks()
        try:
            count = self.body.count("1.0", "end", "displaylines")
            lines = int(count[0]) if count else 1
        except Exception:
            lines = 2
        self.body.configure(height=max(1, lines), state="disabled")

    def _guard(self, e: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        if int(e.state) & 0x4 and e.keysym.lower() in ("c", "a"):
            return None
        return "break"

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._content)

    def _save_code(self, code: str, lang: str) -> None:
        """Save extracted code block to file."""
        ext_map = {
            "python": ".py", "py": ".py", "javascript": ".js", "js": ".js",
            "typescript": ".ts", "ts": ".ts", "java": ".java", "json": ".json",
            "html": ".html", "css": ".css", "bash": ".sh", "sh": ".sh",
            "kotlin": ".kt", "cpp": ".cpp", "c": ".c", "rust": ".rs",
            "sql": ".sql", "xml": ".xml", "yaml": ".yaml", "yml": ".yml",
        }
        ext = ext_map.get(lang.lower(), ".txt")
        path = filedialog.asksaveasfilename(
            initialdir=os.getcwd(),
            defaultextension=ext,
            filetypes=[("Code files", f"*{ext}"), ("All files", "*.*")],
            title="บันทึกโค้ดลงไฟล์",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)

    def _add_save_buttons(self, text: str) -> None:
        """Find ```lang ... ``` and add sleek Save buttons in the header."""
        for b in self._save_btns:
            b.destroy()
        self._save_btns.clear()

        blocks = re.findall(r"```(\w+)?\n([\s\S]*?)```", text)
        for lang, code in blocks:
            lang = lang or "code"
            lbl = f"💾 {lang}"
            btn = tk.Button(
                self._hdr_frame,
                text=lbl,
                bg=T["bg_btn"],
                fg=T["accent"],
                activebackground=T["bg3"],
                activeforeground=T["accent_hover"],
                font=FONT_TINY,
                relief="flat",
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda c=code, l=lang: self._save_code(c.strip(), l),
            )
            btn.pack(side="right", padx=(0, 6))
            self._save_btns.append(btn)

    # ── Antigravity Process / Thinking Methods ───────────────────────────────
    def _toggle_process(self) -> None:
        """Toggle showing/hiding the step-by-step reasoning & tool execution list."""
        self._process_expanded = not self._process_expanded
        if self._process_expanded:
            self._steps_frame.pack(fill="x", pady=(0, 6), after=self._process_header_btn)
            self._update_process_button_label(expanded=True)
        else:
            self._steps_frame.pack_forget()
            self._update_process_button_label(expanded=False)

    def _update_process_button_label(self, expanded: bool) -> None:
        arrow = "▾" if expanded else "▸"
        count = len(self._steps)
        elapsed = getattr(self, "_elapsed_sec", 0.0)
        if elapsed > 0:
            time_str = f"{elapsed:.1f}s"
        else:
            time_str = f"{time.monotonic() - self._start_time:.1f}s" if self._start_time else ""

        if self._is_thinking:
            txt = f"⚡ กำลังคิดและประมวลผล... ({time_str})" if time_str else "⚡ กำลังคิดและประมวลผล..."
            if count > 0:
                txt += f"  [{count} ขั้นตอน]"
        else:
            txt = f"{arrow} Worked for {time_str} ({count} steps)" if count > 0 else f"{arrow} Worked for {time_str}"

        self._process_header_btn.configure(text=txt)

    def add_step(self, title: str, detail: str = "", status: str = "done") -> None:
        """Add an Antigravity-style process step card."""
        self._steps.append({"title": title, "detail": detail, "status": status, "time": time.time()})
        self._process_container.pack(fill="x", pady=(0, 6), before=self.body)
        self._process_header_btn.pack(fill="x", pady=(0, 4))
        self._render_step_item(title, detail, status)
        self._update_process_button_label(expanded=self._process_expanded)

    def _render_step_item(self, title: str, detail: str, status: str) -> None:
        """Render a step item inside _steps_frame."""
        item = tk.Frame(self._steps_frame, bg=T.get("bg2", "#282a2c"), pady=2)
        item.pack(fill="x", pady=(0, 4))

        icon = "✔" if status == "done" else ("❌" if status == "error" else "⚙")
        color = T.get("accent", "#8ab4f8") if status == "done" else (T.get("err_hdr", "#f28b82") if status == "error" else T.get("sub", "#9aa0a6"))

        title_row = tk.Frame(item, bg=T.get("bg2", "#282a2c"))
        title_row.pack(fill="x")

        tk.Label(title_row, text=f"{icon} {title}", font=FONT_BOLD, bg=T.get("bg2", "#282a2c"), fg=color, anchor="w").pack(side="left")

        if detail:
            code_box = tk.Text(
                item,
                bg=T.get("code_bg", "#161718"),
                fg=T.get("code_fg", "#d1d7e0"),
                font=FONT_MONO,
                wrap="none",
                height=min(6, max(2, len(detail.split("\n")))),
                relief="flat",
                bd=0,
                padx=8,
                pady=4,
            )
            code_box.insert("1.0", detail[:800] + ("..." if len(detail) > 800 else ""))
            code_box.configure(state="disabled")
            code_box.pack(fill="x", pady=(3, 0))

    def _animate_spinner(self) -> None:
        """Continuous rotating spinner animation with elapsed time while thinking."""
        if not self._is_thinking:
            return
        try:
            if not self.winfo_exists():
                return
            frame = _SPINNER_FRAMES[self._spinner_idx % len(_SPINNER_FRAMES)]
            self._spinner_idx += 1
            elapsed = time.monotonic() - self._start_time if self._start_time else 0.0
            count = len(self._steps)
            step_str = f"  [{count} ขั้นตอน]" if count > 0 else ""
            self._process_header_btn.configure(text=f"{frame} {self._thinking_text} ({elapsed:.1f}s){step_str}")
            self.after(90, self._animate_spinner)
        except Exception:
            pass

    def update_thinking_status(self, text: str) -> None:
        """Update live status text while thinking."""
        self._thinking_text = text
        self._process_container.pack(fill="x", pady=(0, 6), before=self.body)
        self._process_header_btn.pack(fill="x", pady=(0, 4))
        frame = _SPINNER_FRAMES[self._spinner_idx % len(_SPINNER_FRAMES)]
        elapsed = time.monotonic() - self._start_time if self._start_time else 0.0
        self._process_header_btn.configure(text=f"{frame} {text} ({elapsed:.1f}s)")

    def finish_processing(self, final_text: str, role: str = "AI", elapsed_sec: float = 0.0) -> None:
        """Called when AI generation and tool calling loops finish."""
        self._is_thinking = False
        self._elapsed_sec = elapsed_sec
        self.set_role(role)
        self.update_content(final_text)

        if self._steps or elapsed_sec > 0:
            self._process_container.pack(fill="x", pady=(0, 6), before=self.body)
            self._process_header_btn.pack(fill="x", pady=(0, 4))
            self._update_process_button_label(expanded=False)
            self._steps_frame.pack_forget()
        else:
            self._process_container.pack_forget()
            self._process_header_btn.pack_forget()

    def append_stream_chunk(self, chunk: str) -> None:
        """Append token chunk in real time with auto-fit and scrolling."""
        self._content += chunk
        self.body.configure(state="normal")
        self.body.insert(tk.END, chunk)
        self.body.configure(state="disabled")
        self.body.see(tk.END)
        self._fit()

    def update_content(self, text: str) -> None:
        self._content = text
        self.body.configure(state="normal")
        self.body.delete("1.0", tk.END)
        self.body.insert("1.0", text)
        self._apply_markdown_tags(text)
        self.body.configure(state="disabled")
        self._add_save_buttons(text)
        self.after(10, self._fit)

    def set_role(self, role: str) -> None:
        self._role_raw = role
        self._role_kind = "error" if "Error" in role else ("user" if role.startswith("You") else "ai")
        icon_photo = _get_feather_icon() if self._role_kind == "ai" else None
        if icon_photo:
            self._role_icon_lbl.configure(image=icon_photo, bg=self._bg_card)
            self._role_icon_lbl.pack(side="left", padx=(0, 4), before=self._role_lbl)
        else:
            self._role_icon_lbl.pack_forget()

        self._role_lbl.configure(
            text=_format_badge_text(role, has_icon=icon_photo is not None),
            bg=self._bg_card,
            fg=self._hdr_color,
        )

    def apply_theme(self) -> None:
        self._bg_card = T[{"user": "bg_user", "ai": "bg_ai", "error": "bg_err"}[self._role_kind]]
        self._hdr_color = T[{"user": "user_hdr", "ai": "ai_hdr", "error": "err_hdr"}[self._role_kind]]
        self.configure(bg=self._bg_card, highlightbackground=T["border"])
        self._hdr_frame.configure(bg=self._bg_card)
        if hasattr(self, "_role_icon_lbl"):
            self._role_icon_lbl.configure(bg=self._bg_card)
        self._role_lbl.configure(bg=self._bg_card, fg=self._hdr_color)
        self._copy_btn.configure(
            bg=T["bg_btn"],
            fg=T["fg"],
            activebackground=T["bg3"],
            activeforeground=T["fg"],
        )
        self._process_container.configure(bg=self._bg_card)
        self._process_header_btn.configure(bg=T["bg2"], fg=T["sub"], activebackground=T["bg3"], activeforeground=T["fg"])
        self._steps_frame.configure(bg=T["bg2"], highlightbackground=T["border"])
        self.body.configure(bg=self._bg_card, fg=T["fg"])
        self._configure_tags()
        self._apply_markdown_tags(self._content)

        if hasattr(self, "_img_label"):
            self._img_label.configure(bg=self._bg_card)

        for btn in self._save_btns:
            btn.configure(
                bg=T["bg_btn"],
                fg=T["accent"],
                activebackground=T["bg3"],
                activeforeground=T["accent_hover"],
            )
