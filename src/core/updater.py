"""
src/core/updater.py — GitHub Version Checker and In-Place EXE Updater for MAX.
"""

from dataclasses import dataclass
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from typing import Callable, Optional, Tuple

APP_VERSION = "1.0.6"
GITHUB_REPO = "Karanztez/MAX"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    version: str
    tag_name: str
    title: str
    body: str
    html_url: str
    download_url: Optional[str]
    asset_name: Optional[str]
    asset_size: int = 0


def parse_version_tuple(version_str: str) -> Tuple[int, ...]:
    """Parse version strings like 'v1.0.0', '1.2.3-beta', 'v2.1' into comparable int tuples."""
    cleaned = version_str.strip().lstrip("vV")
    # match leading numeric dotted sequence e.g. 1.0.4
    match = re.match(r"^(\d+(?:\.\d+)*)", cleaned)
    if not match:
        return (0,)
    parts = match.group(1).split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return (0,)


def is_newer_version(latest_str: str, current_str: str = APP_VERSION) -> bool:
    """Returns True if latest_str is strictly newer than current_str."""
    return parse_version_tuple(latest_str) > parse_version_tuple(current_str)


def check_github_release(repo: str = GITHUB_REPO, timeout: int = 10) -> Optional[UpdateInfo]:
    """Fetch latest release info from GitHub API."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"MAX-App/{APP_VERSION}",
            "Accept": "application/vnd.github.v3+json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    tag_name = data.get("tag_name", "")
    version = tag_name.lstrip("vV")
    title = data.get("name", tag_name)
    body = data.get("body", "")
    html_url = data.get("html_url", f"https://github.com/{repo}/releases")

    # Find .exe asset if present
    download_url = None
    asset_name = None
    asset_size = 0
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.lower().endswith(".exe"):
            download_url = asset.get("browser_download_url")
            asset_name = name
            asset_size = asset.get("size", 0)
            break

    return UpdateInfo(
        version=version,
        tag_name=tag_name,
        title=title,
        body=body,
        html_url=html_url,
        download_url=download_url,
        asset_name=asset_name,
        asset_size=asset_size,
    )


def download_file(
    url: str,
    dest_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    chunk_size: int = 65536,
    timeout: int = 30,
) -> None:
    """Download a file with progress reporting (bytes_downloaded, total_bytes)."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"MAX-App/{APP_VERSION}"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback is not None:
                    progress_callback(downloaded, total_size)


def is_frozen_exe() -> bool:
    """Return True if running as a compiled PyInstaller standalone executable."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def apply_exe_update_and_restart(new_exe_path: str) -> None:
    """
    Spawns a detached Windows batch script to replace current running .exe
    with the new downloaded .exe after current process terminates, then restarts it.
    """
    if not is_frozen_exe():
        raise RuntimeError("Cannot auto-replace source files in non-frozen Python mode.")

    target_exe = os.path.abspath(sys.executable)
    new_exe = os.path.abspath(new_exe_path)
    pid = os.getpid()

    # Create a temporary batch script
    bat_fd, bat_path = tempfile.mkstemp(suffix="_max_update.bat")
    os.close(bat_fd)

    bat_content = f"""@echo off
setlocal
set PID={pid}
set TARGET="{target_exe}"
set NEW="{new_exe}"
set BAT="%~f0"

:wait_proc
timeout /t 1 /nobreak >nul
tasklist /fi "PID eq %PID%" 2>nul | find "%PID%" >nul
if not errorlevel 1 goto wait_proc

:copy_file
copy /y %NEW% %TARGET% >nul
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto copy_file
)

del /f /q %NEW% >nul 2>&1
start "" %TARGET%
del /f /q %BAT% >nul 2>&1
exit
"""
    with open(bat_path, "w", encoding="ascii", errors="ignore") as f:
        f.write(bat_content)

    # Launch detached batch process
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=CREATE_NO_WINDOW,
        close_fds=True
    )
    # Terminate current app immediately so file lock is released
    sys.exit(0)
