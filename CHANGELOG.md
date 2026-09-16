<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to **MAX for AI** are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.0.9] - 2026-09-16

### 🧠 Anthropic Messages API Native Support & China Town Autonomous Tool Execution

#### 🎭 Anthropic Messages API Native Support
- **Native Claude `/messages` Protocol:** Full integration of Anthropic's native Messages protocol for Claude endpoints (`claude-native`, `claude-cursor`, `claude-antigravity`).
- **Claude Fabled & Sonnet Tool Calling:** Enabled complete multi-turn tool calling and schema translation (`input_schema`, `tool_use`, `tool_result`) for `claude-fable-5`, `claude-fable-5-1`, `claude-sonnet-4-6`, `claude-opus-5`, etc.
- **Multimodal Block Mapping:** Seamless conversion of text, images, and tool results between standard OpenAI format and Anthropic content blocks.

#### 🇨🇳 China Town (จีน) Provider Optimization
- **Validated Autonomous Tool Execution:** Full verification and benchmark pass across all China Town models (`deepseek-v4.1-flash`, `qwen-3.8-max`, `deepseek-v4-flash`, `glm-5.3-flash`, `deepseek-v4-pro-0813`).
- **Sub-10s Multi-Tool Execution:** Optimized tool chaining pipeline achieving rapid response times and structured Thai response synthesis.

#### 🛡️ AI Client Error Handling & Accurate Reporting
- **Accurate Error Visibility:** Eliminated false-positive completion summaries when upstream providers return 400/500 errors or timeouts, ensuring true error messages are surfaced to the user.
- **Settings Dialog Expansion:** Added `Anthropic Messages` mode selection in Settings for custom API endpoints.

---

## [v1.0.8] - 2026-09-16

### 🔄 In-Place Force Reinstall, Transient 503 Retries & CI Idempotency

#### 🛡️ Resilient AI Client & Transient Error Retries
- **HTTP 500/502/503/504 Backoff Retries:** Added exponential backoff retries with jitter in `AIClient._call_response` for transient provider errors.
- **Graceful Tool Execution Fallback:** Ensures tool execution results are synthesized into a structured Thai report even if the subsequent model call experiences server issues.

#### 🔄 Self-Update & Force Reinstall (`updater.py`)
- **Force Re-download / Reinstall Latest Build:** Added prompt in GUI (Settings and Help update checks) and CLI (`max --update` / `/update`) allowing users to re-download and reinstall the latest build from GitHub Releases even if already running the latest version number.
- **Improved Dialog Messaging:** Update dialog clearly distinguishes between new version upgrades and reinstalling the current build.

#### 📁 Non-Git Repository Safety
- **Workspace Git Detection:** Added `_is_git_repo` helper in `system_tools.py` ensuring git commands fail gracefully with helpful guidance when executed in non-git directories.

#### 🚀 CI/CD Pipeline Hardening
- **Idempotent npm Package Publishing:** Updated `.github/workflows/release.yml` with pre-publish registry checks so re-running actions or updating tags does not fail on already-published versions.

---

## [v1.0.7] - 2026-09-16

### 🚀 IDE Debug Inspector, Background Test Runner & Staged Drafts Tab

#### 🔍 IDE Debug & Diagnostics Reviewer (`IDEInspector`)
- **Python AST Syntax Validation:** Instant detection of syntax errors and compile failures with precise file, line, column, rule code, and error messages.
- **Static Analysis & Linters:** Integration with Pyrefly, Flake8, Ruff, and compiler error extraction.
- **Code Draft Pre-Review:** Compares diagnostics before and after proposed edits to ensure patches fix existing issues without introducing new errors.

#### 🧪 Asynchronous Background Test Runner (`BackgroundTestRunner`)
- **Non-Blocking Execution:** Runs automated tests (`unittest`, `pytest`, custom validation scripts) in background daemon threads without freezing the desktop GUI or chat.
- **Live Terminal Logging:** Captures and streams stdout/stderr in real time, tracking execution duration, exit codes, and pass/fail metrics.
- **Graceful Cancellation & Timeout:** Cancels hanging tests safely with timeout safeguards.

#### 📝 Drafts & Review GUI Tab (`DraftReviewTab`)
- **Dedicated Toolbar Button:** Added `📝 Drafts` button on the primary desktop toolbar for instant access.
- **Staged Drafts & Color Diffs:** Side-by-side / unified diff viewer with syntax color tags (green additions, red deletions).
- **Safe Apply & Discard:** One-click `✅ นำไปใช้ (Apply)` with automatic `.bak` backup creation, and `🗑 ยกเลิก (Discard)`.
- **IDE Diagnostics Panel:** Tabular view of detected project and file issues with one-click `🤖 ส่งให้ AI แก้ไขอัตโนมัติ (Send to AI)`.
- **Background Test Console:** Embedded dark monospace terminal widget with one-click test execution and preset buttons.

#### 🛠 Autonomous MCP Diagnostic Tools
- Added 7 new autonomous tools for AI agents:
  - `inspect_ide_diagnostics`: Scan files or entire workspaces for syntax and static errors.
  - `create_code_draft`: Stage code modifications in the Drafts tab for user inspection.
  - `apply_code_draft`: Apply approved drafts to target files.
  - `discard_code_draft`: Discard unneeded drafts.
  - `list_code_drafts`: Enumerate pending and finished drafts.
  - `run_background_test`: Trigger automated test runs in the background.
  - `get_background_test_status`: Check test results and terminal output.

#### 🧠 Agent Tool Loop & Response Synthesis Enhancements
- **Loop Breaker:** Detects repeated tool calls with identical arguments to prevent long execution stalls.
- **GitHub README Optimization:** Directly retrieves raw `README.md` for GitHub repository links in `fetch_web_page` to prevent HTML bloat.
- **Compulsory Thai Synthesis:** Enforces structured 4-part response synthesis to eliminate abrupt cut-offs and `(ดำเนินการเสร็จสิ้น)`.
- **Fallback Log Reporting:** Automatically generates structured markdown reports from execution logs if the model stays silent.

## [v1.0.6] - 2026-09-16

### 🚀 Initial Major Consolidated Release — MAX for AI

#### 💻 Desktop GUI & Visual Workspace

- **Desktop Window UI:** Modern Tkinter desktop application with Charcoal Dark & Clean Light themes, status indicators, and background system tray.
- **Interactive Project Folder Picker:** Switch working projects in real-time (`📁 <Project Name>`), automatically anchoring all relative MCP tools (`read_file`, `write_file`, `replace_file_content`, `run_command`, `run_python_code`) to the target repository.
- **Dynamic Context Prompt:** Injects active project directory and constraints into AI context with on-disk verification requirements.
- **Real-Time Tool Feedback:** Streams autonomous tool calls and green/red diff blocks into thinking bubbles as tools execute.
- **Screen Crop & Markup:** Capture and crop any screen region (`Ctrl+Alt+A` or global `Ctrl+C` then `Ctrl+A`) and send directly into chat.

#### ⚡ Terminal CLI (`max`)

- **Single-Shot Prompting:** Fast headless execution via `max -p "<prompt>"` or `python main.py -p "<prompt>"`.
- **Project Selection:** Anchor commands to external projects via `--workspace <path>` / `-w <path>`, or interactive `/workspace` and `/cd`.
- **Autonomous Tool Loops:** Self-directed file reading, editing, diffing, and test execution with disk verification.
- **Cross-Platform:** Works on Windows (PowerShell/CMD), Linux, macOS, Docker, and Android Termux.

#### 👥 Multi-Agent Team Pipeline

- **Role-Based Collaboration:** Orchestrate Planner -> Coder -> Reviewer pipelines in CLI (`/team run`) and GUI Team Room.
- **Autonomous Tool Access:** Pipeline agents can call project tools directly to edit code and run tests rather than merely returning text snippets.

#### 📦 JavaScript & TypeScript SDK (`@karanztez/max-ai`)

- **Published to GitHub Packages:** Installable via `npm install @karanztez/max-ai`.
- **Core Classes:** `MaxAgent`, `MaxSession` (stateful memory), and `MaxTeam` (linked agent pipelines).
- **Discord Bot Kit:** Build Discord AI bots with `createDiscordBot()` and message splitting (<2000 chars code-block safe).
- **`MaxConverter` Adapters:** Format converters between MAX AI, Google Gemini, OpenAI, Anthropic Claude, Discord, Markdown tables, and Plain Text.

#### 🐍 Python SDK & API (`max_ai`)

- **Package:** `import max_ai` with `max_ai.Agent`, `max_ai.Session`, and `max_ai.Team`.
- **Discord Bot Kit:** High-level `create_max_bot()` with multi-turn room memory and slash commands.
- **Async & Sync:** First-class async API for FastAPI and Discord integration.

#### 🔒 Security & Stability

- **Windows DPAPI & Unix `chmod 600`:** Encrypted credentials and provider profiles storage.
- **Packaged EXE Fixes:** Standalone EXEs safely discover external Python interpreters for Python execution without re-launching the GUI.
