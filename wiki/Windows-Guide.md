# 🪟 Windows User Guide & Technical Manual

คู่มือฉบับสมบูรณ์สำหรับการติดตั้งและใช้งาน **MAX (MaxPlus AI)** บนระบบปฏิบัติการ Windows 10 / Windows 11

---

## 1. วิธีการติดตั้ง (Installation)

### วิธีที่ 1: ติดตั้งอัตโนมัติผ่าน PowerShell (แนะนำ)
เปิด **PowerShell** (ไม่ต้อง Run as Administrator ก็ได้) แล้ววางคำสั่ง:
```powershell
irm https://raw.githubusercontent.com/Karanztez/MAX/main/install.ps1 | iex
```
สคริปต์จะทำการ:
1. ตรวจสอบ Python 3.8+ (หากไม่มีจะแนะนำวิธีติดตั้ง)
2. โคลนหรือดาวน์โหลดโปรเจกต์มาไว้ที่ `%LOCALAPPDATA%\Programs\MAX`
3. สร้าง Virtual Environment (`.venv`) และติดตั้ง Dependencies
4. เพิ่มโฟลเดอร์สำหรับรันคำสั่ง `max` และ `max-gui` ลงใน User PATH อัตโนมัติ

---

### วิธีที่ 2: ติดตั้งแบบ Manual ด้วย Git & Python
```powershell
# โคลนโปรเจกต์
git clone https://github.com/Karanztez/MAX.git
cd MAX

# สร้าง Virtual Environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# ติดตั้ง Dependencies และ CLI entrypoints
pip install --upgrade pip
pip install -e .
```

---

## 2. การใช้งาน Desktop GUI (`max-gui`)

สั่งเปิดหน้าต่างแอปพลิเคชันด้วยคำสั่ง:
```powershell
max-gui
```

### ฟีเจอร์เด่นใน Desktop GUI:
1. **ธีมที่สวยงาม (Charcoal Dark & Clean Light):** เลือกโทนสีที่สบายตา ปรับแต่งขนาดฟอนต์ได้ตามต้องการ
2. **ระบบ System Tray:**
   - เมื่อกดปิดหน้าต่าง แอปพลิเคชันจะพับเก็บลงไปที่ System Tray (ไอคอนมุมขวาล่างของ Taskbar)
   - ดับเบิลคลิกไอคอนที่ Tray หรือคลิกขวาเลือก *Open MAX* เพื่อเปิดขึ้นมาใหม่ได้ทันที
3. **ระบบแคปหน้าจออัจฉริยะ (Screen Crop & Snip):**
   - **คีย์ลัดสากล:** กด `Ctrl + Alt + A` (หรือกด `Ctrl + C` ตามด้วย `Ctrl + A` ในหน้าต่าง GUI)
   - จะมี Overlay ปรากฏขึ้นมาให้ลากกรอบเลือกบริเวณที่ต้องการจับภาพ
   - กด `Enter` เพื่อยืนยัน รูปภาพจะถูกส่งเข้าไปในช่องแชทพร้อมให้คุณพิมพ์คำสั่งถาม AI ทันที
   - กด `Esc` เพื่อยกเลิก
4. **การวางภาพจาก Clipboard (`Ctrl + V`):**
   - สามารถกด `Print Screen` หรือ Copy ภาพจากเว็บ/โปรแกรมอื่น แล้วกด `Ctrl + V` ในช่องแชทได้ทันที

---

## 3. การใช้งาน Terminal CLI (`max`)

สั่งเปิดโหมด CLI ผ่าน **Windows Terminal**, **PowerShell** หรือ **CMD**:
```powershell
# เข้าสู่ห้องแชทแบบ Interactive
max

# สั่งงานแบบ Single-shot prompt
max -p "เขียนไฟล์ script.py สำหรับแปลงรูปภาพเป็น WebP ทั้งหมดในโฟลเดอร์"

# เลือกรันด้วยโมเดลเฉพาะ
max -m claude-sonnet-4-6 -p "ตรวจทานโค้ดและแก้ไขจุดผิดพลาด"
```

### คีย์ลัดและฟังก์ชันใน Terminal CLI:
- **Colorized Diff Code Viewer:** เมื่อ AI สั่งแก้ไขไฟล์ด้วย `replace_file_content` ระบบจะแสดงส่วนที่เพิ่มเป็นสีเขียว `+` และส่วนที่ตัดออกเป็นสีแดง `-` พร้อมเลขบรรทัด
- **Multi-Line Input:** กด `Enter` เพื่อส่งคำตอบ หรือ Shift+Enter (ขึ้นอยู่กับ Terminal)
- **ประวัติคำสั่ง:** กดลูกศรขึ้น/ลง เพื่อเรียกดูประวัติข้อความที่เคยพิมพ์

---

## 4. ตำแหน่งไฟล์และการเก็บรักษาความปลอดภัย (Windows DPAPI)

MAX ใช้มาตรฐานความปลอดภัยขั้นสูงของ Windows เพื่อรักษาความลับของ API Keys:

| รายการ | ตำแหน่งไฟล์บน Windows | รายละเอียดความปลอดภัย |
| :--- | :--- | :--- |
| **Settings & Keys** | `%APPDATA%\max\settings.json` | คีย์จะถูกเข้ารหัสผ่าน **Windows DPAPI (Data Protection API)** ซึ่งผูกกับ User Account เท่านั้น |
| **Chat History** | `%APPDATA%\max\chat_history.json` | เก็บประวัติการสนทนาเพื่อโหลดกลับมาใช้งานต่อ |
| **Custom Skills** | `%APPDATA%\max\skills\` หรือ `.\skills\` | โฟลเดอร์เก็บสกิล Markdown ที่ดาวน์โหลดหรือสร้างขึ้นเอง |
| **Web Allowed Domains** | `%APPDATA%\max\settings.json` (`allowed_domains`) | บันทึกโดเมนเว็บไซต์ที่ได้รับอนุญาตให้ AI เข้าถึง |

---

## 5. คำสั่งลัดในแชท (Slash Commands)

คุณสามารถพิมพ์คำสั่งเหล่านี้ในช่องแชทของ CLI เพื่อควบคุมการทำงานได้ทันที:

- `/setup` — เปิดวิซาร์ดตั้งค่าผู้ให้บริการ AI (OpenAI, Anthropic, Gemini, DeepSeek ฯลฯ)
- `/models` — แสดงรายชื่อโมเดลทั้งหมดที่พร้อมใช้งาน
- `/model <name>` — สลับไปใช้โมเดลที่ต้องการทันที
- `/skills` — แสดงรายการสกิลทั้งหมดที่ติดตั้งไว้
- `/skill install <repo>` — ติดตั้งสกิลจาก GitHub (เช่น `/skill install Karanztez/MAX/skills/blender-3d`)
- `/skill remove <name>` — ลบสกิลที่ไม่ต้องการออก
- `/security` หรือ `/domains` — ดูและจัดการรายชื่อเว็บไซต์ที่อนุญาตให้ AI ท่องเว็บ
- `/export` หรือ `/download` — บีบอัดโปรเจกต์เป็นไฟล์ `.zip` ส่งเข้าโฟลเดอร์ `Downloads`
- `/update` — ตรวจสอบและอัปเดต MAX เป็นเวอร์ชันล่าสุดจาก GitHub
- `/clear` — ล้างประวัติแชทในหน้าจอ
- `/exit` หรือ `/quit` — ออกจากโปรแกรม

---

## 6. การแก้ไขปัญหาที่พบบ่อย (Troubleshooting)

### Q1: รันคำสั่ง `max` แล้วขึ้นว่า `'max' is not recognized...`
**วิธีแก้:**
1. ตรวจสอบว่าได้เพิ่ม Scripts Path ลงใน User Environment Variables หรือยัง (เช่น `C:\Users\<User>\AppData\Local\Programs\Python\Python3xx\Scripts`)
2. หรือรันผ่าน Python โดยตรง: `python -m src.cli`

### Q2: พาวเวอร์เชลล์ติด `Execution Policy` ตอนรันสคริปต์
**วิธีแก้:** เปิด PowerShell แล้วพิมพ์:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
