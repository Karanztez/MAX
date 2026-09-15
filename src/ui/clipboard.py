"""
clipboard.py — Windows clipboard operations and image conversions for MaxPlus AI.
"""

import base64
import io
import os
import time
import tkinter as tk
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


def img_to_b64(img: "Image.Image") -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def img_to_dib(img: "Image.Image") -> bytes:
    """Return Windows CF_DIB bytes (a BMP without its 14-byte file header)."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="BMP")
    return buf.getvalue()[14:]


def copy_image_to_clipboard(img: "Image.Image") -> None:
    """Place a PIL image on the Windows clipboard as CF_DIB."""
    if os.name != "nt":
        raise RuntimeError("การคัดลอกรูปภาพรองรับ Windows เท่านั้น")

    import ctypes

    data = img_to_dib(img)
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    kernel32.GlobalAlloc.argtypes = (ctypes.c_uint, ctypes.c_size_t)
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = (ctypes.c_void_p,)
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = (ctypes.c_void_p,)
    kernel32.GlobalFree.argtypes = (ctypes.c_void_p,)
    user32.OpenClipboard.argtypes = (ctypes.c_void_p,)
    user32.SetClipboardData.argtypes = (ctypes.c_uint, ctypes.c_void_p)
    user32.SetClipboardData.restype = ctypes.c_void_p

    handle = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
    if not handle:
        raise ctypes.WinError()
    clipboard_open = False
    transferred = False
    try:
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise ctypes.WinError()
        ctypes.memmove(pointer, data, len(data))
        kernel32.GlobalUnlock(handle)

        # Clipboard may briefly be held by another app; retry for 300 ms.
        for _ in range(10):
            if user32.OpenClipboard(None):
                clipboard_open = True
                break
            time.sleep(0.03)
        if not clipboard_open:
            raise RuntimeError("Windows Clipboard กำลังถูกใช้งานโดยโปรแกรมอื่น")
        if not user32.EmptyClipboard():
            raise ctypes.WinError()
        if not user32.SetClipboardData(8, handle):  # CF_DIB
            raise ctypes.WinError()
        transferred = True  # Windows owns the memory from this point.
    finally:
        if clipboard_open:
            user32.CloseClipboard()
        if not transferred:
            kernel32.GlobalFree(handle)


def read_clipboard_text(widget: tk.Misc) -> Optional[str]:
    """Read external clipboard text, preferring native Windows Unicode data."""
    if os.name == "nt":
        import ctypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.OpenClipboard.argtypes = (ctypes.c_void_p,)
        user32.OpenClipboard.restype = ctypes.c_int
        user32.GetClipboardData.argtypes = (ctypes.c_uint,)
        user32.GetClipboardData.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = (ctypes.c_void_p,)
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = (ctypes.c_void_p,)
        opened = False
        try:
            for _ in range(12):
                if user32.OpenClipboard(None):
                    opened = True
                    break
                time.sleep(0.025)
            if opened:
                handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
                if handle:
                    pointer = kernel32.GlobalLock(handle)
                    if pointer:
                        try:
                            return ctypes.wstring_at(pointer).replace("\r\n", "\n").replace("\r", "\n")
                        finally:
                            kernel32.GlobalUnlock(handle)
        except Exception:
            pass
        finally:
            if opened:
                user32.CloseClipboard()
    try:
        value = widget.clipboard_get()
        return value.replace("\r\n", "\n").replace("\r", "\n") if isinstance(value, str) else None
    except tk.TclError:
        return None


def project_name() -> str:
    """ดึงชื่อโปรเจกต์จาก CWD"""
    return os.path.basename(os.path.abspath(os.getcwd()))
