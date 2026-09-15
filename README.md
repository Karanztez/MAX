# MAX (MaxPlus AI)

🪶 โปรแกรม AI Assistant สำหรับ Windows พร้อมระบบแนบ/ครอปภาพ, Multi-Provider Profiles, Built-in MCP Tools, Markdown Skills และการตรวจจับบริบทโปรเจกต์อัตโนมัติ

---

## ฟีเจอร์หลัก (Key Features)

- **🎨 Minimalist Theme:** ดีไซน์เรียบหรู พร้อมโหมด Charcoal Grey (`#1e1f20`) และ Clean White (`#ffffff`)
- **🪶 MAX Identity & Pixel Icon:** โลโก้และไอคอนขนนกพิกเซล พร้อม System Tray และปุ่มคำสั่งสไตล์มินิมอล
- **📁 Active Project Context:** แถบเลือกโปรเจกต์แบบคลิกเลือกโฟลเดอร์ได้ทันที พร้อม Inject บริบทและโครงสร้างไฟล์ให้โมเดล AI อัตโนมัติ
- **🖼 Screenshot & Markup Tools:** จับภาพหน้าจอด้วยคีย์ลัด พร้อมเครื่องมือวาดกล่อง/ลูกศร/ไฮไลท์ และคัดลอก DIB Native ทันที
- **⚡ Multi-Provider & Model Switching:** สลับระหว่าง Gemini, Claude, OpenAI, และ Custom Profile ได้ทันทีจากแถบด้านบน
- **🔒 Windows DPAPI Encryption:** เข้ารหัสความปลอดภัย API Key ด้วยชิปความปลอดภัยเฉพาะเครื่อง Windows
- **🧩 Skills System:** โหลดชุดคำสั่งและเชี่ยวชาญเฉพาะทางจาก `skills/*/SKILL.md` (เช่น `blender-3d`, `pixel-artist`, `overblock-minecraft`, `code-reviewer`)
- **🛠 Model Context Protocol (MCP):** รองรับ Tool Calling อัตโนมัติและเชื่อมต่อ Stdio MCP Server

---

## การติดตั้งและการเริ่มใช้งาน (Getting Started)

### 1. ติดตั้ง Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 2. รันโปรแกรม
```powershell
python main.py
```

---

## คีย์ลัด (Shortcuts)

| คำสั่ง | คีย์ลัด | รายละเอียด |
| :--- | :--- | :--- |
| **วางภาพ / ข้อความ** | `Ctrl + V` | วางภาพจาก Clipboard หรือข้อความ Unicode |
| **จับภาพหน้าจอ (Global)** | `Ctrl + C` แล้วกด `Ctrl + A` | แคปและครอปหน้าจอได้ทันทีแม้พับหน้าต่างลง Tray |
| **จับภาพหน้าจอโดยตรง** | `Ctrl + Alt + A` | เปิดหน้าต่าง Screen Crop Overlay |
| **ยืนยันการแคป** | `Enter` | บันทึกพื้นที่ที่เลือกส่งเข้าห้องแชท |
| **ยกเลิกการแคป** | `Esc` | ปิดหน้าต่างแคปหน้าจอ |
