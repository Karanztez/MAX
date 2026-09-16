# 📱 Android (Termux) User Guide & Mobile Workflow

คู่มือการติดตั้งและใช้งาน **MAX (MaxPlus AI)** บนโทรศัพท์และแท็บเล็ตระบบปฏิบัติการ Android ผ่าน **Termux**

---

## 1. วิธีการติดตั้งบน Android (Termux)

### ข้อแนะนำเบื้องต้น

- ดาวน์โหลดและติดตั้งแอป **Termux** จาก [F-Droid](https://f-droid.org/en/packages/com.termux/) หรือ [GitHub Termux Releases](https://github.com/termux/termux-app/releases) (หลีกเลี่ยงการโหลดจาก Google Play Store เนื่องจากไม่มีการอัปเดตแพ็กเกจแล้ว)

### ขั้นตอนการติดตั้งอัตโนมัติ

เปิดแอป Termux แล้ววางคำสั่งนี้:

```bash
curl -sSL https://raw.githubusercontent.com/Karanztez/MAX/main/install.sh | bash
```

สคริปต์จะทำการ:

1. ขอสิทธิ์การเข้าถึงพื้นที่จัดเก็บข้อมูลบนเครื่อง (`termux-setup-storage`)
2. ติดตั้งแพ็กเกจที่จำเป็น (`python`, `git`, `curl`, `clang`)
3. ติดตั้ง MAX AI และสร้างคำสั่ง `max` ให้อัตโนมัติ

---

## 2. การใช้งาน MAX บนมือถือ

```bash
# 1. เข้าห้องแชทของ AI
max

# 2. สั่งให้ AI รันคำสั่งหรือเขียนโค้ด
max -p "เขียนสคริปต์สแกน WiFi ที่เปิดอยู่แล้วแสดงผล"
```

### ฟีเจอร์ที่ออกแบบมาสำหรับมือถือ

- **คำสั่ง `/export` หรือ `/download`:**
  - เมื่อคุณสั่งให้ AI พัฒนาโปรเจกต์ โค้ด หรือไฟล์ต่างๆ ใน Termux คุณสามารถพิมพ์ `/export` ได้ทันที
  - MAX จะบีบอัดทั้งโปรเจกต์เป็นไฟล์ `.zip` แล้วส่งตรงไปยังโฟลเดอร์ **`/sdcard/Download`** ของโทรศัพท์
  - คุณสามารถเปิดแอปตัวจัดการไฟล์ (Files / My Files) บน Android เพื่อเปิดไฟล์ ZIP หรือแชร์ให้เพื่อนได้ทันที!
- **ระบบ Self-Update (`/update`):**
  - สามารถพิมพ์ `/update` ภายในแชทเพื่อดึงโค้ดเวอร์ชันล่าสุดจาก GitHub ได้โดยไม่ต้องติดตั้งใหม่
