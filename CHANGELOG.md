<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to **MAX for AI** are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
