# 🤝 Tencent TeamAI Integration (การทำงานร่วมกันเป็นทีม)

**Tencent TeamAI (`teamai-cli`)** คือเครื่องมือโอเพนซอร์สจาก Tencent ที่ช่วยจัดการ **Skills, Rules, MCP Servers, และ Team Learnings** ร่วมกันในทีมผ่าน Git Repository กลาง โดย MAX ได้ทำการเชื่อมต่อ TeamAI เข้ามาเป็น Built-in Agent Tools และ Slash Command เพื่อให้สามารถสั่งงานได้โดยตรงจากทั้ง **Desktop GUI** และ **Terminal CLI**

---

## 1. ข้อกำหนดเบื้องต้น (Prerequisites)

เนื่องจาก `teamai-cli` ทำงานบน Node.js คุณจะต้องมี:

1. **Node.js 20+** ติดตั้งอยู่บนเครื่อง ([ดาวน์โหลดจาก nodejs.org](https://nodejs.org/))
2. ติดตั้ง TeamAI CLI ทั่วทั้งระบบ:

   ```bash
   npm install -g teamai-cli
   ```

   *(หากไม่ได้ติดตั้งล่วงหน้า MAX จะพยายามเรียกผ่าน `npx -y teamai-cli` ให้อัตโนมัติ)*

---

## 2. คำสั่งควบคุมใน MAX (`/teamai`)

คุณสามารถพิมพ์คำสั่งเหล่านี้ในช่องแชทของ MAX (ทั้งใน GUI และ CLI) ได้ทันที:

| คำสั่ง | คำอธิบาย |
| --- | --- |
| `/teamai status` | ตรวจสอบสถานะการเชื่อมต่อ Git Repo ของทีม และเวอร์ชัน TeamAI |
| `/teamai pull` | ดึง Skills, Rules และคอนฟิก MCP ล่าสุดของทีมจาก GitHub มารีเฟรชลง MAX อัตโนมัติ |
| `/teamai push` | ส่งต่อทักษะใหม่หรือบทเรียนจากเซสชัน (Learnings) ขึ้นสู่ทีม |
| `/teamai init <repo_url>` | ผูกโปรเจกต์นี้เข้ากับ Git Repository ของทีม (เช่น `teamai init https://github.com/my-team/ai-skills`) |
| `/teamai help` | แสดงคู่มือคำสั่ง TeamAI ทั้งหมด |

---

## 3. การทำงานของ Agent MCP Tools (`teamai_command` & `teamai_sync`)

MAX มาพร้อมกับ Built-in MCP Tools ที่ AI สามารถเรียกใช้งานได้ด้วยตนเองอย่างอิสระ:

1. **`teamai_sync`**: เมื่อผู้ใช้บอกให้ AI *"ช่วยซิงค์ความรู้ของทีมหน่อย"* หรือ *"อัปเดตสกิลทีม"* AI จะเรียก tool นี้เพื่อสั่ง `teamai pull` และเรียก `SkillManager().refresh()` เพื่อให้สกิลใหม่มีผลในทันทีโดยไม่ต้องรีสตาร์ตโปรแกรม
2. **`teamai_command`**: อนุญาตให้ AI รันคำสั่งขั้นสูงของ TeamAI เช่น `teamai projects`, `teamai roles`, `teamai source` เพื่อจัดการการเข้าถึงสกิลตามบทบาทของผู้ใช้

---

## 4. แนะนำโครงสร้าง Team Repository

ใน Git Repo กลางของทีม แนะนำให้จัดโครงสร้างไฟล์ตามมาตรฐานของ TeamAI ดังนี้:

```text
my-team-skills/
├── skills/
│   ├── code-review/
│   │   └── SKILL.md
│   └── api-design/
│       └── SKILL.md
├── rules/
│   └── coding-standards.md
└── mcp/
    └── mcp.yaml
```

เมื่อรัน `/teamai pull` โฟลเดอร์ `skills/` จะถูกดึงลงมาที่โปรเจกต์ MAX ของทุกคนในทีมโดยอัตโนมัติ!
