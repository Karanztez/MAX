"""
message_bubble.py — Gemini blog-style message bubble card widget for chat display.
"""

import os
import re
import tkinter as tk
from tkinter import filedialog
from typing import Optional, TYPE_CHECKING

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


def _format_badge_text(role: str) -> str:
    """Format role into MAX badges with feather icon."""
    if "Error" in role:
        return f"⚠️ {role}"
    if role.startswith("You"):
        return "👤 คุณ"
    if "🛠" in role:
        return "🪶 MAX  [Tools]"
    if role.startswith("AI"):
        return "🪶 MAX"
    return role


class MessageBubble(tk.Frame):
    def __init__(self, parent: tk.Widget, role: str, content: str,
                 bg_card: str, hdr_color: str,
                 img: Optional["Image.Image"] = None) -> None:
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
        self.pack(fill="x", padx=16, pady=(0, 10))

        # Header bar
        self._hdr_frame = tk.Frame(self, bg=bg_card)
        self._hdr_frame.pack(fill="x", pady=(0, 6))

        # Role badge
        badge_text = _format_badge_text(role)
        self._role_lbl = tk.Label(
            self._hdr_frame,
            text=badge_text,
            bg=bg_card,
            fg=hdr_color,
            font=FONT_HDR,
        )
        self._role_lbl.pack(side="left")

        # Copy button (Gemini sleek flat style)
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

        # Body Text (Blog-style typography with line spacing)
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
        self._role_lbl.configure(text=_format_badge_text(role))
        self._role_kind = "error" if "Error" in role else ("user" if role.startswith("You") else "ai")

    def apply_theme(self) -> None:
        self._bg_card = T[{"user": "bg_user", "ai": "bg_ai", "error": "bg_err"}[self._role_kind]]
        self._hdr_color = T[{"user": "user_hdr", "ai": "ai_hdr", "error": "err_hdr"}[self._role_kind]]
        self.configure(bg=self._bg_card, highlightbackground=T["border"])
        self._hdr_frame.configure(bg=self._bg_card)
        self._role_lbl.configure(bg=self._bg_card, fg=self._hdr_color)
        self._copy_btn.configure(
            bg=T["bg_btn"],
            fg=T["fg"],
            activebackground=T["bg3"],
            activeforeground=T["fg"],
        )
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
