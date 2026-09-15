"""
crop_dialog.py — Free-form crop editor with draggable edges, corners and selection.
"""

import tkinter as tk
from typing import Any, Optional, TYPE_CHECKING

try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_TITLE


class CropDialog(tk.Toplevel):
    """Free-form crop editor with draggable edges, corners and selection."""

    HANDLE = 9
    MIN_SIZE = 24

    def __init__(self, parent: tk.Misc, image: "Image.Image", on_apply: Any) -> None:
        super().__init__(parent)
        self._source = image.copy()
        self._on_apply = on_apply
        self._photo = None
        self._drag_mode: Optional[str] = None
        self._drag_start = (0.0, 0.0)
        self._box_start = (0.0, 0.0, 0.0, 0.0)

        self.title("ครอปรูปภาพ")
        self.geometry("900x680")
        self.minsize(620, 500)
        self.configure(bg=T["bg"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        head = tk.Frame(self, bg=T["bg"], padx=22, pady=16)
        head.pack(fill="x")
        tk.Label(head, text="ครอปรูปภาพ", bg=T["bg"], fg=T["fg"],
                 font=FONT_TITLE).pack(anchor="w")
        tk.Label(head, text="ลากด้านในเพื่อย้าย • ลากขอบหรือมุมเพื่อปรับขนาดได้อิสระ",
                 bg=T["bg"], fg=T["fg_dim"], font=FONT_TINY).pack(anchor="w", pady=(4, 0))

        self.canvas = tk.Canvas(self, bg="#07090d", highlightthickness=1,
                                highlightbackground=T["border"], cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=22)
        self.canvas.bind("<Configure>", self._render)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)

        footer = tk.Frame(self, bg=T["bg"], padx=22, pady=16)
        footer.pack(fill="x")
        self._size_var = tk.StringVar()
        tk.Label(footer, textvariable=self._size_var, bg=T["bg"], fg=T["fg_dim"],
                 font=FONT_TINY).pack(side="left")
        tk.Button(footer, text="ยกเลิก", command=self.destroy, bg=T["bg_btn"], fg=T["fg"],
                  activebackground=T["bg3"], activeforeground=T["fg"], relief="flat",
                  padx=18, pady=8, cursor="hand2", font=FONT).pack(side="right")
        tk.Button(footer, text="ครอปภาพ", command=self._apply, bg=T["accent"], fg="#ffffff",
                  activebackground=T["accent_hover"], activeforeground="#ffffff", relief="flat",
                  padx=20, pady=8, cursor="hand2", font=FONT_BOLD).pack(side="right", padx=(0, 8))
        tk.Button(footer, text="รีเซ็ต", command=self._reset, bg=T["bg"], fg=T["fg_dim"],
                  activebackground=T["bg2"], activeforeground=T["fg"], relief="flat",
                  padx=14, pady=8, cursor="hand2", font=FONT).pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._apply())
        self.after(20, self._initial_render)

    def _initial_render(self) -> None:
        self.update_idletasks()
        self._render(reset=True)

    def _render(self, _event: object = None, reset: bool = False) -> None:
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        iw, ih = self._source.size
        scale = min((cw - 32) / iw, (ch - 32) / ih, 1.0)
        self._scale = max(scale, 0.01)
        dw, dh = max(1, int(iw * self._scale)), max(1, int(ih * self._scale))
        self._origin = ((cw - dw) / 2, (ch - dh) / 2)
        preview = self._source.resize((dw, dh), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(preview)
        self.canvas.delete("all")
        ox, oy = self._origin
        self.canvas.create_image(ox, oy, image=self._photo, anchor="nw", tags="image")
        if reset or not hasattr(self, "_box"):
            margin = min(30, dw * .08, dh * .08)
            self._box = [ox + margin, oy + margin, ox + dw - margin, oy + dh - margin]
        else:
            self._box = [max(ox, min(ox + dw, self._box[0])),
                         max(oy, min(oy + dh, self._box[1])),
                         max(ox, min(ox + dw, self._box[2])),
                         max(oy, min(oy + dh, self._box[3]))]
        self._draw_overlay()

    def _reset(self) -> None:
        self._render(reset=True)

    def _draw_overlay(self) -> None:
        self.canvas.delete("crop")
        x1, y1, x2, y2 = self._box
        ox, oy = self._origin
        iw, ih = self._source.size
        rx, by = ox + iw * self._scale, oy + ih * self._scale
        shade = dict(fill="#000000", stipple="gray50", outline="")
        self.canvas.create_rectangle(ox, oy, rx, y1, tags="crop", **shade)
        self.canvas.create_rectangle(ox, y2, rx, by, tags="crop", **shade)
        self.canvas.create_rectangle(ox, y1, x1, y2, tags="crop", **shade)
        self.canvas.create_rectangle(x2, y1, rx, y2, tags="crop", **shade)
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=T["accent"], width=2, tags="crop")
        for a, b, c, d in ((x1, y1, x1, y2), (x2, y1, x2, y2),
                           (x1, y1, x2, y1), (x1, y2, x2, y2)):
            self.canvas.create_line(a, b, c, d, fill="#ffffff", width=1, tags="crop")
        for px, py in ((x1, y1), ((x1+x2)/2, y1), (x2, y1),
                       (x1, (y1+y2)/2), (x2, (y1+y2)/2),
                       (x1, y2), ((x1+x2)/2, y2), (x2, y2)):
            h = self.HANDLE
            self.canvas.create_rectangle(px-h/2, py-h/2, px+h/2, py+h/2,
                                         fill="#ffffff", outline=T["accent"], tags="crop")
        w = max(1, round((x2-x1) / self._scale)); h = max(1, round((y2-y1) / self._scale))
        self._size_var.set(f"ขนาดผลลัพธ์: {w} × {h} px")

    def _hit_test(self, x: float, y: float) -> Optional[str]:
        x1, y1, x2, y2 = self._box; h = self.HANDLE + 4
        near_l, near_r = abs(x-x1) <= h, abs(x-x2) <= h
        near_t, near_b = abs(y-y1) <= h, abs(y-y2) <= h
        if near_l and near_t: return "nw"
        if near_r and near_t: return "ne"
        if near_l and near_b: return "sw"
        if near_r and near_b: return "se"
        if near_l and y1 <= y <= y2: return "w"
        if near_r and y1 <= y <= y2: return "e"
        if near_t and x1 <= x <= x2: return "n"
        if near_b and x1 <= x <= x2: return "s"
        if x1 < x < x2 and y1 < y < y2: return "move"
        return None

    def _press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._drag_mode = self._hit_test(event.x, event.y)
        self._drag_start = (event.x, event.y)
        self._box_start = tuple(self._box)
        if self._drag_mode is None:
            ox, oy = self._origin
            iw, ih = self._source.size
            right, bottom = ox + iw*self._scale, oy + ih*self._scale
            if ox <= event.x <= right and oy <= event.y <= bottom:
                self._drag_mode = "new"
                self._box = [event.x, event.y, event.x, event.y]
                self._box_start = tuple(self._box)

    def _drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._drag_mode: return
        ox, oy = self._origin; iw, ih = self._source.size
        rx, by = ox + iw*self._scale, oy + ih*self._scale
        sx, sy = self._drag_start; dx, dy = event.x-sx, event.y-sy
        x1, y1, x2, y2 = self._box_start; mode = self._drag_mode
        if mode == "new":
            px = max(ox, min(rx, event.x)); py = max(oy, min(by, event.y))
            self._box = [min(sx, px), min(sy, py), max(sx, px), max(sy, py)]
        elif mode == "move":
            dx = max(ox-x1, min(rx-x2, dx)); dy = max(oy-y1, min(by-y2, dy))
            self._box = [x1+dx, y1+dy, x2+dx, y2+dy]
        else:
            if "w" in mode: x1 = max(ox, min(x2+self.MIN_SIZE*-1, event.x))
            if "e" in mode: x2 = min(rx, max(x1+self.MIN_SIZE, event.x))
            if "n" in mode: y1 = max(oy, min(y2-self.MIN_SIZE, event.y))
            if "s" in mode: y2 = min(by, max(y1+self.MIN_SIZE, event.y))
            self._box = [x1, y1, x2, y2]
        self._draw_overlay()

    def _release(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._box[2]-self._box[0] < self.MIN_SIZE or self._box[3]-self._box[1] < self.MIN_SIZE:
            self._render(reset=True)
        self._drag_mode = None

    def _apply(self) -> None:
        x1, y1, x2, y2 = self._box; ox, oy = self._origin
        iw, ih = self._source.size
        crop = (max(0, round((x1-ox)/self._scale)), max(0, round((y1-oy)/self._scale)),
                min(iw, round((x2-ox)/self._scale)), min(ih, round((y2-oy)/self._scale)))
        self._on_apply(self._source.crop(crop))
        self.destroy()
