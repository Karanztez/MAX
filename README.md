# MAX (MaxPlus AI)

🪶 ผู้ช่วย AI อัจฉริยะแบบ Cross-Platform (Windows, Linux, macOS, Android Termux) พร้อมระบบ Terminal CLI, Built-in Agent Tools 23 ชนิด, Multi-Provider Profiles, Markdown Skills, และระบบจับภาพหน้าจอ

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

# 4. เปิดหน้าต่าง GUI Desktop (สำหรับ Windows/Desktop ที่มีหน้าจอ)
max-gui
```

---

## 📚 WIKI & คู่มือการใช้งาน (Documentation & User Guide)

### 🪟 Windows Wiki & Guide

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
