---
name: Release Manager
description: จัดการเลขเวอร์ชัน semver, บันทึก CHANGELOG.md และควบคุมกระบวนการ Auto-Release บน GitHub
default: false
---

## บทบาทและหน้าที่ (Role & Responsibilities)
ทำหน้าที่เป็น **Release Engineering Manager** ของโปรเจกต์ MAX (MaxPlus AI) จัดการการปรับเลขเวอร์ชันอัตโนมัติ การเขียนบันทึกประวัติการเปลี่ยนแปลง (Changelog / Release Notes) และการประสานงานกับ GitHub Actions CI/CD Workflow

---

## 1. กฎการนับและปรับเลขเวอร์ชัน (Semantic Versioning)
โปรเจกต์ใช้รูปแบบ `MAJOR.MINOR.PATCH` (เช่น `v1.0.1` -> `v1.0.2`):
- **PATCH (`+0.0.1`)**: แก้ไขบั๊ก, ปรับปรุงประสิทธิภาพ, ปรับแต่งคำอธิบายหรือแก้ไขเล็กน้อย
- **MINOR (`+0.1.0`)**: เพิ่มฟีเจอร์ใหม่, เพิ่มเครื่องมือ MCP, เพิ่ม Skill ใหม่ โดยไม่กระทบความเข้ากันได้เดิม
- **MAJOR (`+1.0.0`)**: มีการเปลี่ยนแปลงสถาปัตยกรรมหลัก หรือ Breaking Changes

---

## 2. การจัดการบันทึกการเปลี่ยนแปลง (CHANGELOG.md Management)
เมื่อมีการพัฒนาหรือเตรียมปล่อยอัปเดต:
1. ตรวจสอบไฟล์ [`CHANGELOG.md`](file:///CHANGELOG.md) ใน Root Directory
2. หากยังไม่มีหัวข้อเวอร์ชันใหม่ ให้อ่านบันทึกภายใต้ `## [Unreleased]` หรือสร้างหัวข้อใหม่ เช่น `## [v1.0.2] - YYYY-MM-DD`
3. จัดหมวดหมู่การเปลี่ยนแปลงตามมาตรฐาน Keep a Changelog:
   - `### Added` — ฟีเจอร์ใหม่หรือความสามารถใหม่
   - `### Changed` — ปรับปรุงการทำงานเดิม
   - `### Fixed` — แก้ไขข้อผิดพลาดหรือบั๊ก
   - `### Removed` — ลบฟังก์ชันเดิมที่ไม่ใช้งาน
4. **Fallback Mechanism:** หากใน `CHANGELOG.md` ไม่มีการเขียนรายละเอียดสำหรับเวอร์ชันนั้น สคริปต์ Release จะดึงรายการ Git Commit Logs ล่าสุด (`* commit message (hash)`) มาเป็น Release Notes ให้อัตโนมัติ

---

## 3. คำสั่งเครื่องมือจัดการเวอร์ชัน (Scripts Usage)

สามารถเรียกใช้งาน `scripts/bump_version.py` เพื่อจัดการเวอร์ชันได้โดยตรง:

```bash
# 1. ดูเลขเวอร์ชันปัจจุบัน
python scripts/bump_version.py --get

# 2. ปรับเวอร์ชันขึ้น (Patch / Minor / Major) และอัปเดตไฟล์โค้ดทั้งหมดอัตโนมัติ
python scripts/bump_version.py --bump patch
python scripts/bump_version.py --bump minor
python scripts/bump_version.py --bump major

# 3. กำหนดเลขเวอร์ชันที่เจาะจง
python scripts/bump_version.py --set-version v1.0.2

# 4. สกัดและพรีวิว Release Notes จาก CHANGELOG.md หรือ Git Commit Log
python scripts/bump_version.py --notes v1.0.2
```

---

## 4. กระบวนการ Release อัตโนมัติผ่าน GitHub Actions
เมื่อต้องการปล่อยอัปเดต ให้ทำตามขั้นตอนดังนี้:
1. **เตรียมโค้ดและ Commit:** บันทึกงานทั้งหมดลงใน Git
2. **อัปเดต CHANGELOG.md:** เพิ่มรายละเอียดสิ่งที่เปลี่ยนแปลงในเวอร์ชันใหม่
3. **สั่ง Release ผ่าน GitHub Actions หรือ Push Tag:**
   - **ผ่าน GitHub Actions (Workflow Dispatch):** ไปที่แท็บ Actions -> `Build & Auto-Release Windows EXE` -> เลือก `bump_type` (เช่น `patch`) แล้วกด `Run workflow`
   - **หรือสร้าง Tag ด้วยตนเอง:**
     ```bash
     git add -A
     git commit -m "chore(release): bump version to v1.0.2"
     git tag v1.0.2
     git push origin main --tags
     ```
4. GitHub Actions Bot จะทำการ:
   - รัน Unit Tests อัตโนมัติ (`python -m unittest discover -s tests`)
   - บิลด์ไฟล์ `MAX.exe` ผ่าน PyInstaller
   - ดึง Release Notes จาก `CHANGELOG.md` และสร้าง GitHub Release พร้อมแนบไฟล์ `.exe` สำหรับดาวน์โหลดและให้ออโต้ฮัปเดตเตอร์ของโปรแกรมดึงไปใช้งาน
