# Changelog

All notable changes to **MAX (MaxPlus AI)** will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Automated GitHub Actions Release workflow with semantic version auto-increment (`bump_version.py`).
- Automatic markdown changelog extraction and fallback to Git commits.
- Added `release-manager` skill for managing release versions and publishing.

---

## [v1.0.1] - 2026-09-16

### Added
- **Cross-Platform Support**: Added automated 1-line installation scripts (`install.sh` and `install.ps1`) for Linux, macOS, Windows Terminal, and Android (Termux).
- **Package Management**: Added standard `setup.py` and `pyproject.toml` with `max` and `max-gui` CLI entry points.
- **Built-in Agent Toolset**: Expanded built-in MCP agent tools (23 tools) with background execution, file ops, search, and system monitoring.
- **CI/CD Reliability**: Enhanced PyInstaller spec with resilient dynamic dependency checks and unit test gate before release builds.

---

## [v1.0.0] - 2026-09-15

### Added
- **Modular Architecture**: Restructured codebase into `src/core` and `src/ui`.
- **In-Place GitHub Auto-Updater**: Background update check and self-replacing Windows EXE updater with download progress dialog.
- **Multi-Tab GUI & Screen Snipping**: Full Windows screen capture tool, clipboard image paste, global hotkeys, and system tray integration.
- **DPAPI Secure Storage**: Encrypted provider profile credentials using Windows Data Protection API.
