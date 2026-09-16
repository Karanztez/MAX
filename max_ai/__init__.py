"""
max_ai root package re-export.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

try:
    from src.max_ai import *  # type: ignore[import-not-found]
    from src.max_ai import __all__, __version__  # type: ignore[import-not-found]
except (ImportError, ModuleNotFoundError):
    from max_ai import *  # type: ignore[import-not-found, no-redef]
    from max_ai import __all__, __version__  # type: ignore[import-not-found, no-redef]
