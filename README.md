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

## 🚀 การเรียกใช้งาน (Usage)

หลังจากติดตั้งแล้ว สามารถเรียกใช้งานคำสั่ง `max` ได้จากทุกที่ใน Terminal:

```bash
# 1. เปิดโหมด Terminal Interactive Chat (คุยต่อเนื่อง / รันเครื่องมืออัตโนมัติ)
max

# 2. ยิงคำถามเดียว (Single-shot prompt)
max -p "ค้นหาข้อมูลเกี่ยวกับ Python 3.14 ล่าสุดให้หน่อย"

# 3. กำหนดโมเดลเฉพาะเจาะจง
max -m claude-sonnet-4-6 -p "ตรวจสอบไฟล์ในโฟลเดอร์นี้และสรุปโค้ด"

# 4. เปิดหน้าต่าง GUI Desktop (สำหรับเครื่องที่มีหน้าจอ)
max-gui
```

---

## 🛠 ฟีเจอร์หลัก (Key Features)

- **🌐 Cross-Platform & Mobile Support:** รองรับเต็มรูปแบบทั้ง Windows GUI, Linux Server, VPS, Docker, macOS และมือถือ Android (Termux)
- **⚡ Built-in Agent Tools (23 เครื่องมือ):**
  - **ท่องเว็บ & API:** `search_web`, `fetch_web_content`, `http_request`
  - **จัดการโค้ด & แก้ไขไฟล์:** `edit_file_snippet` (ผ่าตัดแก้โค้ดเฉพาะจุด), `read_file`, `write_file`, `get_file_info`, `delete_file`, `list_directory`, `search_files` (grep)
  - **ควบคุมระบบ & คำสั่ง:** `run_command` (Shell runner), `run_python_code` (Sandbox executor), `list_processes`, `get_environment_variable`
  - **ระบบ Git:** `git_status`, `git_diff`, `git_log`
  - **ประมวลผลข้อมูล:** `json_format`, `hash_data`, `base64_codec`, `calculate`, `get_current_time`, `get_system_info`
- **🔒 Cross-Platform Encrypted Storage:** ปลอดภัยด้วย Windows DPAPI บน Windows และ Unix User-only (`chmod 600`) บน Linux/macOS/Termux
- **⚡ Multi-Provider & Model Switching:** สลับระหว่าง Gemini, Claude Native, Claude Cursor, Chinese Specials, Grok Heavy, GPT PRO Supreme, และ OpenAI ได้ทันที
- **🧩 Markdown Skills:** โหลดชุดคำสั่งเฉพาะทางจาก `skills/*/SKILL.md` (เช่น `blender-3d`, `pixel-artist`, `overblock-minecraft`, `code-reviewer`)
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


