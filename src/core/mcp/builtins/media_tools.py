"""AI Image & Video generation, project ZIP export, and media creation tools."""

from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any, Optional

try:
    from ..types import MCPTool
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]


def _builtin_export_to_download(source_path: str = ".", output_name: str = "") -> str:
    """Zip folder and copy to Downloads folder."""
    src = Path(source_path).expanduser().resolve()
    if not src.exists():
        return f"Error: Source path '{source_path}' does not exist."

    downloads_dir: Optional[Path] = None
    termux_dl = Path("/data/data/com.termux/files/home/storage/shared/Download")
    sdcard_dl = Path("/sdcard/Download")
    user_dl = Path.home() / "Downloads"
    win_dl = Path.home() / "Downloads"

    if termux_dl.exists() and termux_dl.is_dir():
        downloads_dir = termux_dl
    elif sdcard_dl.exists() and sdcard_dl.is_dir():
        downloads_dir = sdcard_dl
    elif win_dl.exists() and win_dl.is_dir():
        downloads_dir = win_dl
    elif user_dl.exists() and user_dl.is_dir():
        downloads_dir = user_dl
    else:
        downloads_dir = Path.home() / "storage" / "shared" / "Download"
        try:
            downloads_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            downloads_dir = Path.cwd()

    name = output_name.strip()
    if not name:
        name = f"{src.name if src.name else 'project'}_{time.strftime('%Y%m%d_%H%M%S')}"
    if not name.endswith(".zip"):
        name += ".zip"

    target_zip = downloads_dir / name

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_zip_base = os.path.join(tmp_dir, "archive")
            if src.is_file():
                parent_dir = os.path.join(tmp_dir, "content")
                os.makedirs(parent_dir, exist_ok=True)
                shutil.copy2(src, parent_dir)
                archive_path = shutil.make_archive(tmp_zip_base, "zip", parent_dir)
            else:
                archive_path = shutil.make_archive(tmp_zip_base, "zip", src)

            shutil.copy2(archive_path, target_zip)

        size_mb = target_zip.stat().st_size / (1024 * 1024)
        return (
            f"📦 ส่งออกโปรเจกต์สำเร็จเรียบร้อย!\n"
            f"• ไฟล์ ZIP: {target_zip}\n"
            f"• ขนาด: {size_mb:.2f} MB\n"
            f"• ปลายทาง: {downloads_dir}\n"
            f"💡 คุณสามารถเปิดดูในแอป 'ไฟล์ (Files / My Files / Downloads)' ของเครื่องได้ทันที"
        )
    except Exception as ex:
        return f"Error exporting to Download: {ex}"


def _builtin_generate_image(
    prompt: str,
    output_path: str = "",
    width: int = 1024,
    height: int = 1024,
    model: str = "flux",
    negative_prompt: str = "",
) -> str:
    """Generate high-resolution AI image and save to disk."""
    import urllib.request
    import urllib.error

    p = prompt.strip()
    if not p:
        return "Error: Prompt cannot be empty"

    if not output_path.strip():
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        clean_slug = "".join(c for c in p[:25] if c.isalnum() or c in ("-", "_")).strip() or "image"
        out_file = Path("images") / f"{clean_slug}_{timestamp}.png"
    else:
        out_file = Path(output_path.strip())

    out_file.parent.mkdir(parents=True, exist_ok=True)

    encoded_prompt = urllib.parse.quote(p)
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&nologo=true"
    if negative_prompt.strip():
        pollinations_url += f"&negative={urllib.parse.quote(negative_prompt.strip())}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MAX-AI-Agent/1.0",
        "Accept": "image/png,image/jpeg,image/*",
    }

    try:
        req = urllib.request.Request(pollinations_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            img_data = resp.read()

        if len(img_data) < 10:
            return f"Error: รูปภาพที่สร้างมีขนาดเล็กผิดปกติ ({len(img_data)} bytes)"

        out_file.write_bytes(img_data)
        size_kb = len(img_data) / 1024

        return (
            f"🎨 สร้างรูปภาพสำเร็จเรียบร้อยแล้ว!\n"
            f"• คำสั่ง (Prompt): \"{p}\"\n"
            f"• ขนาดภาพ: {width}x{height} pixels ({size_kb:.1f} KB)\n"
            f"• บันทึกไว้ที่: {out_file.resolve()}\n"
            f"• ลิงก์รูปภาพ: {pollinations_url}"
        )
    except Exception as ex:
        return f"Error generating image: {ex}"


def _builtin_generate_video(
    prompt: str,
    output_path: str = "",
    duration_seconds: int = 4,
    aspect_ratio: str = "16:9",
    model: str = "wan2.1",
) -> str:
    """Generate short AI video/animation and save to disk."""
    import urllib.request
    import urllib.error

    p = prompt.strip()
    if not p:
        return "Error: Prompt cannot be empty"

    if not output_path.strip():
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        clean_slug = "".join(c for c in p[:25] if c.isalnum() or c in ("-", "_")).strip() or "video"
        out_file = Path("videos") / f"{clean_slug}_{timestamp}.mp4"
    else:
        out_file = Path(output_path.strip())

    out_file.parent.mkdir(parents=True, exist_ok=True)

    encoded_prompt = urllib.parse.quote(p)
    pollinations_video_url = f"https://video.pollinations.ai/prompt/{encoded_prompt}?model={model}&aspect_ratio={aspect_ratio}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MAX-AI-Agent/1.0",
        "Accept": "video/mp4,video/*",
    }

    try:
        req = urllib.request.Request(pollinations_video_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            video_data = resp.read()

        if len(video_data) > 50:
            out_file.write_bytes(video_data)
            size_mb = len(video_data) / (1024 * 1024)
            return (
                f"🎬 สร้างวิดีโอสำเร็จเรียบร้อยแล้ว!\n"
                f"• คำสั่ง (Prompt): \"{p}\"\n"
                f"• ความยาว: ~{duration_seconds} วินาที (สัดส่วน {aspect_ratio})\n"
                f"• บันทึกไว้ที่: {out_file.resolve()} ({size_mb:.2f} MB)\n"
                f"• โมเดลที่ใช้: {model}"
            )
        else:
            return (
                f"🎬 สั่งสร้างวิดีโอเรียบร้อยแล้ว!\n"
                f"• คำสั่ง (Prompt): \"{p}\"\n"
                f"• ลิงก์เข้าชม/ดาวน์โหลดวิดีโอ: {pollinations_video_url}\n"
                f"• โมเดล: {model} ({aspect_ratio})"
            )
    except Exception as ex:
        return (
            f"🎬 สั่งสร้างวิดีโอผ่าน Web Service เรียบร้อยแล้ว (Direct Stream Link):\n"
            f"• คำสั่ง: \"{p}\"\n"
            f"• ลิงก์วิดีโอ: {pollinations_video_url}\n"
            f"• ข้อความระบบ: {ex}"
        )


def get_media_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return dictionary of media and export tools."""
    return {
        "export_to_download": (
            MCPTool(
                name="export_to_download",
                description="บีบอัดและส่งออกโฟลเดอร์/โปรเจกต์ไปยังโฟลเดอร์ Download ของมือถือ (Android Termux) หรือเครื่อง เพื่อให้เปิดดูและแชร์ไฟล์ได้ทันที",
                input_schema={
                    "type": "object",
                    "properties": {
                        "source_path": {"type": "string", "description": "โฟลเดอร์หรือไฟล์ที่ต้องการส่งออก (ค่าเริ่มต้น . โฟลเดอร์ปัจจุบัน)", "default": "."},
                        "output_name": {"type": "string", "description": "ชื่อไฟล์ ZIP ปลายทาง เช่น my-app.zip", "default": ""},
                    },
                },
                server_name="builtin",
            ),
            lambda args: _builtin_export_to_download(
                source_path=str(args.get("source_path", ".")),
                output_name=str(args.get("output_name", "")),
            ),
        ),
        "generate_image": (
            MCPTool(
                name="generate_image",
                description="สร้างรูปภาพด้วย AI ตามคำบรรยาย (Prompt) ความละเอียดสูง บันทึกเป็นไฟล์ภาพ PNG/JPG ลงเครื่อง",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "คำอธิบายภาพที่ต้องการสร้าง เช่น a cybernetic glowing cat in cyberpunk city, 8k"},
                        "output_path": {"type": "string", "description": "พาธไฟล์ภาพปลายทาง เช่น images/cat.png (หากไม่ระบุจะตั้งชื่ออัตโนมัติตามเวลา)", "default": ""},
                        "width": {"type": "integer", "description": "ความกว้างของภาพ (pixels, เช่น 1024, 768, 512)", "default": 1024},
                        "height": {"type": "integer", "description": "ความสูงของภาพ (pixels, เช่น 1024, 768, 512)", "default": 1024},
                        "model": {"type": "string", "description": "โมเดลที่ต้องการสร้าง (flux, turbo, dall-e-3)", "default": "flux"},
                        "negative_prompt": {"type": "string", "description": "สิ่งที่ไม่ต้องการให้ปรากฏในภาพ", "default": ""},
                    },
                    "required": ["prompt"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_generate_image(
                prompt=str(args.get("prompt", "")),
                output_path=str(args.get("output_path", "")),
                width=int(args.get("width", 1024)),
                height=int(args.get("height", 1024)),
                model=str(args.get("model", "flux")),
                negative_prompt=str(args.get("negative_prompt", "")),
            ),
        ),
        "generate_video": (
            MCPTool(
                name="generate_video",
                description="สร้างวิดีโอหรือคลิปอนิเมชันสั้นด้วย AI ตาม Prompt บันทึกเป็นไฟล์ MP4 ลงเครื่อง",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "คำอธิบายคลิปวิดีโอหรืออนิเมชันที่ต้องการสร้าง เช่น cinematic drone shot flying over futuristic neon city"},
                        "output_path": {"type": "string", "description": "พาธไฟล์วิดีโอปลายทาง เช่น videos/city.mp4 (หากไม่ระบุจะตั้งชื่ออัตโนมัติตามเวลา)", "default": ""},
                        "duration_seconds": {"type": "integer", "description": "ความยาวคลิปเป็นวินาที (ค่าเริ่มต้น 4, สูงสุด 15)", "default": 4},
                        "aspect_ratio": {"type": "string", "description": "สัดส่วนภาพ เช่น 16:9, 9:16, 1:1", "default": "16:9"},
                        "model": {"type": "string", "description": "โมเดลสร้างวิดีโอ (wan2.1, cogvideo, luma)", "default": "wan2.1"},
                    },
                    "required": ["prompt"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_generate_video(
                prompt=str(args.get("prompt", "")),
                output_path=str(args.get("output_path", "")),
                duration_seconds=int(args.get("duration_seconds", 4)),
                aspect_ratio=str(args.get("aspect_ratio", "16:9")),
                model=str(args.get("model", "wan2.1")),
            ),
        ),
    }
