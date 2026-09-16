"""File management, code inspection, and precision code editing tools."""

from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Optional

try:
    from ..diff_engine import render_diff, replace_content_chunk
    from ..types import MCPTool
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.diff_engine import render_diff, replace_content_chunk  # type: ignore[no-redef]
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]


def _resolve_safe_path(target_path: str) -> Path:
    p = Path(target_path).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return p


def _builtin_list_dir(path: str = ".", max_depth: int = 2) -> str:
    """List directory structure up to max_depth."""
    base = _resolve_safe_path(path)
    if not base.exists():
        return f"Error: Path '{path}' does not exist."
    if not base.is_dir():
        return f"Error: Path '{path}' is a file, not a directory."

    lines: list[str] = [f"📂 Directory: {base}"]

    def _walk(current: Path, depth: int, prefix: str = "") -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            lines.append(f"{prefix}└── [Permission Denied]")
            return

        entries = [e for e in entries if not e.name.startswith(".git") and e.name != "__pycache__"]
        for idx, entry in enumerate(entries):
            is_last = idx == len(entries) - 1
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")

            if entry.is_dir():
                lines.append(f"{prefix}{connector}📁 {entry.name}/")
                _walk(entry, depth + 1, child_prefix)
            else:
                size_kb = entry.stat().st_size / 1024
                lines.append(f"{prefix}{connector}📄 {entry.name} ({size_kb:.1f} KB)")

    _walk(base, 1)
    return "\n".join(lines[:300])


def _builtin_read_file(path: str, start_line: int = 1, line_count: int = 200) -> str:
    """Read file content with line numbers."""
    target = _resolve_safe_path(path)
    if not target.exists():
        return f"Error: File '{path}' does not exist."
    if not target.is_file():
        return f"Error: Path '{path}' is a directory, not a file."

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        all_lines = content.splitlines()
        total_lines = len(all_lines)

        s = max(1, start_line)
        e = min(total_lines, s + max(1, line_count) - 1)

        numbered = [f"{i:4d} | {all_lines[i - 1]}" for i in range(s, e + 1)]
        header = f"📄 File: {target} (Lines {s}-{e} of {total_lines})\n{'─'*50}\n"
        return header + "\n".join(numbered)
    except Exception as ex:
        return f"Error reading file '{path}': {ex}"


def _builtin_write_file(path: str, content: str, overwrite: bool = True) -> str:
    """Write text or code content to file."""
    target = _resolve_safe_path(path)
    if target.exists() and not overwrite:
        return f"Error: File '{path}' already exists and overwrite is set to False."

    try:
        old_content = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        diff = render_diff(old_content, content, filename=target.name) if old_content else ""
        diff_part = f"\n\n{diff}" if diff else ""
        return f"✅ บันทึกไฟล์ '{target.name}' สำเร็จ ({len(content.splitlines())} บรรทัด, {len(content)} bytes){diff_part}"
    except Exception as ex:
        return f"Error writing to file '{path}': {ex}"


def _builtin_replace_file_content(
    path: str,
    target_content: str,
    replacement_content: str,
    allow_multiple: bool = False,
) -> str:
    """
    Surgically replace specific blocks of code inside a file and display the visual diff (Gemini/Antigravity style).
    """
    target = _resolve_safe_path(path)
    if not target.exists():
        return f"Error: File '{path}' does not exist."
    if not target.is_file():
        return f"Error: Path '{path}' is not a file."

    try:
        original = target.read_text(encoding="utf-8")
        ok, updated_text, diff_summary = replace_content_chunk(
            original_text=original,
            target_content=target_content,
            replacement_content=replacement_content,
            allow_multiple=allow_multiple,
        )
        if not ok:
            return updated_text  # contains error description

        target.write_text(updated_text, encoding="utf-8")
        return (
            f"✅ แก้ไขโค้ดในไฟล์ `{target.name}` สำเร็จเรียบร้อยแล้ว!\n\n"
            f"{diff_summary}"
        )
    except Exception as ex:
        return f"Error editing file '{path}': {ex}"


def _builtin_edit_file_snippet(path: str, target: str, replacement: str) -> str:
    """Backward-compatible wrapper for snippet replacement."""
    return _builtin_replace_file_content(path, target_content=target, replacement_content=replacement, allow_multiple=False)


def _builtin_get_file_info(path: str) -> str:
    """Get metadata about a file."""
    p = _resolve_safe_path(path)
    if not p.exists():
        return f"Error: File '{path}' does not exist."

    stat = p.stat()
    size_kb = stat.st_size / 1024
    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))

    if p.is_file():
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            lines_count = len(content.splitlines())
        except Exception:
            lines_count = 0
        return (
            f"📄 File: {p.name}\n"
            f"Path: {p}\n"
            f"Size: {size_kb:.2f} KB ({stat.st_size} bytes)\n"
            f"Lines: {lines_count}\n"
            f"Modified: {mtime}"
        )
    else:
        return f"📁 Directory: {p.name}\nPath: {p}\nModified: {mtime}"


def _builtin_delete_file(path: str) -> str:
    """Delete a file or directory."""
    p = _resolve_safe_path(path)
    if not p.exists():
        return f"Error: Path '{path}' does not exist."

    try:
        if p.is_file():
            p.unlink()
            return f"✅ ลบไฟล์ '{p.name}' สำเร็จ"
        elif p.is_dir():
            shutil.rmtree(p)
            return f"✅ ลบโฟลเดอร์ '{p.name}' สำเร็จ"
        return f"Error: Unknown path type '{path}'"
    except Exception as ex:
        return f"Error deleting '{path}': {ex}"


def _builtin_search_files(query: str, path: str = ".", is_regex: bool = False, file_glob: str = "*") -> str:
    """Search for string or regex pattern across workspace files."""
    base = _resolve_safe_path(path)
    if not base.exists():
        return f"Error: Path '{path}' does not exist."

    flags = re.IGNORECASE
    try:
        pattern = re.compile(query if is_regex else re.escape(query), flags)
    except re.error as e:
        return f"Error: Invalid regular expression '{query}': {e}"

    matches: list[str] = []
    max_results = 40

    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"__pycache__", "node_modules", "dist", "build", "venv", ".venv"}]
        for fname in files:
            if not Path(fname).match(file_glob):
                continue
            fpath = Path(root) / fname
            try:
                if fpath.stat().st_size > 1024 * 1024:
                    continue  # skip files > 1MB
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                for line_no, line in enumerate(text.splitlines(), start=1):
                    if pattern.search(line):
                        rel = fpath.relative_to(base)
                        matches.append(f"{rel}:{line_no}: {line.strip()[:140]}")
                        if len(matches) >= max_results:
                            break
            except Exception:
                continue
        if len(matches) >= max_results:
            break

    if not matches:
        return f"🔍 ไม่พบข้อความ '{query}' ใน '{path}' (ตัวกรอง: {file_glob})"

    header = f"🔍 พบผลการค้นหา '{query}' ({len(matches)} รายการ):\n{'─'*50}\n"
    return header + "\n".join(matches)


def get_file_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return dictionary of file & code editing tools."""
    return {
        "list_directory": (
            MCPTool(
                name="list_directory",
                description="แสดงโครงสร้างโฟลเดอร์และไฟล์ในโฟลเดอร์ที่กำหนด (Workspace / Project tree)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของโฟลเดอร์ (ค่าเริ่มต้นคือ . หรือโฟลเดอร์ปัจจุบัน)", "default": "."},
                        "max_depth": {"type": "integer", "description": "ระดับความลึกสูงสุดของโฟลเดอร์ย่อย (ค่าเริ่มต้น 2)", "default": 2},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_list_dir(str(args.get("path", ".")), max_depth=int(args.get("max_depth", 2))),
        ),
        "read_file": (
            MCPTool(
                name="read_file",
                description="อ่านเนื้อหาไฟล์โค้ดหรือไฟล์ข้อความในเครื่อง พร้อมระบุบรรทัด",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์ที่ต้องการอ่าน"},
                        "start_line": {"type": "integer", "description": "บรรทัดเริ่มต้น (ค่าเริ่มต้น 1)", "default": 1},
                        "line_count": {"type": "integer", "description": "จำนวนบรรทัดที่ต้องการอ่าน (ค่าเริ่มต้น 200)", "default": 200},
                    },
                    "required": ["path"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_read_file(
                str(args.get("path", "")),
                start_line=int(args.get("start_line", 1)),
                line_count=int(args.get("line_count", 200)),
            ),
        ),
        "write_file": (
            MCPTool(
                name="write_file",
                description="สร้างหรือบันทึกไฟล์ข้อความ/โค้ดในโปรเจกต์แบบเต็มไฟล์",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์ที่ต้องการเขียน"},
                        "content": {"type": "string", "description": "เนื้อหาข้อความหรือโค้ดที่ต้องการบันทึก"},
                        "overwrite": {"type": "boolean", "description": "อนุญาตให้เขียนทับไฟล์เดิมหรือไม่ (ค่าเริ่มต้น True)", "default": True},
                    },
                    "required": ["path", "content"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_write_file(
                str(args.get("path", "")),
                str(args.get("content", "")),
                overwrite=bool(args.get("overwrite", True)),
            ),
        ),
        "replace_file_content": (
            MCPTool(
                name="replace_file_content",
                description="ผ่าตัดแก้ไขโค้ดเฉพาะจุดที่ต้องการในไฟล์ (Gemini / Antigravity style) โดยระบุโค้ดเดิมและโค้ดใหม่ พร้อมแสดง Diff เขียว/แดง ให้ตรวจสอบทันที",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์ที่ต้องการแก้ไข"},
                        "target_content": {"type": "string", "description": "ข้อความหรือบล็อกโค้ดเดิมที่ต้องการแทนที่ (ต้องตรงกับในไฟล์ทุกตัวอักษร)"},
                        "replacement_content": {"type": "string", "description": "บล็อกโค้ดใหม่ที่จะนำมาแทนที่"},
                        "allow_multiple": {"type": "boolean", "description": "แทนที่ทุกจุดที่ตรงกันหรือไม่ (ค่าเริ่มต้น False)", "default": False},
                    },
                    "required": ["path", "target_content", "replacement_content"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_replace_file_content(
                path=str(args.get("path", "")),
                target_content=str(args.get("target_content", "")),
                replacement_content=str(args.get("replacement_content", "")),
                allow_multiple=bool(args.get("allow_multiple", False)),
            ),
        ),
        "edit_file_snippet": (
            MCPTool(
                name="edit_file_snippet",
                description="แทนที่ข้อความเดิมด้วยข้อความใหม่ในไฟล์",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์"},
                        "target": {"type": "string", "description": "ข้อความเดิม"},
                        "replacement": {"type": "string", "description": "ข้อความใหม่"},
                    },
                    "required": ["path", "target", "replacement"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_edit_file_snippet(
                path=str(args.get("path", "")),
                target=str(args.get("target", "")),
                replacement=str(args.get("replacement", "")),
            ),
        ),
        "get_file_info": (
            MCPTool(
                name="get_file_info",
                description="ตรวจสอบรายละเอียดไฟล์ (ขนาด, จำนวนบรรทัด, เวลาแก้ไขล่าสุด)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์"},
                    },
                    "required": ["path"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_get_file_info(str(args.get("path", ""))),
        ),
        "delete_file": (
            MCPTool(
                name="delete_file",
                description="ลบไฟล์หรือโฟลเดอร์",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "พาธของไฟล์หรือโฟลเดอร์ที่ต้องการลบ"},
                    },
                    "required": ["path"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_delete_file(str(args.get("path", ""))),
        ),
        "search_files": (
            MCPTool(
                name="search_files",
                description="ค้นหาข้อความหรือ Regular Expression ในไฟล์ต่างๆ ในโปรเจกต์ (Grep / Search)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "ข้อความหรือ regex ที่ต้องการค้นหา"},
                        "path": {"type": "string", "description": "โฟลเดอร์เริ่มต้นค้นหา (ค่าเริ่มต้น .)", "default": "."},
                        "is_regex": {"type": "boolean", "description": "ค้นหาด้วย Regex หรือไม่", "default": False},
                        "file_glob": {"type": "string", "description": "รูปแบบชื่อไฟล์ เช่น *.py, *.md, * (ค่าเริ่มต้น *)", "default": "*"},
                    },
                    "required": ["query"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_search_files(
                str(args.get("query", "")),
                path=str(args.get("path", ".")),
                is_regex=bool(args.get("is_regex", False)),
                file_glob=str(args.get("file_glob", "*")),
            ),
        ),
    }
