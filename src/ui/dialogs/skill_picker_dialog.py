"""
skill_picker_dialog.py — Dialog for enabling/disabling Prompt Skills with auto-apply and scrolling.
"""

import tkinter as tk
from typing import Any
from src.core.skill_manager import SkillManager
from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_TITLE
from src.ui.widgets.scrollable_frame import ScrollableFrame


class SkillPickerDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, manager: SkillManager,
                 selected: set[str], on_apply: Any) -> None:
        super().__init__(parent)
        self._manager = manager
        self._selected = set(selected)
        self._on_apply = on_apply
        self._vars: dict[str, tk.BooleanVar] = {}

        self.title("จัดการสกิล (Prompt Skills)")
        self.geometry("540x520")
        self.minsize(440, 380)
        self.configure(bg=T["bg"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # Header
        head = tk.Frame(self, bg=T["bg"], padx=20, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="🪶 Prompt Skills", bg=T["bg"], fg=T["fg"],
                 font=FONT_TITLE).pack(side="left")

        tk.Button(
            head, text="↻ รีโหลด", command=self._reload,
            bg=T["bg_btn"], fg=T["fg"], activebackground=T["bg3"],
            activeforeground=T["fg"], relief="flat", font=FONT_TINY,
            padx=10, pady=4, cursor="hand2"
        ).pack(side="right")

        self._subtitle = tk.Label(
            self,
            text=f"เลือกคำสั่งเสริมสำหรับแท็บนี้ (มีผลทันที) • เปิดใช้งานอยู่: {len(self._selected)} สกิล",
            bg=T["bg"], fg=T["fg_dim"], font=FONT_TINY, anchor="w"
        )
        self._subtitle.pack(fill="x", padx=20, pady=(0, 10))

        # Scrollable skill list container
        self._scroll = ScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Pinned Footer
        footer = tk.Frame(self, bg=T["bg"], padx=20, pady=12, highlightthickness=1, highlightbackground=T["border"])
        footer.pack(fill="x", side="bottom")

        tk.Button(
            footer, text="ปิดหน้าต่าง", command=self.destroy,
            bg=T["accent"], fg="#ffffff", activebackground=T["accent_hover"],
            activeforeground="#ffffff", relief="flat", font=FONT_BOLD,
            padx=18, pady=6, cursor="hand2"
        ).pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())
        self._reload()

    def _reload(self) -> None:
        self._manager.refresh()
        for child in self._scroll.inner.winfo_children():
            child.destroy()
        self._vars.clear()

        if not self._manager.skills:
            tk.Label(self._scroll.inner, text="ยังไม่พบ Skill ในโฟลเดอร์ skills/", bg=T["bg"],
                     fg=T["fg_dim"], font=FONT).pack(pady=40)
            return

        for skill in self._manager.skills.values():
            is_active = skill.skill_id in self._selected
            var = tk.BooleanVar(value=is_active)
            self._vars[skill.skill_id] = var

            # Card row
            row = tk.Frame(
                self._scroll.inner,
                bg=T["bg2"],
                padx=14,
                pady=12,
                highlightthickness=1,
                highlightbackground=T["border"],
                cursor="hand2"
            )
            row.pack(fill="x", pady=(0, 8))

            check = tk.Checkbutton(
                row,
                variable=var,
                bg=T["bg2"],
                activebackground=T["bg2"],
                selectcolor=T["bg3"],
                fg=T["accent"],
                bd=0,
                highlightthickness=0,
                cursor="hand2",
                command=self._on_toggle,
            )
            check.pack(side="left", padx=(0, 10))

            text_frame = tk.Frame(row, bg=T["bg2"], cursor="hand2")
            text_frame.pack(side="left", fill="x", expand=True)

            name_lbl = tk.Label(
                text_frame, text=skill.name, bg=T["bg2"], fg=T["fg"],
                font=FONT_BOLD, anchor="w", cursor="hand2"
            )
            name_lbl.pack(fill="x")

            desc_lbl = tk.Label(
                text_frame, text=skill.description or skill.skill_id,
                bg=T["bg2"], fg=T["fg_dim"], font=FONT_TINY,
                anchor="w", wraplength=420, justify="left", cursor="hand2"
            )
            desc_lbl.pack(fill="x", pady=(3, 0))

            # Clicking anywhere on the row toggles the checkbox
            def _toggle_var(_e: object, v=var) -> None:
                v.set(not v.get())
                self._on_toggle()

            row.bind("<Button-1>", _toggle_var)
            text_frame.bind("<Button-1>", _toggle_var)
            name_lbl.bind("<Button-1>", _toggle_var)
            desc_lbl.bind("<Button-1>", _toggle_var)

        self._update_subtitle()

    def _on_toggle(self) -> None:
        """Auto-apply selected skills immediately upon toggle."""
        self._selected = {skill_id for skill_id, var in self._vars.items() if var.get()}
        self._on_apply(self._selected)
        self._update_subtitle()

    def _update_subtitle(self) -> None:
        count = len(self._selected)
        self._subtitle.configure(
            text=f"เลือกคำสั่งเสริมสำหรับแท็บนี้ (มีผลทันที) • เปิดใช้งานอยู่: {count} สกิล"
        )
