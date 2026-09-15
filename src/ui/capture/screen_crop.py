"""
screen_crop.py — Garena-style full-screen capture overlay with drawing and text tools.
"""

import tkinter as tk
from tkinter import simpledialog
from typing import Any, Optional, TYPE_CHECKING

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


class ScreenCropOverlay(tk.Toplevel):
    """Garena-style capture overlay: press, drag freely, and release to crop."""

    HANDLE = 10
    MIN_SIZE = 8

    def __init__(self, parent: tk.Misc, screenshot: "Image.Image",
                 on_apply: Any, on_cancel: Any) -> None:
        super().__init__(parent)
        self._source = screenshot
        self._on_apply = on_apply
        self._on_cancel = on_cancel
        self._box: Optional[list[float]] = None
        self._mode: Optional[str] = None
        self._start = (0.0, 0.0)
        self._box_start = (0.0, 0.0, 0.0, 0.0)
        self._closed = False
        self._tool = "select"
        self._draw_color = "#ff3b5c"
        self._draw_size = 4
        self._annotations: list[dict[str, Any]] = []
        self._current_points: list[tuple[float, float]] = []
        self._toolbar: Optional[tk.Frame] = None
        self._toolbar_window: Optional[int] = None

        # Build the complete overlay while hidden to prevent a white Tk window flash.
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.configure(bg="#000000")
        width, height = parent.winfo_screenwidth(), parent.winfo_screenheight()
        self.geometry(f"{width}x{height}+0+0")
        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after_idle(self._show_ready)

    def _show_ready(self) -> None:
        self.deiconify()
        self.update_idletasks()
        self.after(20, self._finish_show)

    def _finish_show(self) -> None:
        self.update_idletasks()
        if self.canvas.winfo_width() <= 2 or self.canvas.winfo_height() <= 2:
            self.after(20, self._finish_show)
            return
        self._render()
        self.attributes("-alpha", 1.0)
        self.lift()
        self.grab_set()
        self.focus_force()

    def _render(self, _event: object = None) -> None:
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        if cw <= 2 or ch <= 2:
            self.after(10, self._render)
            return
        self._scale_x = self._source.width / cw
        self._scale_y = self._source.height / ch
        preview = self._source.resize((cw, ch), Image.Resampling.LANCZOS).convert("RGB")
        dimmed = Image.blend(preview, Image.new("RGB", preview.size, "#000000"), 0.18)
        self._photo = ImageTk.PhotoImage(dimmed)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw", tags="screen")
        self._draw()

    def _draw(self) -> None:
        self.canvas.delete("crop")
        if self._box is None:
            return
        x1, y1, x2, y2 = self._box
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#ffffff", width=1, tags="crop")
        self.canvas.create_rectangle(x1+1, y1+1, x2-1, y2-1,
                                     outline="#6676ff", width=1, tags="crop")
        width = round((x2-x1) * self._scale_x)
        height = round((y2-y1) * self._scale_y)
        label_y = y1 - 18 if y1 > 35 else y2 + 18
        self.canvas.create_text(x1, label_y, anchor="w", text=f"{width} × {height} px",
                                fill="#ffffff", font=("Segoe UI", 10, "bold"), tags="crop")

    def _show_toolbar(self) -> None:
        if self._box is None:
            return
        if self._toolbar is not None:
            self._toolbar.destroy()
        self.canvas.delete("toolbar")
        bar = tk.Frame(self.canvas, bg="#151922", padx=5, pady=5,
                       highlightthickness=1, highlightbackground="#3a4252")
        self._toolbar = bar
        self._tool_buttons: dict[str, tk.Button] = {}

        def icon(text: str, command: Any, *, fg: str = "#f2f4f8",
                 bg: str = "#242b38", font: tuple = ("Segoe UI Symbol", 12)) -> tk.Button:
            button = tk.Button(bar, text=text, command=command, bg=bg, fg=fg,
                               activebackground="#343d4e", activeforeground="#ffffff",
                               font=font, relief="flat", bd=0, padx=8, pady=4,
                               cursor="hand2", takefocus=False)
            button.pack(side="left", padx=2)
            return button

        self._tool_buttons["select"] = icon("▣", lambda: self._set_tool("select"))
        self._tool_buttons["pen"] = icon("✎", lambda: self._set_tool("pen"))
        self._tool_buttons["text"] = icon("T", lambda: self._set_tool("text"),
                                            font=("Segoe UI", 11, "bold"))
        icon("↶", self._undo)

        tk.Frame(bar, bg="#3a4252", width=1).pack(side="left", fill="y", padx=4)
        for color in ("#ff3b5c", "#ffbf3c", "#45d483", "#49a7ff", "#ffffff", "#17191f"):
            icon("●", lambda c=color: self._set_color(c), fg=color,
                 font=("Segoe UI Symbol", 12))

        tk.Frame(bar, bg="#3a4252", width=1).pack(side="left", fill="y", padx=4)
        icon("−", lambda: self._change_size(-1), font=("Segoe UI", 12, "bold"))
        self._size_var = tk.StringVar(value=str(self._draw_size))
        tk.Label(bar, textvariable=self._size_var, bg="#151922", fg="#f2f4f8",
                 font=("Segoe UI", 9), width=2).pack(side="left")
        icon("＋", lambda: self._change_size(1), font=("Segoe UI", 11, "bold"))

        tk.Frame(bar, bg="#3a4252", width=1).pack(side="left", fill="y", padx=4)
        icon("✓", self._apply, bg="#5965dc", font=("Segoe UI", 12, "bold"))
        icon("✕", self._cancel, fg="#ff7892", font=("Segoe UI", 11, "bold"))
        bar.update_idletasks()

        x1, y1, _x2, y2 = self._box
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        bx = max(8, min(cw-bar.winfo_reqwidth()-8, x1))
        if y2 + bar.winfo_reqheight() + 10 <= ch:
            by, anchor = y2 + 8, "nw"
        else:
            by, anchor = max(8, y1 - 8), "sw"
        self._toolbar_window = self.canvas.create_window(
            bx, by, window=bar, anchor=anchor, tags="toolbar"
        )
        self._set_tool("pen")

    def _set_tool(self, tool: str) -> None:
        self._tool = tool
        cursors = {"select": "crosshair", "pen": "pencil", "text": "xterm"}
        self.canvas.configure(cursor=cursors.get(tool, "crosshair"))
        for name, button in getattr(self, "_tool_buttons", {}).items():
            button.configure(bg="#5965dc" if name == tool else "#242b38")

    def _set_color(self, color: str) -> None:
        self._draw_color = color

    def _change_size(self, delta: int) -> None:
        sizes = (2, 4, 6, 10, 16, 24)
        index = min(range(len(sizes)), key=lambda i: abs(sizes[i]-self._draw_size))
        self._draw_size = sizes[max(0, min(len(sizes)-1, index+delta))]
        self._size_var.set(str(self._draw_size))

    def _inside_crop(self, x: float, y: float) -> bool:
        if self._box is None:
            return False
        x1, y1, x2, y2 = self._box
        return x1 <= x <= x2 and y1 <= y <= y2

    def _undo(self) -> None:
        if self._annotations:
            self._annotations.pop()
            self._redraw_annotations()

    def _redraw_annotations(self) -> None:
        self.canvas.delete("annotation")
        for item in self._annotations:
            if item["kind"] == "pen":
                points = item["points"]
                flat = [coord for point in points for coord in point]
                if len(flat) >= 4:
                    self.canvas.create_line(*flat, fill=item["color"], width=item["size"],
                                            capstyle=tk.ROUND, joinstyle=tk.ROUND,
                                            smooth=True, tags="annotation")
            elif item["kind"] == "text":
                self.canvas.create_text(item["x"], item["y"], text=item["text"],
                                        fill=item["color"], anchor="nw",
                                        font=("Segoe UI", item["size"], "bold"),
                                        tags="annotation")

    def _add_text(self, x: float, y: float) -> None:
        text_value = simpledialog.askstring("เพิ่มข้อความ", "ข้อความ:", parent=self)
        if not text_value:
            return
        item = {"kind": "text", "x": x, "y": y, "text": text_value,
                "color": self._draw_color, "size": max(14, self._draw_size * 4)}
        self._annotations.append(item)
        self._redraw_annotations()

    def _hit(self, x: float, y: float) -> Optional[str]:
        if self._box is None:
            return None
        x1, y1, x2, y2 = self._box; h = self.HANDLE + 5
        left, right = abs(x-x1) <= h, abs(x-x2) <= h
        top, bottom = abs(y-y1) <= h, abs(y-y2) <= h
        if left and top: return "nw"
        if right and top: return "ne"
        if left and bottom: return "sw"
        if right and bottom: return "se"
        if left and y1 <= y <= y2: return "w"
        if right and y1 <= y <= y2: return "e"
        if top and x1 <= x <= x2: return "n"
        if bottom and x1 <= x <= x2: return "s"
        if x1 < x < x2 and y1 < y < y2: return "move"
        return None

    def _press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._box is not None and self._tool == "pen" and self._inside_crop(event.x, event.y):
            self._mode = "pen"
            self._current_points = [(event.x, event.y)]
            return
        if self._box is not None and self._tool == "text" and self._inside_crop(event.x, event.y):
            self._mode = None
            self._add_text(event.x, event.y)
            return
        if self._tool != "select" and self._box is not None:
            return
        self._start = (event.x, event.y)
        self._mode = "new"
        self._box = [event.x, event.y, event.x, event.y]
        self._annotations.clear()
        self.canvas.delete("annotation")
        self.canvas.delete("toolbar")
        if self._toolbar is not None:
            self._toolbar.destroy()
            self._toolbar = None

    def _drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._mode is None:
            return
        if self._mode == "pen":
            if self._box is None:
                return
            x1, y1, x2, y2 = self._box
            px = max(x1, min(x2, event.x)); py = max(y1, min(y2, event.y))
            previous = self._current_points[-1]
            self._current_points.append((px, py))
            self.canvas.create_line(previous[0], previous[1], px, py,
                                    fill=self._draw_color, width=self._draw_size,
                                    capstyle=tk.ROUND, smooth=True, tags="annotation-preview")
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        px, py = max(0, min(cw, event.x)), max(0, min(ch, event.y))
        sx, sy = self._start
        self._box = [min(sx, px), min(sy, py), max(sx, px), max(sy, py)]
        self._draw()

    def _release(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._mode == "pen":
            if len(self._current_points) >= 2:
                self._annotations.append({"kind": "pen", "points": list(self._current_points),
                                          "color": self._draw_color, "size": self._draw_size})
            self._current_points = []
            self._mode = None
            self.canvas.delete("annotation-preview")
            self._redraw_annotations()
            return
        if self._box and (self._box[2]-self._box[0] < self.MIN_SIZE
                          or self._box[3]-self._box[1] < self.MIN_SIZE):
            self._box = None
            self._mode = None
            self._draw()
            return
        self._mode = None
        self._draw()
        self._show_toolbar()

    def _apply(self) -> None:
        if self._closed or self._box is None:
            return
        self._closed = True
        x1, y1, x2, y2 = self._box
        crop = (round(x1*self._scale_x), round(y1*self._scale_y),
                round(x2*self._scale_x), round(y2*self._scale_y))
        annotated = self._source.convert("RGB").copy()
        painter = ImageDraw.Draw(annotated)
        scale = (self._scale_x + self._scale_y) / 2
        for item in self._annotations:
            if item["kind"] == "pen":
                points = [(round(px*self._scale_x), round(py*self._scale_y))
                          for px, py in item["points"]]
                if len(points) >= 2:
                    painter.line(points, fill=item["color"],
                                 width=max(1, round(item["size"]*scale)), joint="curve")
            elif item["kind"] == "text":
                font_size = max(10, round(item["size"]*scale))
                try:
                    font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", font_size)
                except Exception:
                    font = ImageFont.load_default()
                painter.text((round(item["x"]*self._scale_x),
                              round(item["y"]*self._scale_y)),
                             item["text"], fill=item["color"], font=font)
        result = annotated.crop(crop)
        self.grab_release()
        self.destroy()
        self._on_apply(result)

    def _cancel(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.grab_release()
        self.destroy()
        self._on_cancel()
