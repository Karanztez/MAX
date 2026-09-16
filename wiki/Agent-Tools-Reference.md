# 🛠 Agent Tools Reference (34+ Built-in MCP Tools)

เอกสารอ้างอิงเครื่องมืออัตโนมัติ (Built-in Agent Tools) ทั้งหมดที่ AI ในระบบ MAX สามารถเรียกใช้งานได้

---

## 1. 🗂 File & Code Operations (การจัดการไฟล์และโค้ด)

| เครื่องมือ | คำอธิบาย | ตัวอย่าง Parameter |
| :--- | :--- | :--- |
| `replace_file_content` | ผ่าตัดแก้โค้ดเฉพาะจุดแบบแม่นยำ พร้อมแสดง Diff เขียว-แดง แบบ Gemini/Antigravity | `target_file`, `target_content`, `replacement_content`, `start_line`, `end_line` |
| `read_file` | อ่านเนื้อหาไฟล์แบบเต็มหรือตามช่วงบรรทัด | `file_path`, `offset`, `limit` |
| `write_file` | สร้างหรือเขียนทับไฟล์ใหม่ | `file_path`, `content` |
| `edit_file_snippet` | ค้นหาและแทนที่ข้อความในไฟล์ | `file_path`, `old_snippet`, `new_snippet` |
| `get_file_info` | ดูขนาด วันที่แก้ไข และ Metadata ของไฟล์ | `file_path` |
| `delete_file` | ลบไฟล์เดี่ยวออกจากระบบ | `file_path` |
| `list_directory` | แสดงรายชื่อไฟล์และโฟลเดอร์ | `directory_path`, `depth` |
| `search_files` | ค้นหาข้อความหรือ Regex ในโปรเจกต์ (แบบ `ripgrep`) | `directory`, `pattern`, `case_sensitive` |

---

## 2. 🌐 Web & Networking (ท่องเว็บและเน็ตเวิร์ก)

*ทุกคำขอเข้าถึงเว็บไซต์จะต้องผ่านระบบ **Web Domain Security Guard** เสมอ*

| เครื่องมือ | คำอธิบาย | ตัวอย่าง Parameter |
| :--- | :--- | :--- |
| `search_web` | ค้นหาข้อมูลล่าสุดจากอินเทอร์เน็ต | `query`, `num_results` |
| `fetch_web_content` | ดึงเนื้อหาหน้าเว็บ แปลงเป็นข้อความ Markdown ที่อ่านง่าย | `url` |
| `http_request` | ส่งคำขอ HTTP GET / POST / PUT / DELETE พร้อม Headers และ JSON payload | `url`, `method`, `headers`, `json_data` |

---

## 3. 🐙 GitHub Operations (จัดการ GitHub Repository)

| เครื่องมือ | คำอธิบาย | ตัวอย่าง Parameter |
| :--- | :--- | :--- |
| `github_search_repos` | ค้นหาคลังเก็บโค้ดบน GitHub | `query`, `sort` |
| `github_get_repo` | ดูข้อมูลดาว, ภาษา, Description ของ Repo | `owner`, `repo` |
| `github_read_file` | อ่านไฟล์บน GitHub โดยตรงไม่ต้องโคลน | `owner`, `repo`, `path`, `ref` |
| `github_list_issues` | ดึงรายการ Issues และ Pull Requests | `owner`, `repo`, `state` |
| `github_clone_repo` | สั่งโคลน Repository ลงเครื่อง | `owner`, `repo`, `dest_dir` |

---

## 4. 🧩 Skill Management (จัดการสกิลอัตโนมัติ)

| เครื่องมือ | คำอธิบาย | ตัวอย่าง Parameter |
| :--- | :--- | :--- |
| `install_skill` | ติดตั้งสกิลจาก GitHub หรือ Markdown text และ Hot-reload ทันที | `source`, `skill_name` |
| `remove_skill` | ลบสกิลออกจากระบบอย่างปลอดภัย | `skill_name` |
| `list_skills` | ดึงรายชื่อสกิลทั้งหมดที่พร้อมใช้งาน | - |

---

## 5. 🎨 Multimedia Generation (สร้างภาพและวิดีโอ)

| เครื่องมือ | คำอธิบาย | ตัวอย่าง Parameter |
| :--- | :--- | :--- |
| `generate_image` | สร้างรูปภาพความละเอียดสูงจาก Prompt (Flux, Turbo, DALL-E) | `prompt`, `output_path`, `aspect_ratio` |
| `generate_video` | สร้างวิดีโอหรือภาพเคลื่อนไหวสั้น (Wan2.1 / MP4) | `prompt`, `output_path`, `duration` |

---

## 6. ⚙️ System & Execution (รันคำสั่งและควบคุมระบบ)

| เครื่องมือ | คำอธิบาย | ตัวอย่าง Parameter |
| :--- | :--- | :--- |
| `run_command` | สั่งรันคำสั่ง Shell / Terminal แบบปลอดภัย | `command`, `cwd`, `timeout` |
| `run_python_code` | รันโค้ด Python ใน Sandbox พร้อมดึงผลลัพธ์กลับมา | `code` |
| `list_processes` | ตรวจสอบ Process ที่กำลังทำงานในเครื่อง | `filter_name` |
| `get_system_info` | ตรวจสอบ OS, CPU, RAM, Disk, Architecture | - |
| `get_environment_variable` | ดึงค่าตัวแปรระบบ | `name` |

---

## 7. 📦 Project Packaging & Utilities

| เครื่องมือ | คำอธิบาย | ตัวอย่าง Parameter |
| :--- | :--- | :--- |
| `export_project_zip` | บีบอัดไฟล์โปรเจกต์เป็น ZIP ส่งเข้าโฟลเดอร์ Downloads | `source_dir`, `output_filename` |
| `git_status` | ตรวจสอบสถานะการเปลี่ยนแปลงใน Git | - |
| `git_diff` | ดูความแตกต่างของโค้ดใน Git | - |
| `git_log` | ดูประวัติ Commit ใน Git | `limit` |
| `json_format` | แปลงหรือจัดฟอร์แมต JSON | `data`, `indent` |
| `hash_data` | คำนวณค่าแฮช MD5, SHA1, SHA256 | `data`, `algorithm` |
| `base64_codec` | เข้ารหัส / ถอดรหัส Base64 | `action`, `text` |
| `calculate` | คำนวณผลลัพธ์ทางคณิตศาสตร์อย่างแม่นยำ | `expression` |
| `get_current_time` | ดึงวันและเวลาปัจจุบันตาม Timezone | `timezone` |
