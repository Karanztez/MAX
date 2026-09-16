# 🪶 MAX for AI

🪶 ผู้ช่วย AI อัจฉริยะแบบ Cross-Platform (Windows, Linux, macOS, Android Termux) พร้อมระบบ Desktop GUI, Terminal CLI, Autonomous Tools 34+ ชนิด, Multi-Agent Team Pipeline, และ SDK รองรับทั้ง Python & JavaScript

---

## ⚡ ติดตั้งอัตโนมัติใน 1 คำสั่ง (One-Line Automated Install)

### 🐧 Linux / macOS / 📱 Android (Termux)

เปิด Terminal หรือ Termux แล้ววางคำสั่งนี้:

```bash
curl -sSL https://raw.githubusercontent.com/Karanztez/MAX/main/install.sh | bash
```

### 🪟 Windows (PowerShell)

เปิด PowerShell แล้ววางคำสั่งนี้:

```powershell
irm https://raw.githubusercontent.com/Karanztez/MAX/main/install.ps1 | iex
```

---

## 🚀 การเรียกใช้งานทั่วไป (Quick Usage)

หลังจากติดตั้งแล้ว สามารถเรียกใช้งานคำสั่ง `max` ได้จากทุกที่ใน Terminal:

```bash
# 1. เปิดโหมด Terminal Interactive Chat (คุยต่อเนื่อง / รันเครื่องมืออัตโนมัติ)
max

# 2. ยิงคำถามเดียว (Single-shot prompt)
max -p "ค้นหาข้อมูลเกี่ยวกับ Python 3.14 ล่าสุดให้หน่อย"

# 3. กำหนดโมเดลเฉพาะเจาะจง
max -m claude-sonnet-4-6 -p "ตรวจสอบไฟล์ในโฟลเดอร์นี้และสรุปโค้ด"

# 4. ให้ Agent แก้โปรเจกต์อื่นโดยระบุ workspace ชัดเจน
max --workspace "C:\path\to\project" -p "ตรวจโค้ด แก้บั๊กจริง แล้วรัน tests ยืนยันผล"

# 5. เปิดหน้าต่าง GUI Desktop (สำหรับ Windows/Desktop ที่มีหน้าจอ)
max-gui
```

---

## 📚 WIKI & คู่มือการใช้งาน (Documentation & User Guide)

เอกสารคู่มือการใช้งานฉบับสมบูรณ์ถูกแยกเป็นหมวดหมู่ในโฟลเดอร์ [`wiki/`](wiki/) และ [GitHub Wiki](https://github.com/Karanztez/MAX/wiki):

- 🪟 **[Windows User Guide & Technical Manual](wiki/Windows-Guide.md)** — การใช้งาน Desktop GUI, Screen Snip, DPAPI, Terminal CLI
- 🐧 **[Linux & Server User Guide & Technical Manual](wiki/Linux-Guide.md)** — การใช้งานบน Ubuntu/Debian/Arch/VPS, Headless Agent, Cron, Security Guard
- 📱 **[Android (Termux) Mobile Workflow Guide](wiki/Android-Termux-Guide.md)** — การติดตั้งบนมือถือ, การ Export ZIP ส่งตรงเข้าเครื่อง
- 🛠 **[Agent Tools Reference (34+ Built-in Tools)](wiki/Agent-Tools-Reference.md)** — เจาะลึกเครื่องมืออัตโนมัติทั้งหมด (Code Diff, Git, Web, System, Media)
- 🧩 **[Skills Management Guide](wiki/Skills-Management.md)** — วิธีการติดตั้งสกิลอัตโนมัติจาก GitHub (`/skills`, `install_skill`)
- 🛡 **[Web Domain Security Guard](wiki/Web-Security.md)** — ระบบคัดกรองความปลอดภัยและการขอสิทธิ์เข้าถึงเว็บไซต์ภายนอก

---

### 🪟 สรุปการใช้งาน Windows (Quick Summary)

MAX บน Windows รองรับทั้งหน้าต่าง **Desktop GUI ที่ล้ำสมัย** และ **Terminal CLI** ใน PowerShell / Windows Terminal / CMD พร้อมระบบความปลอดภัยระดับฮาร์ดแวร์ด้วย Windows DPAPI

#### 1. วิธีการติดตั้งบน Windows

- **วิธีที่ 1 (อัตโนมัติผ่าน PowerShell):**

  ```powershell
  irm https://raw.githubusercontent.com/Karanztez/MAX/main/install.ps1 | iex
  ```

- **วิธีที่ 2 (ติดตั้งแบบพัฒนาผ่าน Git & Python):**

  ```powershell
  git clone https://github.com/Karanztez/MAX.git
  cd MAX
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -e .
  ```

#### 2. การเปิดใช้งานและฟีเจอร์เด่นบน Windows

- **Desktop GUI (`max-gui`):**
  - รันคำสั่ง `max-gui` หรือดับเบิลคลิกไฟล์ชอร์ตคัตบนเดสก์ท็อป
  - รองรับธีม Charcoal Dark & Clean Light
  - ระบบ **System Tray**: สามารถพับหน้าต่างลงไปทำงานอยู่เบื้องหลังได้
  - **Screen Crop & Snip (`Ctrl + Alt + A`):** กดคีย์ลัดสากลเพื่อจับภาพหน้าจอส่วนที่ต้องการ แล้ว AI จะวิเคราะห์ภาพทันที
  - **Clipboard Image Paste (`Ctrl + V`):** สามารถ Copy รูปภาพจากไหนก็ได้ แล้วกด `Ctrl + V` แปะลงในช่องแชทได้ทันที

- **Terminal CLI (`max`):**
  - รันใน **Windows Terminal** หรือ **PowerShell**
  - ระบุโปรเจกต์ด้วย `max --workspace "C:\path\to\project"` หรือเปลี่ยนระหว่างใช้งานด้วย `/workspace <path>`
  - รองรับ Colorized Diff Renderer แสดงโค้ดสีเขียว `+` และสีแดง `-` แบบ Antigravity / Gemini
  - มีระบบ Auto-updater สั่งอัปเดตเวอร์ชันใหม่ได้ในคำสั่งเดียวผ่าน `/update`

#### 3. ข้อมูลทางเทคนิคและตำแหน่งไฟล์ (Windows)

- **ไฟล์การตั้งค่า & API Keys:** `%APPDATA%\max\settings.json` (เข้ารหัสด้วย Windows Data Protection API / DPAPI ปลอดภัยจากการขโมยคีย์)
- **ประวัติการแชท (Chat History):** `%APPDATA%\max\chat_history.json`
- **โฟลเดอร์สกิลเสริม (Skills):** `%APPDATA%\max\skills\` หรือ `.\skills\` ในโปรเจกต์
- **การตั้งค่า Environment Variables (ถ้าต้องการ):**
  - `MAX_SETTINGS_DIR`: กำหนดโฟลเดอร์เก็บ config เองได้

#### 4. คำสั่งลัดในแชท (Slash Commands บน Windows)

- `/setup` — เปิดวิซาร์ดตั้งค่า AI Provider และ Model แบบเลือกหมายเลข [1..N]
- `/workspace <path>` หรือ `/cd <path>` — ดูหรือเปลี่ยนโฟลเดอร์โปรเจกต์ที่ Agent ใช้อ่าน แก้ไฟล์ และรันคำสั่ง
- `/models` หรือ `/model <name>` — ดูรายชื่อและสลับโมเดล AI
- `/skills` หรือ `/skill install <repo>` — ติดตั้งสกิลอัตโนมัติจาก GitHub
- `/security` หรือ `/domains` — ตั้งค่าความปลอดภัยการเข้าถึงเว็บไซต์ภายนอก
- `/export` หรือ `/download` — บีบอัดโปรเจกต์เป็น ZIP ส่งเข้าโฟลเดอร์ Downloads ทันที
- `/update` — ตรวจสอบและอัปเดต MAX เป็นเวอร์ชันล่าสุดจาก GitHub

---

### 🐧 Linux & Server Wiki & Guide

MAX ถูกออกแบบให้ทำงานบน Linux (Ubuntu, Debian, Arch, CentOS, Fedora, Alpine, Docker, VPS, Cloud Servers) ได้อย่างสมบูรณ์แบบในโหมด **Headless Terminal Agent** โดยไม่ต้องติดตั้ง X11 หรือ GUI Libraries

#### 1. วิธีการติดตั้งบน Linux

- **วิธีที่ 1 (อัตโนมัติใน 1 บรรทัด):**

  ```bash
  curl -sSL https://raw.githubusercontent.com/Karanztez/MAX/main/install.sh | bash
  ```

- **วิธีที่ 2 (ติดตั้งแบบ Manual ผ่าน Python venv):**

  ```bash
  # ติดตั้ง prerequisites (Ubuntu/Debian)
  sudo apt update && sudo apt install -y python3 python3-pip python3-venv git curl

  # โคลนโปรเจกต์และติดตั้ง
  git clone https://github.com/Karanztez/MAX.git ~/.max-ai
  cd ~/.max-ai
  python3 -m venv venv
  ./venv/bin/pip install --upgrade pip
  ./venv/bin/pip install -e .

  # เพิ่ม symlink เพื่อเรียกใช้คำสั่ง max ได้จากทุกที่
  sudo ln -sf ~/.max-ai/venv/bin/max /usr/local/bin/max
  ```

#### 2. การใช้งานบน Linux Server & VPS

- **โหมด Interactive CLI:**

  ```bash
  max
  ```

  ใช้งานคุยโต้ตอบกับ AI พร้อมสั่งให้เขียนโค้ด, ตรวจสอบ log, ค้นหาไฟล์, รันคำสั่ง shell และแก้บัคโปรเจกต์ได้อัตโนมัติ

- **โหมด Non-interactive / Scripting / CI-CD:**

  ```bash
  # ตรวจสอบโค้ดในโปรเจกต์แล้วส่งผลลัพธ์
  max -p "ช่วย review โค้ดในโฟลเดอร์ src/ และรายงานจุดที่ควรปรับปรุง"

  # ไพพ์ (Pipe) ข้อความหรือ log เข้าไปให้ AI วิเคราะห์
  cat /var/log/nginx/error.log | max -p "วิเคราะห์หาสาเหตุ error ใน log นี้"
  ```

- **ใช้งาน Desktop GUI บน Linux (ถ้ามี Desktop Environment เช่น GNOME / KDE / XFCE):**

  ```bash
  sudo apt install -y python3-tk
  max-gui
  ```

#### 3. ข้อมูลทางเทคนิคและความปลอดภัย (Linux)

- **ตำแหน่งไฟล์ Config & Keys:** `~/.config/max/settings.json`
- **การรักษาความปลอดภัย (POSIX Permission Guard):**
  - MAX จะตั้งค่าสิทธิ์ไฟล์ Config เป็น `chmod 600` (อ่าน/เขียนได้เฉพาะ Owner เท่านั้น) อัตโนมัติ ป้องกันไม่ให้ user อื่นในเซิร์ฟเวอร์เข้าถึง API Key ได้
- **ประวัติการแชท (Chat History):** `~/.config/max/chat_history.json`
- **โฟลเดอร์สกิลเสริม (Skills):** `~/.config/max/skills/` หรือ `$(pwd)/skills/`

#### 4. การตั้งค่าบน Linux Server ให้รันอัตโนมัติ (Systemd / Cron)

สามารถเขียน shell script เพื่อเรียกใช้ `max` ใน cron jobs หรือ systemd service ได้ เช่น การตรวจสุขภาพเซิร์ฟเวอร์ทุกวัน:

```bash
# ตัวอย่าง script: /opt/daily_report.sh
#!/usr/bin/env bash
df -h | max -p "ตรวจสอบพื้นที่ดิสก์ หากมีพาร์ติชันใดเกิน 85% ให้สรุปคำเตือน" >> /var/log/disk_report.log
```

---

### 📱 Android (Termux) Quick Guide

- ติดตั้ง Termux และรันคำสั่ง One-liner:

  ```bash
  curl -sSL https://raw.githubusercontent.com/Karanztez/MAX/main/install.sh | bash
  ```

- รองรับคำสั่ง `/export` บีบอัดโปรเจกต์ส่งเข้า `/sdcard/Download` ของมือถือได้ทันที

---

## 🐍 MAX AI Python SDK & Public API Package

คุณสามารถนำ MAX AI ไปติดตั้งและใช้งานเป็น **Python Package (`import max_ai`)** ในโปรเจกต์อื่นๆ เช่น **Discord Bot, Telegram Bot, FastAPI Server, หรือ Automation Scripts** ได้ทันที

### 📦 การติดตั้งในโปรเจกต์อื่น

```bash
# ติดตั้งแบบมาตรฐาน
pip install git+https://github.com/Karanztez/MAX.git

# หรือติดตั้งพร้อมส่วนเสริมสำหรับ Discord Bot
pip install "max-ai[discord] @ git+https://github.com/Karanztez/MAX.git"
```

---

### 🤖 1. ตัวอย่างสร้าง Discord AI Bot (ไม่ถึง 10 บรรทัด)

```python
import os
from max_ai.discord import create_max_bot

bot = create_max_bot(
    discord_token=os.environ.get("DISCORD_BOT_TOKEN"),
    max_api_key=os.environ.get("MAXPLUS_API_KEY"),
    model="gemini-2.5-flash",
    command_prefix="!max ",
    system_prompt="You are MAX, a helpful and friendly Discord AI assistant.",
    enable_tools=True,  # เปิดใช้งานเครื่องมือคำนวณและค้นหาอัตโนมัติ
)

# เริ่มต้นบอท (รองรับ Multi-turn chat แยกตามห้อง, Mention @Bot, และคำสั่ง !max reset)
bot.run()
```

---

### ⚡ 2. ใช้งานแบบ Python SDK ทั่วไป (Sync & Async)

```python
import max_ai

# ถาม-ตอบคำถามเดียว (Single-shot Ask)
reply = max_ai.ask("อธิบายทฤษฎีควอนตัมแบบเข้าใจง่าย")
print(reply)

# สร้าง Agent พร้อม Session Memory (จำบริบทการสนทนา)
agent = max_ai.Agent(model="gemini-2.5-flash")
session = agent.create_session(session_id="channel-101")

# คุยต่อเนื่อง
res1 = session.send("สวัสดีครับ ผมชื่อสมชาย")
res2 = session.send("ผมชื่ออะไรนะ?")
print(res2.text)  # "คุณชื่อสมชายครับ"

# รองรับ Asynchronous สำหรับ FastAPI / Discord / Aiohttp
async def handle_request():
    response = await agent.ask_async("ช่วยเขียนโค้ด Python FastAPI")
    print(response)
```

---

### 👥 3. Multi-Agent Team Pipeline ในโค้ด Python

```python
import max_ai

team = max_ai.Team(name="Dev Team")
team.add_member(1, name="Architect", role="planner", model="gemini-2.5-pro")
team.add_member(2, name="Engineer", role="coder", model="deepseek-v4.1-flash")
team.add_member(3, name="Auditor", role="reviewer", model="claude-3-7-sonnet")

# เชื่อมต่อกระบวนการทำงาน: Architect -> Engineer -> Auditor
team.link(from_id=1, to_id=2)
team.link(from_id=2, to_id=3)

results = team.run("สร้าง Discord bot เล่นเพลง")
print(results["final_output"])
```

---

## JavaScript / TypeScript SDK

The Node.js SDK is published to GitHub Packages as `@karanztez/max-ai` and requires Node.js 18 or newer.

```bash
npm config set @karanztez:registry https://npm.pkg.github.com
npm install @karanztez/max-ai
```

Set `MAXPLUS_API_KEY`, then use the one-shot API or a stateful session:

```ts
import { MaxAgent, ask } from "@karanztez/max-ai";

const answer = await ask("Explain quantum computing simply");

const agent = new MaxAgent({ model: "gemini-2.5-flash" });
const session = agent.createSession("channel-101");
console.log((await session.send("My name is Alex")).text);
console.log((await session.send("What is my name?")).text);
```

For an existing `discord.js` client, attach the included message handler:

```ts
import { Client, GatewayIntentBits } from "discord.js";
import { createDiscordBot } from "@karanztez/max-ai";

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent],
});

createDiscordBot({
  discordToken: process.env.DISCORD_BOT_TOKEN!,
  commandPrefix: "!max ",
}).attachToClient(client);

await client.login(process.env.DISCORD_BOT_TOKEN);
```

The package also exports `MaxTeam` for linked agent pipelines and `MaxConverter` helpers for OpenAI, Gemini, Anthropic, Discord, Markdown, and plain-text formats.

---

## 🛠 ฟีเจอร์หลัก (Key Features)

- **🌐 Cross-Platform & Mobile Support:** รองรับเต็มรูปแบบทั้ง Windows GUI, Linux Server, VPS, Docker, macOS และมือถือ Android (Termux)
- **⚡ Built-in Agent Tools (34+ เครื่องมืออัตโนมัติ):**
  - **ผ่าตัดแก้โค้ด & จัดการไฟล์:** `replace_file_content` (แสดง diff เขียว-แดง แบบ Gemini), `edit_file_snippet`, `read_file`, `write_file`, `get_file_info`, `delete_file`, `list_directory`, `search_files` (grep)
  - **ท่องเว็บ & API:** `search_web`, `fetch_web_content`, `http_request` พร้อมระบบ Web Domain Security Verification
  - **จัดการ GitHub:** `github_search_repos`, `github_get_repo`, `github_read_file`, `github_list_issues`, `github_clone_repo`
  - **จัดการสกิลอัตโนมัติ:** `install_skill`, `remove_skill`, `list_skills` (ดึงสกิลจาก GitHub และ Hot-reload ทันที)
  - **สร้างภาพและวิดีโอ AI:** `generate_image`, `generate_video`
  - **ส่งออกโปรเจกต์:** `export_project_zip` ส่งเข้า Downloads โฟลเดอร์ในคลิกเดียว
  - **ควบคุมระบบ & คำสั่ง:** `run_command` (Shell runner), `run_python_code` (Sandbox executor), `list_processes`, `get_environment_variable`
  - **ระบบ Git:** `git_status`, `git_diff`, `git_log`
  - **ประมวลผลข้อมูล:** `json_format`, `hash_data`, `base64_codec`, `calculate`, `get_current_time`, `get_system_info`
- **🔒 Cross-Platform Encrypted Storage:** ปลอดภัยด้วย Windows DPAPI บน Windows และ Unix User-only (`chmod 600`) บน Linux/macOS/Termux
- **⚡ Multi-Provider & Model Switching:** สลับระหว่าง Gemini, Claude Native, Claude Cursor, Chinese Specials, Grok Heavy, GPT PRO Supreme, และ OpenAI ได้ทันที
- **🧩 Markdown Skills:** โหลดชุดคำสั่งเฉพาะทางจาก `skills/*/SKILL.md` (เช่น `blender-3d`, `pixel-artist`, `overblock-minecraft`, `code-reviewer`, `github-specialist`)
- **🎨 Minimalist Desktop GUI:** ดีไซน์เรียบหรู พร้อมโหมด Charcoal Dark & Clean Light พร้อมระบบ Screen Crop & Markup ทันที

---

## ⌨️ คีย์ลัดใน Desktop GUI (Shortcuts)

| คำสั่ง | คีย์ลัด | รายละเอียด |
| :--- | :--- | :--- |
| **วางภาพ / ข้อความ** | `Ctrl + V` | วางภาพจาก Clipboard หรือข้อความ Unicode |
| **จับภาพหน้าจอ (Global)** | `Ctrl + C` แล้วกด `Ctrl + A` | แคปและครอปหน้าจอได้ทันทีแม้พับหน้าต่างลง Tray |
| **จับภาพหน้าจอโดยตรง** | `Ctrl + Alt + A` | เปิดหน้าต่าง Screen Crop Overlay |
| **ยืนยันการแคป** | `Enter` | บันทึกพื้นที่ที่เลือกส่งเข้าห้องแชท |
| **ยกเลิกการแคป** | `Esc` | ปิดหน้าต่างแคปหน้าจอ |

---

## 📄 สัญญาอนุญาตการใช้งาน (License)

Copyright (c) 2026 **Karanztez**. All Rights Reserved.

- 🟢 **การใช้งานส่วนตัว & การศึกษา**: อนุญาตให้ใช้งาน ศึกษา และดัดแปลงได้ฟรีเพื่อการใช้งานส่วนบุคคลและการศึกษา
- 🚫 **ข้อห้ามทางการค้า**: **ไม่อนุญาตให้นำซอฟต์แวร์ไปจำหน่าย จ่ายแจกแบบคิดค่าบริการ หรือใช้ในเชิงพาณิชย์ทุกกรณี นอกจากจะได้รับอนุญาตเป็นลายลักษณ์อักษร (Commercial License) จากเจ้าของลิขสิทธิ์เท่านั้น**
- 📩 **ติดต่อขอสิทธิ์เชิงพาณิชย์**: [https://github.com/Karanztez](https://github.com/Karanztez)
