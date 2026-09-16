"""
src/ui/widgets/context_menu.py — Universal Right-Click Context Menu for Text & Entry widgets.
Supports instant auto-copy on highlight + right-click, free Copy/Cut/Paste/Select All, and clipboard images.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

try:
    from ui.themes import T, FONT, FONT_BOLD, FONT_TINY
    from ui.clipboard import read_clipboard_text
except (ImportError, ModuleNotFoundError):
    from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY  # type: ignore[no-redef]
    from src.ui.clipboard import read_clipboard_text  # type: ignore[no-redef]


def _get_selected_text(widget: tk.Misc) -> str:
    """Retrieve currently selected text from Text or Entry widget if any."""
    try:
        if isinstance(widget, tk.Text):
            if widget.tag_ranges(tk.SEL):
                return widget.get(tk.SEL_FIRST, tk.SEL_LAST)
        elif isinstance(widget, (tk.Entry, ttk.Entry)):
            if widget.selection_present():  # type: ignore[attr-defined]
                return widget.selection_get()  # type: ignore[attr-defined]
    except Exception:
        pass
    return ""


def _select_all(widget: tk.Misc) -> None:
    """Select all text in widget."""
    try:
        if isinstance(widget, tk.Text):
            widget.tag_add(tk.SEL, "1.0", "end-1c")
            widget.mark_set(tk.INSERT, "1.0")
            widget.see(tk.INSERT)
            widget.focus_set()
        elif isinstance(widget, tk.Entry):
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
            widget.focus_set()
    except Exception:
        pass


def _copy_selected(widget: tk.Misc, text: str) -> None:
    """Copy given text to clipboard."""
    if not text:
        return
    try:
        widget.clipboard_clear()
        widget.clipboard_append(text)
    except Exception:
        pass


def _copy_all(widget: tk.Misc) -> None:
    """Copy entire content of widget to clipboard."""
    try:
        if isinstance(widget, tk.Text):
            full_text = widget.get("1.0", "end-1c")
        elif isinstance(widget, tk.Entry):
            full_text = widget.get()
        else:
            full_text = ""
        if full_text:
            widget.clipboard_clear()
            widget.clipboard_append(full_text)
    except Exception:
        pass


def _cut_selected(widget: tk.Misc) -> None:
    """Cut selected text from widget."""
    sel = _get_selected_text(widget)
    if not sel:
        return
    _copy_selected(widget, sel)
    try:
        if isinstance(widget, tk.Text):
            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        elif isinstance(widget, tk.Entry):
            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
    except Exception:
        pass


def _delete_selected(widget: tk.Misc) -> None:
    """Delete selected text without copying."""
    try:
        if isinstance(widget, tk.Text):
            if widget.tag_ranges(tk.SEL):
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        elif isinstance(widget, tk.Entry):
            if widget.selection_present():
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
    except Exception:
        pass


def _clear_all(widget: tk.Misc) -> None:
    """Clear all text in editable widget."""
    try:
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
        elif isinstance(widget, tk.Entry):
            widget.delete(0, tk.END)
    except Exception:
        pass


def _paste_to_widget(widget: tk.Misc, on_paste: Optional[Callable[[Any], Any]] = None) -> None:
    """Perform paste operation."""
    if on_paste is not None:
        try:
            # Create a mock event or call callback
            res = on_paste(None)
            if res == "break":
                return
        except Exception:
            pass

    clip = read_clipboard_text(widget) or ""
    if not clip:
        try:
            clip = widget.clipboard_get()
        except Exception:
            clip = ""

    if not clip:
        return

    try:
        if isinstance(widget, tk.Text):
            if widget.tag_ranges(tk.SEL):
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            widget.insert(tk.INSERT, clip)
            widget.see(tk.INSERT)
        elif isinstance(widget, tk.Entry):
            if widget.selection_present():
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            widget.insert(tk.INSERT, clip)
    except Exception:
        pass


def attach_text_context_menu(
    widget: tk.Misc,
    is_editable: bool = False,
    on_paste: Optional[Callable[[Any], Any]] = None,
    on_copy: Optional[Callable[[str], Any]] = None,
) -> None:
    """
    Attach right-click popup context menu to a Text or Entry widget.
    If text is highlighted (คลุมดำ), right-clicking immediately copies the text
    and displays context menu with copy/paste/select-all actions.
    """

    def _show_menu(event: tk.Event) -> str:  # type: ignore[type-arg]
        selected_text = _get_selected_text(widget)

        # Requirement: Highlight text + right click auto-copies
        if selected_text:
            _copy_selected(widget, selected_text)
            if on_copy:
                try:
                    on_copy(selected_text)
                except Exception:
                    pass
        else:
            # If no selection and editable, move insertion cursor to right-click coordinates
            try:
                if is_editable:
                    if isinstance(widget, tk.Text):
                        widget.mark_set(tk.INSERT, f"@{event.x},{event.y}")
                        widget.focus_set()
                    elif isinstance(widget, tk.Entry):
                        widget.icursor(f"@{event.x}")
                        widget.focus_set()
            except Exception:
                pass

        menu = tk.Menu(
            widget,
            tearoff=0,
            bg=T.get("bg2", "#282a2c"),
            fg=T.get("fg", "#ffffff"),
            activebackground=T.get("accent", "#8ab4f8"),
            activeforeground=T.get("bg", "#1e1f20"),
            relief="flat",
            bd=1,
            font=FONT_TINY,
        )

        has_sel = bool(selected_text)

        # Clipboard content check
        has_clip = False
        try:
            has_clip = bool(read_clipboard_text(widget))
            if not has_clip:
                has_clip = bool(widget.clipboard_get())
        except Exception:
            has_clip = False

        if has_sel:
            menu.add_command(
                label="✔ คัดลอกแล้ว (Copied)",
                command=lambda: _copy_selected(widget, selected_text),
            )
            if is_editable:
                menu.add_command(
                    label="✂ ตัด (Cut)",
                    command=lambda: _cut_selected(widget),
                )
        else:
            menu.add_command(
                label="📋 คัดลอก (Copy)",
                state="disabled",
            )

        if is_editable:
            menu.add_command(
                label="📥 วาง (Paste)",
                state="normal" if has_clip or on_paste is not None else "disabled",
                command=lambda: _paste_to_widget(widget, on_paste),
            )

        menu.add_separator()

        menu.add_command(
            label="✨ เลือกทั้งหมด (Select All)",
            command=lambda: _select_all(widget),
        )

        menu.add_command(
            label="📄 คัดลอกทั้งหมด (Copy All)",
            command=lambda: _copy_all(widget),
        )

        if is_editable:
            menu.add_separator()
            if has_sel:
                menu.add_command(
                    label="✕ ลบข้อความที่เลือก (Delete)",
                    command=lambda: _delete_selected(widget),
                )
            menu.add_command(
                label="🗑 ล้างทั้งหมด (Clear)",
                command=lambda: _clear_all(widget),
            )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

        return "break"

    # Bind right-click on all platforms
    widget.bind("<Button-3>", _show_menu, add="+")
    # macOS bindings
    widget.bind("<Button-2>", _show_menu, add="+")
    widget.bind("<Control-Button-1>", _show_menu, add="+")
