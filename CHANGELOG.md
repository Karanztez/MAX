<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to **MAX (MaxPlus AI)** will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

- **GitHub Specialist Skill & Tools (`github_search_repos`, `github_get_repo`, `github_read_file`, `github_list_issues`, `github_clone_repo`)**: Added tools #27 to #31 and [`skills/github-specialist`](file:///skills/github-specialist/SKILL.md) for full Git Flow, GitHub REST API, repository inspection, remote file reading, and CI/CD workflow automation.
- **AI Image Generation Tool (`generate_image`, `/image`, `/img`)**: Tool #25 enabling high-resolution image creation (Flux, Turbo, DALL-E) directly saved to disk with zero-config fallback.
- **AI Video Generation Tool (`generate_video`, `/video`, `/vid`)**: Tool #26 enabling AI-driven short video and animation synthesis (Wan2.1 / MP4) with instant preview.
- **Multimedia Generator Skill**: Added [`skills/multimedia-generator`](file:///skills/multimedia-generator/SKILL.md) for automated graphic assets, concept art, UI mockups, and video creation.
- **Project Export & Download Tool (`/export`, `/download`)**: Added tool #24 and slash commands to easily export project files as ZIP to Android Termux Download storage (`/sdcard/Download`) and desktop download directories.
- **Java & Kotlin Project Support**: Added specialized [`skills/java-developer`](file:///skills/java-developer/SKILL.md) and [`skills/kotlin-developer`](file:///skills/kotlin-developer/SKILL.md) skills covering Gradle, Maven, Spring Boot, Android, Coroutines, Compose, and Termux OpenJDK execution.
- **CLI Self-Updater (`/update`)**: Added command in Terminal/Mobile CLI to check GitHub releases, preview Changelogs, and auto-download/update both frozen EXE and source/git environments.
- **Interactive Numbered Setup (1-2-3-4)**: First-run setup and `/setup` wizard in CLI allowing users to choose AI Provider by number [1..N], select model by number [1..N], and configure custom endpoints.
- **In-Chat API Key & Base URL Guard**: Prompt directly inside the CLI chat session whenever API keys or Base URLs are missing, with instant secure DPAPI/POSIX persistence.
- **Automated GitHub Actions Release workflow** with semantic version auto-increment (`bump_version.py`).
- **Release Manager Skill** in `skills/release-manager/SKILL.md`.

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
