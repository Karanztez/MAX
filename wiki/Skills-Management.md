# 🧩 Skills Management Guide

ระบบสกิล (Skills) ของ **MAX (MaxPlus AI)** ช่วยเพิ่มความสามารถเฉพาะทางให้กับ AI โดยไม่ต้องเขียนโปรแกรมเพิ่ม AI สามารถโหลดคำสั่ง กฎเกณฑ์ และขั้นตอนการทำงานเฉพาะทางจากไฟล์ `SKILL.md` ได้แบบไดนามิก

---

## 1. การติดตั้งสกิล (Installing Skills)

คุณสามารถติดตั้งสกิลได้ 2 ช่องทาง:

### 1. ให้ AI ติดตั้งอัตโนมัติผ่านแชท

บอก AI ตรงๆ ในช่องแชท:

```text
"ช่วยติดตั้งสกิล blender จาก https://github.com/Karanztez/MAX/tree/main/skills/blender-3d ให้หน่อย"
```

AI จะเรียกเครื่องมือ `install_skill` เพื่อดาวน์โหลดและติดตั้งให้ทันที

### 2. ใช้ Slash Command ใน CLI

```text
/skill install owner/repo/path/to/skill
/skill install https://raw.githubusercontent.com/.../SKILL.md
```

---

## 2. การดูรายชื่อและลบสกิล (Listing & Removing Skills)

- **ดูรายชื่อสกิลที่ติดตั้งอยู่:**

  ```text
  /skills
  ```

- **ลบสกิลที่ไม่ต้องการ:**

  ```text
  /skill remove blender-3d
  ```

---

## 3. โครงสร้างของไฟล์สกิล (Skill File Structure)

ไฟล์สกิลจะถูกบันทึกเป็น Markdown ที่มี Metadata ส่วนหัว (YAML Frontmatter):

```markdown
---
name: my-custom-skill
description: คำอธิบายสั้นๆ เกี่ยวกับหน้าที่ของสกิลนี้
version: 1.0.0
author: Your Name
---

# 🚀 My Custom Skill

## กฎและขั้นตอนการทำงาน
1. เมื่อผู้ใช้ขอให้ทำ X ให้ทำ Y
2. ใช้เครื่องมือ Z ในการตรวจสอบความถูกต้อง
```

ตำแหน่งโฟลเดอร์สกิล:

- **Global Skills:** `%APPDATA%\max\skills\` (Windows) หรือ `~/.config/max/skills/` (Linux)
- **Local Project Skills:** `./skills/` ภายในโปรเจกต์ปัจจุบัน

