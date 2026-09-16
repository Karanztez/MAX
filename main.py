from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# Ensure root directory and src directory are always in sys.path
_ROOT = str(Path(__file__).resolve().parent)
_SRC = str(Path(__file__).resolve().parent / "src")
for _p in (_ROOT, _SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def is_headless() -> bool:
    """Check if environment lacks GUI display (Linux headless, Docker, Termux, Android)."""
    if os.name == "posix":
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            return True
    return False


def _get_run_cli():
    try:
        from cli import run_cli
        return run_cli
    except (ImportError, ModuleNotFoundError):
        from src.cli import run_cli  # type: ignore[no-redef]
        return run_cli


def _get_run_gui():
    try:
        from ui.main_window import main as run_gui
        return run_gui
    except (ImportError, ModuleNotFoundError):
        from src.ui.main_window import main as run_gui  # type: ignore[no-redef]
        return run_gui


if __name__ == "__main__":
    cli_flags = {"--cli", "-c", "-p", "--prompt", "--help", "-h"}
    args = sys.argv[1:]

    # If CLI flags passed or running in headless environment (Termux, SSH, Docker, Server)
    if any(flag in args for flag in cli_flags) or is_headless():
        run_cli = _get_run_cli()
        run_cli(args)
    else:
        try:
            run_gui = _get_run_gui()
            run_gui()
        except Exception as e:
            # Fallback to CLI if GUI initialization fails (e.g. Tkinter / Display / X11 connection refused)
            err_msg = str(e).lower()
            if any(k in err_msg for k in ("display", "tkinter", "_tkinter", "xlib", "connection refused", "cannot connect")):
                print(f"[info] No GUI display detected ({e}). Starting MAX in Terminal CLI mode...")
                run_cli = _get_run_cli()
                run_cli(args)
            else:
                traceback.print_exc()
                sys.exit(1)

