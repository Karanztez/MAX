"""
tests/test_media_viewer.py — Unit tests for MediaViewerTab, media path extraction, and in-chat media previews.
"""

import os
import sys
import unittest
import tkinter as tk
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ui.widgets.message_bubble import extract_media_items, MessageBubble
from src.ui.tabs.media_tab import MediaViewerTab
from src.ui.main_window import MaxPlusGUI
from src.ui.themes import T

try:
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


class TestMediaViewer(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.temp_dir = TemporaryDirectory()

    def tearDown(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_extract_media_items_from_text(self) -> None:
        # Create dummy image and video files
        img_path = os.path.join(self.temp_dir.name, "generated_art.png")
        if _PIL_OK:
            Image.new("RGB", (100, 100), color="blue").save(img_path)
        else:
            with open(img_path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        vid_path = os.path.join(self.temp_dir.name, "demo_clip.mp4")
        with open(vid_path, "wb") as f:
            f.write(b"\x00\x00\x00 ftypisom" + b"\x00" * 100)

        sample_text = (
            f"🎨 สร้างรูปภาพสำเร็จเรียบร้อยแล้ว!\n"
            f"• บันทึกไว้ที่: {img_path}\n"
            f"🎬 สร้างวิดีโอสำเร็จเรียบร้อยแล้ว!\n"
            f"• บันทึกไว้ที่: {vid_path} (2.50 MB)\n"
        )

        items = extract_media_items(sample_text)
        self.assertEqual(len(items), 2)
        types = {item["type"] for item in items}
        self.assertIn("image", types)
        self.assertIn("video", types)

    def test_media_viewer_tab_image(self) -> None:
        img_path = os.path.join(self.temp_dir.name, "sample.png")
        if _PIL_OK:
            Image.new("RGBA", (120, 80), color="red").save(img_path)
        else:
            with open(img_path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        closed = False
        def on_close(tab: MediaViewerTab) -> None:
            nonlocal closed
            closed = True

        tab = MediaViewerTab(
            self.root,
            file_path=img_path,
            title="🎨 Sample",
            media_type="image",
            prompt="draw a sample red rectangle",
            on_close=on_close,
        )
        self.assertEqual(tab.media_type, "image")
        self.assertIn("Sample", tab.title_text)
        self.assertTrue(hasattr(tab, "_canvas"))

        # Test rotation and fit
        tab._rotate_image()
        self.assertEqual(tab._rotation_angle, 270)
        tab._toggle_fit()
        self.assertFalse(tab._fit_to_window)

        tab._handle_close()
        self.assertTrue(closed)

    def test_media_viewer_tab_video(self) -> None:
        vid_path = os.path.join(self.temp_dir.name, "sample.mp4")
        with open(vid_path, "wb") as f:
            f.write(b"\x00\x00\x00 ftypisom" + b"\x00" * 100)

        tab = MediaViewerTab(
            self.root,
            file_path=vid_path,
            title="🎬 Sample Video",
            media_type="video",
            prompt="create an animation of stars",
        )
        self.assertEqual(tab.media_type, "video")
        self.assertIn("🎬", tab.title_text)

    def test_message_bubble_renders_media_card(self) -> None:
        img_path = os.path.join(self.temp_dir.name, "bubble_img.png")
        if _PIL_OK:
            Image.new("RGB", (64, 64), color="green").save(img_path)
        else:
            with open(img_path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        opened_path = ""
        def on_open(path: str, mtype: str, prompt: str) -> None:
            nonlocal opened_path
            opened_path = path

        msg = f"สร้างภาพเสร็จแล้ว บันทึกไว้ที่: {img_path}"
        bubble = MessageBubble(
            self.root, "AI", msg, T["bg_ai"], T["ai_hdr"],
            on_open_media=on_open,
        )
        self.assertGreaterEqual(len(bubble._media_cards), 1)

        bubble._trigger_open_media(img_path, "image")
        self.assertEqual(os.path.abspath(opened_path), os.path.abspath(img_path))

    def test_main_window_open_media_tab(self) -> None:
        gui = MaxPlusGUI()
        gui.withdraw()
        try:
            img_path = os.path.join(self.temp_dir.name, "window_test.png")
            if _PIL_OK:
                Image.new("RGB", (32, 32), color="purple").save(img_path)
            else:
                with open(img_path, "wb") as f:
                    f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

            initial_tab_count = len(gui._tabs)
            media_tab = gui.open_media_tab(img_path, media_type="image", prompt="test purple square")
            self.assertIsNotNone(media_tab)
            self.assertEqual(len(gui._tabs), initial_tab_count + 1)
            self.assertIsInstance(media_tab, MediaViewerTab)

            # Re-opening same path selects existing tab without duplicating
            same_tab = gui.open_media_tab(img_path, media_type="image")
            self.assertIs(same_tab, media_tab)
            self.assertEqual(len(gui._tabs), initial_tab_count + 1)

            # Close tab
            gui._close_tab()
            self.assertEqual(len(gui._tabs), initial_tab_count)
        finally:
            gui.destroy()


if __name__ == "__main__":
    unittest.main()
