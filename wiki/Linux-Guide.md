# 🐧 Linux & Server User Guide & Technical Manual

คู่มือการติดตั้ง ใช้งาน และปรับแต่ง **MAX (MaxPlus AI)** บนระบบปฏิบัติการ Linux (Ubuntu, Debian, Arch, CentOS, Fedora, Alpine, Docker, VPS, Cloud Servers)

---

## 1. วิธีการติดตั้ง (Installation)

### วิธีที่ 1: ติดตั้งอัตโนมัติใน 1 คำสั่ง (One-Liner)

เปิด Terminal บนเครื่อง Linux / VPS แล้วรัน:

```bash
curl -sSL https://raw.githubusercontent.com/Karanztez/MAX/main/install.sh | bash
```

สคริปต์จะทำการ:

1. ตรวจสอบและแนะนำการติดตั้ง Python 3.8+ และ `venv`
2. โคลนโปรเจกต์ลงใน `~/.max-ai`
3. สร้างสภาพแวดล้อมเสมือน (Virtual Environment)
4. ทำการติดตั้งโปรแกรมและสร้าง Symlink ไปที่ `~/.local/bin/max` (และ `/usr/local/bin/max` หากมีสิทธิ์ sudo)

---

### วิธีที่ 2: ติดตั้งแบบ Manual ผ่าน Python venv

```bash
# 1. ติดตั้ง Dependencies พื้นฐาน (สำหรับ Ubuntu / Debian)
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git curl

# 2. โคลนและสร้าง Virtual Environment
git clone https://github.com/Karanztez/MAX.git ~/.max-ai
cd ~/.max-ai
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -e .

# 3. สร้าง Symlink ให้เรียกใช้ได้ทั่วระบบ
mkdir -p ~/.local/bin
ln -sf ~/.max-ai/venv/bin/max ~/.local/bin/max

# (ถ้ายังไม่มี ~/.local/bin ใน PATH ให้เพิ่มลงใน ~/.bashrc หรือ ~/.zshrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## 2. การใช้งานบน Linux Server & VPS

MAX บน Linux ถูกออกแบบให้เป็น **Headless Autonomous Agent** ที่สามารถสั่งงานได้ครบทุกฟังก์ชันโดยไม่ต้องมี Desktop GUI:

### 1. โหมด Interactive CLI (`max`)

```bash
max
```

- คุยโต้ตอบกับ AI ได้แบบเรียลไทม์
- สั่งให้ AI รันคำสั่ง Linux (`run_command`), ค้นหาไฟล์ด้วย `grep` (`search_files`), อ่านและผ่าตัดแก้โค้ด (`replace_file_content`), รันเทส และคอมมิต Git ได้อย่างเป็นอิสระ

### 2. โหมด Non-interactive & Automation (`max -p "..."`)

```bash
# สั่งตรวจทานความปลอดภัยของระบบ
max -p "ช่วยตรวจสอบ open ports ด้วย ss -tulpn และสรุปความปลอดภัย"

# วิเคราะห์ Log ไฟล์แบบ Pipe
cat /var/log/nginx/error.log | tail -n 100 | max -p "ช่วยวิเคราะห์ error ใน log นี้และเสนอวิธีแก้"

# ให้ AI สร้าง unit test ให้ไฟล์ในโปรเจกต์
max -p "เขียน unit test ครอบคลุมโค้ดใน src/core/mcp_manager.py ให้หน่อย"
```

### 3. การเปิดใช้งาน Desktop GUI (บน Ubuntu Desktop / GNOME / KDE)

หากคุณใช้งาน Linux ที่มีหน้าจอแสดงผล สามารถเปิด GUI ได้:

```bash
# ติดตั้ง Tkinter ก่อนเปิด GUI
sudo apt install -y python3-tk
max-gui
```

---

## 3. ความปลอดภัยและการจัดเก็บข้อมูลบน Linux (POSIX Security Guard)

MAX ให้ความสำคัญสูงสุดกับความปลอดภัยของเซิร์ฟเวอร์:

| รายการ | ตำแหน่งไฟล์บน Linux | กลไกความปลอดภัย |
| :--- | :--- | :--- |
| **Settings & Keys** | `~/.config/max/settings.json` | ระบบจะบังคับสิทธิ์ไฟล์เป็น `chmod 600` (User-only read/write) อัตโนมัติ ป้องกันไม่ให้ user อื่นในเซิร์ฟเวอร์แอบดู API Key |
| **Chat History** | `~/.config/max/chat_history.json` | เก็บประวัติการแชท |
| **Custom Skills** | `~/.config/max/skills/` | โฟลเดอร์เก็บสกิลเสริม |
| **Project Root Settings** | `./skills/` | โหลดสกิลประจำโฟลเดอร์โปรเจกต์ |

---

## 4. การรันงานอัตโนมัติด้วย Cron Job & Systemd

คุณสามารถตั้งค่าให้ MAX ตรวจสอบและดูแลระบบแทนคุณได้ตลอด 24 ชั่วโมง:

### ตัวอย่าง Cron Job รายวัน

สร้างสคริปต์ `/opt/scripts/daily_system_check.sh`:

```bash
#!/usr/bin/env bash
REPORT=$(max -p "ตรวจสอบอุณหภูมิ CPU, พื้นที่ดิสก์ (df -h) และการใช้งาน RAM (free -m) หากมีสิ่งผิดปกติให้ระบุคำเตือน")
echo "$REPORT" | mail -s "Daily Server Report" admin@example.com
```

เพิ่มใน `crontab -e`:

```cron
0 8 * * * /bin/bash /opt/scripts/daily_system_check.sh
```

---

## 5. การรันบน Docker / Container

หากต้องการรัน MAX ใน Docker Container สามารถใช้ Base Image `python:3.11-slim` ได้ทันที:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["max"]
```

รันคอนเทนเนอร์:

```bash
docker build -t max-ai .
docker run -it -v $(pwd):/workspace -w /workspace max-ai
```

---

## 6. การแก้ไขปัญหาที่พบบ่อย (Troubleshooting)

### Q1: เรียก `max` แล้วฟ้องว่า `command not found`

**วิธีแก้:** ตรวจสอบว่าได้เพิ่ม `~/.local/bin` เข้าใน `$PATH` หรือยัง:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Q2: GUI ไม่เปิด หรือฟ้อง `_tkinter.TclError: no display name`

**วิธีแก้:** หากคุณเชื่อมต่อผ่าน SSH โดยไม่มี X11 Forwarding จะไม่สามารถเปิด `max-gui` ได้ ให้ใช้โหมด Terminal CLI `max` แทน

