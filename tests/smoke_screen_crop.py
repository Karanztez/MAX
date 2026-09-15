"""Local smoke test for the Python screen-crop overlay (no GitHub build needed)."""

from types import SimpleNamespace
import subprocess
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import src.ui as gui
from src.core.settings_store import SettingsStore


def main() -> None:
    gui._TRAY_OK = False
    app = gui.MaxPlusGUI()
    app.withdraw()
    tab = app._current_tab()
    assert tab is not None and len(tab.skill_manager.skills) >= 2
    app.clipboard_clear()
    app.clipboard_append("ข้อความจากโปรแกรมภายนอก\nบรรทัดที่สอง")
    app.update()
    tab.entry.insert("1.0", "ข้อความเดิม")
    tab.entry.tag_add("sel", "1.0", "end-1c")
    assert tab._on_paste(SimpleNamespace(widget=tab.entry)) == "break"
    pasted_text = tab.entry.get("1.0", "end-1c")
    assert pasted_text == "ข้อความจากโปรแกรมภายนอก\nบรรทัดที่สอง", repr(pasted_text)
    tab.entry.delete("1.0", "end")
    with TemporaryDirectory() as saved_settings_folder:
        saved_path = Path(saved_settings_folder) / "settings.json"
        app.settings_store = SettingsStore(saved_path)
        settings = gui.SettingsDialog(app, app.profiles, app.selected_profile_id, False,
                                      app._save_api_settings)
        settings.withdraw()
        settings.update_idletasks()
        assert settings._save_btn.winfo_manager() == "pack"
        assert settings._save_btn.winfo_reqwidth() >= 100
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "Set-Clipboard -Value '  api-key-pasted-from-external-app  '"],
            check=True,
        )
        app.update()
        settings._key_entry.delete(0, "end")
        assert settings._key_control_shortcut(SimpleNamespace(keycode=86, keysym="Thai_V")) == "break"
        assert settings._key_var.get() == "api-key-pasted-from-external-app"
        settings._save()
        assert saved_path.exists(), "บันทึก API must create encrypted settings file"
        loaded, selected = app.settings_store.load_provider_settings(gui.default_profiles())
        active = next(profile for profile in loaded if profile["id"] == selected)
        assert active["api_key"] == "api-key-pasted-from-external-app"
        if settings.winfo_exists():
            settings.destroy()
    with TemporaryDirectory() as settings_folder:
        app.settings_store = SettingsStore(Path(settings_folder) / "settings.json")
        profiles = gui.default_profiles()
        profiles[1]["api_key"] = "claude-session-key"
        app._save_api_settings(profiles, "maxplus-claude", remember=False)
        assert app.api_key == "claude-session-key"
        assert tab.ai.api_key == "claude-session-key"
        assert tab.ai.base_url.endswith("/claude-cursor-full/v1")
        assert tab.ai.model == "claude-sonnet-4-6"
        app.provider_var.set("OpenAI GPT / Codex")
        app.update()
        assert tab.ai.api_mode == "responses"
        assert tab.ai.base_url == "https://api.openai.com/v1"
    tab._set_enabled_skills({"image-analyst"})
    assert "Active skill: Image Analyst" in tab._effective_system_prompt()
    result = []
    overlay = gui.ScreenCropOverlay(
        app,
        Image.new("RGB", (800, 600), "#d33a42"),
        result.append,
        lambda: None,
    )
    for _ in range(20):
        app.update()
        if hasattr(overlay, "_scale_x"):
            break
        time.sleep(0.01)
    assert hasattr(overlay, "_scale_x"), "overlay must wait for real Canvas geometry"
    overlay.attributes("-alpha", 0.0)
    overlay._press(SimpleNamespace(x=100, y=80))
    overlay._drag(SimpleNamespace(x=500, y=360))
    overlay._release(SimpleNamespace(x=500, y=360))
    app.update()

    assert len(result) == 0, "selection release must enter annotation mode"
    overlay._press(SimpleNamespace(x=150, y=120))
    overlay._drag(SimpleNamespace(x=280, y=210))
    overlay._release(SimpleNamespace(x=280, y=210))
    overlay._annotations.append({"kind": "text", "x": 180, "y": 150,
                                 "text": "Test", "color": "#ffffff", "size": 18})
    overlay._apply()

    assert len(result) == 1, "confirm must produce one annotated crop"
    assert result[0].width > 0 and result[0].height > 0
    assert result[0].getpixel((0, 0)) == (211, 58, 66)
    colors = {color for _count, color in (result[0].getcolors(maxcolors=1_000_000) or [])}
    assert (255, 59, 92) in colors, "pen annotation must be rendered into the image"
    dib = gui._img_to_dib(result[0])
    assert dib[:4] == (40).to_bytes(4, "little"), "clipboard image must be BITMAPINFOHEADER DIB"
    assert int.from_bytes(dib[4:8], "little", signed=True) == result[0].width
    assert int.from_bytes(dib[8:12], "little", signed=True) == result[0].height
    app._quit_app()
    print(f"screen crop + annotations + clipboard DIB smoke test passed: {result[0].size}")


if __name__ == "__main__":
    main()
