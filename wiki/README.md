# 📚 MAX Official Wiki

โฟลเดอร์นี้รวบรวมเอกสาร Wiki ทางการของ **MAX (MaxPlus AI)** ซึ่งจัดเตรียมไว้สำหรับเผยแพร่บน [GitHub Wiki](https://github.com/Karanztez/MAX/wiki)

## 📄 รายการหน้า Wiki

- [`Home.md`](Home.md) — หน้าแรกของ Wiki, ภาพรวม, Quick Start
- [`Windows-Guide.md`](Windows-Guide.md) — คู่มือ Windows, Desktop GUI, Shortcuts, DPAPI, Terminal CLI
- [`Linux-Guide.md`](Linux-Guide.md) — คู่มือ Linux Server, VPS, Docker, Headless Agent, Cron & Systemd
- [`Android-Termux-Guide.md`](Android-Termux-Guide.md) — คู่มือ Android Termux และการ Export ZIP
- [`Agent-Tools-Reference.md`](Agent-Tools-Reference.md) — เอกสารเครื่องมือ Agent Tools ทั้ง 34+ รายการ
- [`Skills-Management.md`](Skills-Management.md) — คู่มือการติดตั้งและสร้างสกิลเสริม
- [`Web-Security.md`](Web-Security.md) — ระบบรักษาความปลอดภัย Web Domain Guard
- [`_Sidebar.md`](_Sidebar.md) — แถบนำทางด้านข้างของ GitHub Wiki
- [`_Footer.md`](_Footer.md) — ส่วนท้ายของหน้า GitHub Wiki

---

## 🚀 วิธีนำขึ้น GitHub Wiki

เมื่อกด **"Create the first page"** บนหน้า [GitHub Wiki ของโปรเจกต์](https://github.com/Karanztez/MAX/wiki) คุณสามารถ:

1. นำเนื้อหาจาก `Home.md` ไปวางแล้วกด **Save Page**
2. กด **New Page** เพิ่มหน้าอื่นๆ ตามชื่อไฟล์ด้านบน
3. หรือสามารถโคลน Git Wiki Repository ผ่าน:

```bash
git clone https://github.com/Karanztez/MAX.wiki.git
cp wiki/*.md MAX.wiki/
cd MAX.wiki
git add .
git commit -m "docs(wiki): publish initial wiki documentation"
git push origin master
```
