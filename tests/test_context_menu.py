"""
tests/test_context_menu.py — Unit tests for universal right-click context menu and text selection copy/paste.
"""

import os
import sys
import unittest
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from ui.widgets.context_menu import (
        attach_text_context_menu,
        _get_selected_text,
        _select_all,
        _copy_selected,
        _copy_all,
        _cut_selected,
        _clear_all,
        _paste_to_widget,
    )
except (ImportError, ModuleNotFoundError):
    from src.ui.widgets.context_menu import (  # type: ignore[no-redef]
        attach_text_context_menu,
        _get_selected_text,
        _select_all,
        _copy_selected,
        _copy_all,
        _cut_selected,
        _clear_all,
        _paste_to_widget,
    )


class TestContextMenu(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except Exception as e:
            self.skipTest(f"Tkinter display not available: {e}")

    def tearDown(self):
        if hasattr(self, "root") and self.root:
            try:
                self.root.destroy()
            except Exception:
                pass

    def test_text_selection_and_copy(self):
        txt = tk.Text(self.root)
        txt.insert("1.0", "Hello MaxPlus AI World")
        # Select "MaxPlus"
        txt.tag_add(tk.SEL, "1.6", "1.13")

        selected = _get_selected_text(txt)
        self.assertEqual(selected, "MaxPlus")

        _copy_selected(txt, selected)
        clip = txt.clipboard_get()
        self.assertEqual(clip, "MaxPlus")

    def test_select_all_text(self):
        txt = tk.Text(self.root)
        txt.insert("1.0", "Line 1\nLine 2")
        _select_all(txt)
        selected = _get_selected_text(txt)
        self.assertEqual(selected, "Line 1\nLine 2")

    def test_copy_all_text(self):
        txt = tk.Text(self.root)
        txt.insert("1.0", "Complete content to copy")
        _copy_all(txt)
        clip = txt.clipboard_get()
        self.assertEqual(clip, "Complete content to copy")

    def test_cut_and_delete_text(self):
        txt = tk.Text(self.root)
        txt.insert("1.0", "Quick brown fox")
        txt.tag_add(tk.SEL, "1.6", "1.11")  # "brown"
        _cut_selected(txt)
        self.assertEqual(txt.clipboard_get(), "brown")
        self.assertEqual(txt.get("1.0", "end-1c"), "Quick  fox")

    def test_clear_all_text(self):
        txt = tk.Text(self.root)
        txt.insert("1.0", "Text that should be cleared")
        _clear_all(txt)
        self.assertEqual(txt.get("1.0", "end-1c"), "")

    def test_entry_selection_and_paste(self):
        entry = tk.Entry(self.root)
        entry.insert(0, "Sample Entry Data")
        entry.select_range(0, 6)  # "Sample"
        self.assertEqual(_get_selected_text(entry), "Sample")

        # Paste via _paste_to_widget
        entry.clipboard_clear()
        entry.clipboard_append("NewData")
        _paste_to_widget(entry)
        self.assertIn("NewData", entry.get())

    def test_attach_text_context_menu_bindings(self):
        from unittest.mock import patch

        txt = tk.Text(self.root)
        copied = []
        attach_text_context_menu(
            txt,
            is_editable=True,
            on_copy=lambda s: copied.append(s),
        )
        txt.insert("1.0", "Testing Right Click Auto Copy")
        txt.tag_add(tk.SEL, "1.8", "1.19")  # "Right Click"

        with patch.object(tk.Menu, "tk_popup", return_value=None):
            txt.event_generate("<Button-3>", x=10, y=10)

        # Verify clipboard was updated with selected text
        clip = txt.clipboard_get()
        self.assertEqual(clip, "Right Click")
        self.assertIn("Right Click", copied)


if __name__ == "__main__":
    unittest.main()
