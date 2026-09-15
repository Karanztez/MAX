"""
main.py — MaxPlus AI Application Entry Point
"""

import os
import sys
import traceback
from pathlib import Path

# Ensure root directory is always in sys.path
_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

def is_headless() -> bool:
    """Check if environment lacks GUI display (Linux headless, Docker, Termux)."""
    if os.name == "posix":
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            return True
    return False


if __name__ == "__main__":
    cli_flags = {"--cli", "-c", "-p", "--prompt", "--help", "-h"}
    args = sys.argv[1:]

    # If CLI flags passed or running in headless environment
    if any(flag in args for flag in cli_flags) or is_headless():
        from src.cli import run_cli
        run_cli(args)
    else:
        try:
            from src.ui.main_window import main
            main()
        except Exception as e:
            # Fallback to CLI if GUI initialization fails (e.g. Tkinter / Display errors)
            if "display" in str(e).lower() or "tkinter" in str(e).lower() or "_tkinter" in str(e).lower():
                print(f"[info] No GUI display detected. Starting MAX in Terminal CLI mode...")
                from src.cli import run_cli
                run_cli(args)
            else:
                traceback.print_exc()
                sys.exit(1)

