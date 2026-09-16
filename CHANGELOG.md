<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to **MAX (MaxPlus AI)** will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [v1.0.2] - 2026-09-16

### Added

- **Multi-Agent Team Room (`AgentTeamTab`, `/team`)**:
  - Dedicated collaborative multi-agent workspace with default roles: 📋 **Planner / Architect**, 💻 **Coder / Developer**, and 🔍 **Reviewer / QA Auditor**.
  - Pipeline orchestration passing specifications and code sequentially between team agents with live streaming output.
  - **Team Configuration Dialog (`TeamConfigDialog`)** allowing custom toggles, provider profiles, models, temperatures, and system prompts per agent.
  - In-chat stop button (`⏹ หยุด`) to cancel execution mid-turn gracefully.
- **Per-Tab Provider, Model & API Base Independence**:
  - Each chat tab (`ChatTab`) now stores its own `profile_id` and `model` independently.
  - Top toolbar provider dropdown automatically syncs to the active tab upon tab switching without interfering with other tabs.
- **MAX Virtual Screens Architecture (`ScreenManager`, Sequential IDs `1`, `2`, `3`, `4`...)**:
  - Virtual screen manager ([`src/core/screen_manager.py`](file:///c:/Users/ACER/IdeaProjects/MAX/src/core/screen_manager.py)) assigning sequential numeric IDs for intuitive terminal navigation.
  - Isolated screen state holding role, custom model, profile ID, system prompt, and message history per screen.
- **CLI Virtual Screen Navigation (`/screen`, `/screens`)**:
  - `/screens` or `/screen list`: Beautiful ASCII table of all screens, roles, models, pipeline links, and message counts.
  - `/screen 1`, `/screen 2`, `/screen 3`: Instant screen switching with dynamic prompt indicator (e.g. `[1:Planner] You:`) and recent message summary.
  - `/screen create <name> [role] [model]`: Create new screens with auto-assigned IDs.
  - `/screen link <from_id> <to_id>`: Link screens together into an automated data pipeline.
  - `/screen unlink <id>` / `/screen close <id>`: Unlink or close screens.
- **CLI Team Pipeline Commands (`/team init`, `/team run <prompt>`, `/team status`)**:
  - `/team init`: Auto-scaffold Screen 1 (Planner) ➔ Screen 2 (Coder) ➔ Screen 3 (Reviewer) with configured links.
  - `/team run <prompt>`: Execute linked multi-agent team pipeline in the terminal with live streaming output and screen history persistence.
  - `/team status`: Inspect current team screens and pipeline links.
- **Autonomous AI MCP Tools for Screens & Workspaces**:
  - `create_chat_tab` and `create_team_room`: AI tools proposing new tabs or team rooms with explicit user approval dialog.
  - `screen_list`, `screen_create`, `screen_switch`, `screen_link`: MCP tools allowing AI agents to query, create, switch, and link virtual screens autonomously.
- **Comprehensive Verification & Type Safety**:
  - Added unit test suites [`tests/test_team_room.py`](file:///c:/Users/ACER/IdeaProjects/MAX/tests/test_team_room.py), [`tests/test_workspace_tools.py`](file:///c:/Users/ACER/IdeaProjects/MAX/tests/test_workspace_tools.py), and [`tests/test_screen_manager.py`](file:///c:/Users/ACER/IdeaProjects/MAX/tests/test_screen_manager.py).
  - 104 out of 104 unit tests passing with zero Pyrefly diagnostic warnings.

- **Software License & Terms of Use (`LICENSE`)**: Added Non-Commercial Proprietary License with permission-only commercial use (ไม่อนุญาตให้นำไปจำหน่ายหรือใช้ในเชิงพาณิชย์โดยไม่ได้รับอนุญาตเป็นลายลักษณ์อักษรจากเจ้าของลิขสิทธิ์ Karanztez).
- **Gemini / Antigravity Style Code Diff & Editing Engine (`replace_file_content`, `diff_engine`)**: Added precision surgical code replacement tools and colorized terminal/GUI unified diff renderer showing line-by-line green `+` additions and red `-` deletions with line numbers and diff blocks.
- **Modular MCP Package Architecture (`src/core/mcp/`)**: Decomposed the monolithic 2,100+ line `mcp_manager.py` into dedicated, maintainable sub-modules (`builtins/file_tools.py`, `web_tools.py`, `git_tools.py`, `media_tools.py`, `system_tools.py`, `skill_tools.py`, `connection.py`, `diff_engine.py`, `manager.py`) while preserving 100% backward-compatible facade re-exports and resolving Pyrefly import diagnostics.
- **Autonomous Skill Management (`install_skill`, `remove_skill`, `list_skills`, `/skills`, `/skill`)**: MCP Tools #32, #33, #34 and CLI commands enabling AI and users to install skills directly from GitHub (`owner/repo`, tree/blob URLs, raw SKILL.md links) or markdown text, delete skills safely, and list all installed skills with instant hot-reloading without restarting.
- **Web Access Security Guard & Domain Verification (`/security`, `/domains`)**: Interactive domain permission guard prompting users before AI accesses external websites (`fetch_web_content`, `http_request`), with choices to Allow once, Deny, Always allow domain, or Allow all.
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
