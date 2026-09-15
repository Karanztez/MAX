"""
src/ui package — MaxPlus AI graphical interface modules.
"""

from src.ui.themes import (
    DARK,
    LIGHT,
    GREY,
    WHITE,
    T,
    FONT,
    FONT_BOLD,
    FONT_MONO,
    FONT_TINY,
    FONT_HDR,
    FONT_TITLE,
)
from src.ui.clipboard import (
    copy_image_to_clipboard,
    img_to_b64,
    img_to_dib,
    read_clipboard_text,
)
from src.ui.widgets.scrollable_frame import ScrollableFrame
from src.ui.widgets.message_bubble import MessageBubble
from src.ui.capture.screen_crop import ScreenCropOverlay
from src.ui.dialogs.crop_dialog import CropDialog
from src.ui.dialogs.settings_dialog import SettingsDialog
from src.ui.dialogs.skill_picker_dialog import SkillPickerDialog
from src.ui.dialogs.mcp_dialog import MCPManagerDialog
from src.ui.chat_tab import ChatTab
from src.ui.main_window import MaxPlusGUI, _TRAY_OK, _PIL_OK, main
from src.core.provider_profiles import default_profiles

_img_to_dib = img_to_dib
_img_to_b64 = img_to_b64

__all__ = [
    "DARK",
    "LIGHT",
    "T",
    "FONT",
    "FONT_BOLD",
    "FONT_MONO",
    "FONT_TINY",
    "FONT_HDR",
    "FONT_TITLE",
    "copy_image_to_clipboard",
    "img_to_b64",
    "img_to_dib",
    "read_clipboard_text",
    "ScrollableFrame",
    "MessageBubble",
    "ScreenCropOverlay",
    "CropDialog",
    "SettingsDialog",
    "SkillPickerDialog",
    "MCPManagerDialog",
    "ChatTab",
    "MaxPlusGUI",
    "_TRAY_OK",
    "_PIL_OK",
    "_img_to_dib",
    "_img_to_b64",
    "default_profiles",
    "main",
]
