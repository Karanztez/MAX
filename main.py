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

from src.ui.main_window import main

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
