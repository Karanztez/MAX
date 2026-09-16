"""
src/ui/tabs/media_tab.py — Dedicated High-Resolution Image & Video Viewer Tab in MAX GUI.
Supports zoom, pan, rotation, save as, open in default app, and folder reveal.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional, TYPE_CHECKING

try:
    from PIL import Image, ImageTk, ImageOps  # type: ignore[import-untyped]
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    from ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_HDR, FONT_MONO
except (ImportError, ModuleNotFoundError):
    from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_HDR, FONT_MONO  # type: ignore[no-redef]


class MediaViewerTab(tk.Frame):
    """
    Dedicated Viewer Tab for AI-generated images or videos.
    """

    def __init__(
        self,
        parent: tk.Widget,
        file_path: str,
        title: Optional[str] = None,
        media_type: str = "image",
        prompt: str = "",
        on_close: Optional[Callable[[MediaViewerTab], None]] = None,
    ) -> None:
        super().__init__(parent, bg=T["bg"])
        self.file_path = str(Path(file_path).resolve())
        self.media_type = media_type.lower()
        self.prompt = prompt
        self.on_close = on_close

        base_name = os.path.basename(self.file_path)
        self.title_text = title or (f"🎨 {base_name}" if self.media_type == "image" else f"🎬 {base_name}")

        self._zoom_factor: float = 1.0
        self._rotation_angle: int = 0
        self._fit_to_window: bool = True
        self._original_pil: Optional[Image.Image] = None
        self._current_photo: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self._load_media()

    # ── UI Construction ─────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        # Top Toolbar
        self._toolbar = tk.Frame(self, bg=T["bg2"], pady=6, padx=12, highlightthickness=1, highlightbackground=T["border"])
        self._toolbar.pack(fill="x", side="top")

        # Left: Title + Path badge
        self._title_lbl = tk.Label(
            self._toolbar,
            text=self.title_text,
            font=FONT_HDR,
            bg=T["bg2"],
            fg=T["accent"],
        )
        self._title_lbl.pack(side="left", padx=(0, 10))

        if self.prompt:
            p_short = self.prompt if len(self.prompt) <= 45 else self.prompt[:42] + "..."
            self._prompt_lbl = tk.Label(
                self._toolbar,
                text=f'"{p_short}"',
                font=FONT_TINY,
                bg=T["bg2"],
                fg=T["sub"],
            )
            self._prompt_lbl.pack(side="left", padx=(0, 10))

        # Right: Action Buttons
        self._close_btn = tk.Button(
            self._toolbar,
            text="✕ ปิดแท็บ",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["err_hdr"],
            activebackground=T["bg_btn"],
            activeforeground=T["err_hdr"],
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._handle_close,
        )
        self._close_btn.pack(side="right")

        if self.media_type == "image":
            self._build_image_toolbar()
        else:
            self._build_video_toolbar()

        # Bottom Info Bar
        self._info_bar = tk.Frame(self, bg=T["bg2"], pady=4, padx=12, highlightthickness=1, highlightbackground=T["border"])
        self._info_bar.pack(fill="x", side="bottom")

        self._info_lbl = tk.Label(
            self._info_bar,
            text="กำลังโหลดข้อมูลสื่อ...",
            font=FONT_TINY,
            bg=T["bg2"],
            fg=T["sub"],
        )
        self._info_lbl.pack(side="left")

        # Central Viewport
        self._viewport = tk.Frame(self, bg=T["bg"])
        self._viewport.pack(fill="both", expand=True)

        if self.media_type == "image":
            self._canvas = tk.Canvas(self._viewport, bg=T["bg"], highlightthickness=0)
            self._canvas.pack(fill="both", expand=True)
            self._canvas.bind("<Configure>", lambda _e: self._on_resize())
            self._canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        else:
            self._build_video_view()

    def _build_image_toolbar(self) -> None:
        self._open_ext_btn = tk.Button(
            self._toolbar,
            text="🖼 เปิดในระบบ",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._open_in_external_viewer,
        )
        self._open_ext_btn.pack(side="right", padx=3)

        self._folder_btn = tk.Button(
            self._toolbar,
            text="📂 โฟลเดอร์",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._open_containing_folder,
        )
        self._folder_btn.pack(side="right", padx=3)

        self._save_as_btn = tk.Button(
            self._toolbar,
            text="💾 บันทึกเป็น",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._save_as,
        )
        self._save_as_btn.pack(side="right", padx=3)

        self._rotate_btn = tk.Button(
            self._toolbar,
            text="↻ หมุนภาพ",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._rotate_image,
        )
        self._rotate_btn.pack(side="right", padx=3)

        self._fit_btn = tk.Button(
            self._toolbar,
            text="↔ พอดีจอ",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["accent"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._toggle_fit,
        )
        self._fit_btn.pack(side="right", padx=3)

        self._zoom_out_btn = tk.Button(
            self._toolbar,
            text="🔍-",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda: self._zoom(0.8),
        )
        self._zoom_out_btn.pack(side="right", padx=2)

        self._zoom_in_btn = tk.Button(
            self._toolbar,
            text="🔍+",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda: self._zoom(1.25),
        )
        self._zoom_in_btn.pack(side="right", padx=2)

    def _build_video_toolbar(self) -> None:
        self._play_btn = tk.Button(
            self._toolbar,
            text="▶ เล่นวิดีโอ (Default Player)",
            font=FONT_TINY,
            bg=T["accent"],
            fg=T["bg"],
            activebackground=T["accent_hover"],
            activeforeground=T["bg"],
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=self._open_in_external_viewer,
        )
        self._play_btn.pack(side="right", padx=3)

        self._folder_btn = tk.Button(
            self._toolbar,
            text="📂 โฟลเดอร์",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._open_containing_folder,
        )
        self._folder_btn.pack(side="right", padx=3)

        self._copy_path_btn = tk.Button(
            self._toolbar,
            text="📋 คัดลอก Path",
            font=FONT_TINY,
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._copy_path,
        )
        self._copy_path_btn.pack(side="right", padx=3)

    def _build_video_view(self) -> None:
        """Render a modern video player launch card in the central viewport."""
        card = tk.Frame(self._viewport, bg=T["bg2"], padx=24, pady=24, highlightthickness=1, highlightbackground=T["border"])
        card.place(relx=0.5, rely=0.5, anchor="center")

        icon_lbl = tk.Label(card, text="🎬", font=("Segoe UI Emoji", 48), bg=T["bg2"], fg=T["accent"])
        icon_lbl.pack(pady=(0, 10))

        vtitle = tk.Label(card, text=os.path.basename(self.file_path), font=FONT_HDR, bg=T["bg2"], fg=T["fg"])
        vtitle.pack(pady=(0, 6))

        if self.prompt:
            p_lbl = tk.Label(card, text=f'Prompt: "{self.prompt}"', font=FONT, bg=T["bg2"], fg=T["sub"], wraplength=520)
            p_lbl.pack(pady=(0, 14))

        action_frame = tk.Frame(card, bg=T["bg2"])
        action_frame.pack(pady=(6, 12))

        btn_play = tk.Button(
            action_frame,
            text="▶ เปิดเล่นวิดีโอทันที",
            font=FONT_BOLD,
            bg=T["accent"],
            fg=T["bg"],
            activebackground=T["accent_hover"],
            activeforeground=T["bg"],
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._open_in_external_viewer,
        )
        btn_play.pack(side="left", padx=6)

        btn_folder = tk.Button(
            action_frame,
            text="📂 เปิดโฟลเดอร์ไฟล์",
            font=FONT_BOLD,
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg_btn"],
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._open_containing_folder,
        )
        btn_folder.pack(side="left", padx=6)

        path_lbl = tk.Label(card, text=self.file_path, font=FONT_MONO, bg=T["bg2"], fg=T["sub"], wraplength=580)
        path_lbl.pack(pady=(10, 0))

    # ── Media Loading & Rendering ──────────────────────────────────────────
    def _load_media(self) -> None:
        if not os.path.exists(self.file_path):
            self._info_lbl.configure(text=f"⚠️ ไม่พบไฟล์: {self.file_path}", fg=T["err_hdr"])
            return

        size_bytes = os.path.getsize(self.file_path)
        size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / (1024 * 1024):.2f} MB"

        if self.media_type == "image" and _PIL_OK:
            try:
                self._original_pil = Image.open(self.file_path)
                w, h = self._original_pil.size
                self._info_lbl.configure(
                    text=f"ความละเอียด: {w} × {h} px  |  ขนาดไฟล์: {size_str}  |  ที่อยู่: {self.file_path}"
                )
                self.after(50, self._render_image)
            except Exception as ex:
                self._info_lbl.configure(text=f"⚠️ โหลดภาพไม่สำเร็จ: {ex}", fg=T["err_hdr"])
        else:
            self._info_lbl.configure(
                text=f"ประเภท: วิดีโอ MP4  |  ขนาดไฟล์: {size_str}  |  ที่อยู่: {self.file_path}"
            )

    def _render_image(self) -> None:
        if self._original_pil is None or not hasattr(self, "_canvas"):
            return

        canvas_w = max(100, self._canvas.winfo_width())
        canvas_h = max(100, self._canvas.winfo_height())

        img = self._original_pil
        if self._rotation_angle != 0:
            img = img.rotate(self._rotation_angle, expand=True)

        orig_w, orig_h = img.size

        if self._fit_to_window:
            scale_w = (canvas_w - 40) / orig_w
            scale_h = (canvas_h - 40) / orig_h
            scale = min(scale_w, scale_h, 1.0)
            self._zoom_factor = max(0.05, scale)

        target_w = max(1, int(orig_w * self._zoom_factor))
        target_h = max(1, int(orig_h * self._zoom_factor))

        resample_mode = getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)
        resized = img.resize((target_w, target_h), resample_mode)
        self._current_photo = ImageTk.PhotoImage(resized)

        self._canvas.delete("all")
        cx = canvas_w // 2
        cy = canvas_h // 2
        self._canvas.create_image(cx, cy, image=self._current_photo, anchor="center")

    def _on_resize(self) -> None:
        if self._fit_to_window:
            self._render_image()

    def _on_mouse_wheel(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if event.delta > 0:
            self._zoom(1.15)
        else:
            self._zoom(0.85)

    def _zoom(self, factor: float) -> None:
        self._fit_to_window = False
        if hasattr(self, "_fit_btn"):
            self._fit_btn.configure(fg=T["fg"])
        self._zoom_factor = max(0.1, min(5.0, self._zoom_factor * factor))
        self._render_image()

    def _toggle_fit(self) -> None:
        self._fit_to_window = not self._fit_to_window
        if self._fit_to_window:
            self._fit_btn.configure(fg=T["accent"])
        else:
            self._fit_btn.configure(fg=T["fg"])
            self._zoom_factor = 1.0
        self._render_image()

    def _rotate_image(self) -> None:
        self._rotation_angle = (self._rotation_angle - 90) % 360
        self._render_image()

    # ── Actions ─────────────────────────────────────────────────────────────
    def _save_as(self) -> None:
        if not os.path.exists(self.file_path):
            messagebox.showerror("ผิดพลาด", "ไม่พบไฟล์ต้นฉบับ")
            return
        ext = os.path.splitext(self.file_path)[1]
        dest = filedialog.asksaveasfilename(
            initialfile=os.path.basename(self.file_path),
            defaultextension=ext,
            filetypes=[("Image files", f"*{ext}"), ("All files", "*.*")],
            title="บันทึกรูปภาพเป็น...",
        )
        if dest:
            try:
                shutil.copy2(self.file_path, dest)
                messagebox.showinfo("สำเร็จ", f"บันทึกไฟล์เรียบร้อยแล้ว:\n{dest}")
            except Exception as ex:
                messagebox.showerror("ผิดพลาด", f"ไม่สามารถบันทึกไฟล์ได้: {ex}")

    def _copy_path(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.file_path)
        messagebox.showinfo("คัดลอกแล้ว", f"คัดลอก Path ไปยัง Clipboard เรียบร้อยแล้ว:\n{self.file_path}")

    def _open_in_external_viewer(self) -> None:
        if not os.path.exists(self.file_path):
            messagebox.showerror("ผิดพลาด", f"ไม่พบไฟล์: {self.file_path}")
            return
        try:
            if os.name == "nt":
                os.startfile(self.file_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.file_path])
            else:
                subprocess.Popen(["xdg-open", self.file_path])
        except Exception as ex:
            messagebox.showerror("ผิดพลาด", f"ไม่สามารถเปิดไฟล์ได้: {ex}")

    def _open_containing_folder(self) -> None:
        if not os.path.exists(self.file_path):
            messagebox.showerror("ผิดพลาด", f"ไม่พบไฟล์: {self.file_path}")
            return
        try:
            folder = os.path.dirname(os.path.abspath(self.file_path))
            if os.name == "nt":
                subprocess.Popen(f'explorer /select,"{os.path.abspath(self.file_path)}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", self.file_path])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as ex:
            messagebox.showerror("ผิดพลาด", f"ไม่สามารถเปิดโฟลเดอร์ได้: {ex}")

    def _handle_close(self) -> None:
        if self.on_close:
            self.on_close(self)
        else:
            self.destroy()

    def apply_theme(self) -> None:
        """Update colors on theme toggle."""
        self.configure(bg=T["bg"])
        self._toolbar.configure(bg=T["bg2"], highlightbackground=T["border"])
        self._title_lbl.configure(bg=T["bg2"], fg=T["accent"])
        if hasattr(self, "_prompt_lbl"):
            self._prompt_lbl.configure(bg=T["bg2"], fg=T["sub"])
        self._info_bar.configure(bg=T["bg2"], highlightbackground=T["border"])
        self._info_lbl.configure(bg=T["bg2"], fg=T["sub"])
        if hasattr(self, "_canvas"):
            self._canvas.configure(bg=T["bg"])
            self._render_image()
