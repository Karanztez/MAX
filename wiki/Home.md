# 🪶 Welcome to MAX (MaxPlus AI) Wiki

**MAX (MaxPlus AI)** คือผู้ช่วย AI อัจฉริยะแบบ Cross-Platform (Windows, Linux, macOS, Android Termux) ที่มาพร้อมระบบ Terminal CLI, Desktop GUI ทรงพลัง, Built-in Agent Tools 34+ ชนิด, ระบบผ่าตัดแก้ไขโค้ดแบบ Gemini/Antigravity, Autonomous Skill Management, และการรักษาความปลอดภัยขั้นสูง

---

## 🧭 สารบัญเอกสาร (Wiki Navigation)

| หมวดหมู่ | ลิงก์เอกสาร | คำอธิบาย |
| :--- | :--- | :--- |
| 🪟 **Windows** | [[Windows Guide\|Windows-Guide]] | คู่มือการติดตั้งและใช้งาน Desktop GUI, Screen Snip, DPAPI, Terminal CLI บน Windows |
| 🐧 **Linux & Server** | [[Linux Guide\|Linux-Guide]] | คู่มือการติดตั้งบน Ubuntu/Debian/Arch/VPS, Headless Agent, Cron, Security Guard |
| 📱 **Android** | [[Android Termux Guide\|Android-Termux-Guide]] | คู่มือการใช้งานบนมือถือผ่าน Termux, Export ZIP, Mobile AI Assistant |
| 🛠 **Agent Tools** | [[Agent Tools Reference\|Agent-Tools-Reference]] | เจาะลึกเครื่องมืออัตโนมัติ 34+ ชนิด (Code Diff, Git, Web, System, Media) |
| 🧩 **Skills** | [[Skills Management\|Skills-Management]] | วิธีการติดตั้งสกิลอัตโนมัติจาก GitHub (`/skills`, `install_skill`) และสร้างสกิลเอง |
| 🛡 **Security** | [[Web & Data Security\|Web-Security]] | ระบบคัดกรองความปลอดภัยเว็บ (Domain Guard) และการเข้ารหัส Credentials |

---

## ⚡ Quick Start (ติดตั้งใน 1 บรรทัด)

### 🐧 Linux / macOS / 📱 Android (Termux)

```bash
curl -sSL https://raw.githubusercontent.com/Karanztez/MAX/main/install.sh | bash
```

### 🪟 Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/Karanztez/MAX/main/install.ps1 | iex
```

---

## 🚀 การเรียกใช้งานด่วน (Basic Commands)

```bash
# 1. เปิดโหมดแชทแบบโต้ตอบ (Interactive Chat + Tool Execution)
max

# 2. ยิงคำถามเดียว (Single-shot Prompt)
max -p "ช่วยเขียน script python ตรวจสอบ network และบันทึกลงไฟล์"

# 3. กำหนดโมเดล AI เฉพาะเจาะจง
max -m claude-sonnet-4-6 -p "สรุปโค้ดในโปรเจกต์นี้"

# 4. เปิด Desktop GUI (บน Windows หรือ Linux ที่มีหน้าจอ)
max-gui
```

---

## 📄 สัญญาอนุญาตการใช้งาน (License)

Copyright (c) 2026 **Karanztez**. All Rights Reserved.  
ซอฟต์แวร์นี้อนุญาตให้ใช้งานและศึกษาได้ฟรีสำหรับบุคคลทั่วไป **ไม่อนุญาตให้นำไปจำหน่ายหรือใช้ในเชิงพาณิชย์โดยไม่ได้รับอนุญาตเป็นลายลักษณ์อักษร**  
รายละเอียดเพิ่มเติม: [[LICENSE\|https://github.com/Karanztez/MAX/blob/main/LICENSE]]
