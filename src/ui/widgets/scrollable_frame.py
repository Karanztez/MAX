"""
scrollable_frame.py — Reusable smooth-scrolling frame widget.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any

try:
    from ui.themes import T
except (ImportError, ModuleNotFoundError):
    from src.ui.themes import T  # type: ignore[no-redef]


class ScrollableFrame(tk.Frame):
    def __init__(self, parent: tk.Misc, **kw: Any) -> None:
        super().__init__(parent, bg=T["bg"], **kw)
        self.canvas = tk.Canvas(self, bg=T["bg"], highlightthickness=0)
        self._sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._sb.set)
        self._sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=T["bg"])
        self._win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>",   self._wheel)
        self.canvas.bind_all("<Button-5>",   self._wheel)

    def _on_inner(self, _: object) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, e: tk.Event) -> None:  # type: ignore[type-arg]
        self.canvas.itemconfig(self._win_id, width=e.width)

    def _wheel(self, e: tk.Event) -> None:  # type: ignore[type-arg]
        d = -1*(e.delta//120) if e.delta else (1 if e.num == 5 else -1)
        self.canvas.yview_scroll(d, "units")

    def scroll_bottom(self) -> None:
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def apply_theme(self) -> None:
        self.configure(bg=T["bg"])
        self.canvas.configure(bg=T["bg"])
        self.inner.configure(bg=T["bg"])
