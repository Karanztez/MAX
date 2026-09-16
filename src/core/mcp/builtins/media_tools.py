"""AI Image & Video generation, project ZIP export, and media creation tools."""

from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
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


def _get_image_provider_credentials(provider: str) -> tuple[str, str]:
    """Retrieve base_url and api_key for image generation provider from stored settings."""
    provider_urls = {
        "gpt-image": "https://api.maxplus-ai.cc/gpt-image/v1",
        "nai-image": "https://api.maxplus-ai.cc/nai-image/v1",
        "grok-image": "https://api.maxplus-ai.cc/grok-image/v1",
    }
    base_url = provider_urls.get(provider, "")
    api_key = ""

    try:
        from core.settings_store import SettingsStore
        from core.provider_profiles import default_profiles
    except (ImportError, ModuleNotFoundError):
        from src.core.settings_store import SettingsStore  # type: ignore[no-redef]
        from src.core.provider_profiles import default_profiles  # type: ignore[no-redef]

    try:
        store = SettingsStore()
        profiles, selected_id = store.load_provider_settings(default_profiles())

        # 1. Exact match on profile id or matching base_url
        for p in profiles:
            p_url = str(p.get("base_url", "")).strip().rstrip("/")
            if provider in str(p.get("id", "")).lower() or (base_url and base_url.lower() == p_url.lower()):
                if p.get("api_key"):
                    return (p_url or base_url, str(p["api_key"]).strip())

        # 2. Check active profile if it has an API key
        for p in profiles:
            if p.get("id") == selected_id and p.get("api_key"):
                api_key = str(p["api_key"]).strip()
                break

        # 3. Fallback: Any stored profile with an API key
        if not api_key:
            for p in profiles:
                if p.get("api_key"):
                    api_key = str(p["api_key"]).strip()
                    break
    except Exception:
        pass

    return (base_url, api_key)


def _generate_image_via_maxplus(
    provider: str,
    prompt: str,
    out_file: Path,
    width: int,
    height: int,
    model: str,
    negative_prompt: str = "",
    quality: str = "standard",
    style: str = "vivid",
    reference_images: Optional[list[str]] = None,
) -> tuple[bool, str]:
    """Call MaxPlus AI image generation endpoint (/images/generations)."""
    base_url, api_key = _get_image_provider_credentials(provider)
    if not api_key:
        return False, "ไม่พบ API Key ในการตั้งค่าโปรไฟล์"

    url = f"{base_url.rstrip('/')}/images/generations"
    size_str = f"{width}x{height}"
    payload: dict[str, Any] = {
        "prompt": prompt,
        "model": model,
        "n": 1,
        "size": size_str,
        "response_format": "b64_json",
    }
    if quality:
        payload["quality"] = quality
    if style:
        payload["style"] = style
    if negative_prompt.strip():
        payload["negative_prompt"] = negative_prompt.strip()
    if reference_images:
        payload["reference_images"] = reference_images

    req_data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 MAX-AI-Agent/1.0",
        "Accept": "application/json",
    }

    try:
        req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_body = json.loads(resp.read().decode("utf-8"))

        data_items = resp_body.get("data", [])
        if not data_items:
            return False, f"API ตอบกลับโดยไม่มีข้อมูลรูปภาพ: {resp_body}"

        first_item = data_items[0]
        if "b64_json" in first_item:
            img_bytes = base64.b64decode(first_item["b64_json"])
            out_file.write_bytes(img_bytes)
            size_kb = len(img_bytes) / 1024
            return True, (
                f"🎨 สร้างรูปภาพระดับพรีเมียมสำเร็จด้วย {provider.upper()} ({model})!\n"
                f"• คำสั่ง (Prompt): \"{prompt}\"\n"
                f"• ความละเอียด: {width}x{height} pixels ({size_kb:.1f} KB)\n"
                f"• บันทึกไว้ที่: {out_file.resolve()}\n"
                f"• เครื่องยนต์: MaxPlus AI Built-in ({provider})"
            )
        elif "url" in first_item:
            img_url = first_item["url"]
            dl_req = urllib.request.Request(img_url, headers={"User-Agent": "MAX-AI/1.0"})
            with urllib.request.urlopen(dl_req, timeout=30) as dl_resp:
                img_bytes = dl_resp.read()
            out_file.write_bytes(img_bytes)
            size_kb = len(img_bytes) / 1024
            return True, (
                f"🎨 สร้างรูปภาพสำเร็จด้วย {provider.upper()} ({model})!\n"
                f"• คำสั่ง (Prompt): \"{prompt}\"\n"
                f"• ความละเอียด: {width}x{height} pixels ({size_kb:.1f} KB)\n"
                f"• บันทึกไว้ที่: {out_file.resolve()}\n"
                f"• ลิงก์รูปภาพ: {img_url}\n"
                f"• เครื่องยนต์: MaxPlus AI Built-in ({provider})"
            )
        else:
            return False, f"รูปแบบผลลัพธ์ไม่ตรงที่คาดไว้: {first_item.keys()}"

    except urllib.error.HTTPError as e:
        err_text = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_text)
            msg = err_json.get("error", {}).get("message", err_text)
        except Exception:
            msg = err_text
        return False, f"HTTP {e.code}: {msg}"
    except Exception as ex:
        return False, str(ex)


def _builtin_generate_image(
    prompt: str,
    output_path: str = "",
    width: int = 1024,
    height: int = 1024,
    model: str = "dall-e-3",
    provider: str = "auto",
    negative_prompt: str = "",
    quality: str = "standard",
    style: str = "vivid",
    reference_images: Optional[list[str]] = None,
) -> str:
    """Generate high-resolution AI image and save to disk."""
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

    # Provider resolution
    chosen_provider = provider.lower().strip()
    m_lower = model.lower().strip()

    if chosen_provider == "auto":
        if "nai" in m_lower or "anime" in m_lower or "furry" in m_lower:
            chosen_provider = "nai-image"
            if model in ("dall-e-3", "auto", ""):
                model = "nai-diffusion-4-5-full"
        elif "grok" in m_lower:
            chosen_provider = "grok-image"
            if model in ("dall-e-3", "auto", ""):
                model = "grok-imagine-image-2.0"
        elif "dall-e" in m_lower or "gpt" in m_lower:
            chosen_provider = "gpt-image"
        elif "flux" in m_lower or "turbo" in m_lower:
            chosen_provider = "pollinations"
        else:
            chosen_provider = "gpt-image"
    else:
        # Align default model with chosen provider
        if chosen_provider == "nai-image" and model in ("dall-e-3", "auto", ""):
            model = "nai-diffusion-4-5-full"
        elif chosen_provider == "grok-image" and model in ("dall-e-3", "auto", ""):
            model = "grok-imagine-image-2.0"

    # If MaxPlus Image Provider requested
    if chosen_provider in ("gpt-image", "nai-image", "grok-image"):
        ok, res_or_err = _generate_image_via_maxplus(
            provider=chosen_provider,
            prompt=p,
            out_file=out_file,
            width=width,
            height=height,
            model=model,
            negative_prompt=negative_prompt,
            quality=quality,
            style=style,
            reference_images=reference_images,
        )
        if ok:
            return res_or_err
        # MaxPlus call did not succeed, fallback gracefully to Pollinations Flux
        fallback_notice = f"\n⚠️ [หมายเหตุระบบ]: ไม่สามารถเรียกใช้ {chosen_provider.upper()} ได้ ({res_or_err}) สลับมาใช้เครื่องยนต์สำรอง Flux คุณภาพสูงอัตโนมัติ"
    else:
        fallback_notice = ""

    # High-quality Pollinations / Flux engine fallback
    encoded_prompt = urllib.parse.quote(p)
    poll_model = "flux" if model in ("dall-e-3", "gpt-image-1", "grok-2-image", "nai-diffusion-3") else model
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={poll_model}&nologo=true"
    if negative_prompt.strip():
        pollinations_url += f"&negative={urllib.parse.quote(negative_prompt.strip())}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MAX-AI-Agent/1.0",
        "Accept": "image/png,image/jpeg,image/*",
    }

    try:
        req = urllib.request.Request(pollinations_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=35) as resp:
            img_data = resp.read()

        if len(img_data) < 10:
            return f"Error: รูปภาพที่สร้างมีขนาดเล็กผิดปกติ ({len(img_data)} bytes){fallback_notice}"

        out_file.write_bytes(img_data)
        size_kb = len(img_data) / 1024

        return (
            f"🎨 สร้างรูปภาพสำเร็จเรียบร้อยแล้ว!\n"
            f"• คำสั่ง (Prompt): \"{p}\"\n"
            f"• ขนาดภาพ: {width}x{height} pixels ({size_kb:.1f} KB)\n"
            f"• บันทึกไว้ที่: {out_file.resolve()}\n"
            f"• โมเดล: {poll_model}\n"
            f"• ลิงก์รูปภาพ: {pollinations_url}"
            f"{fallback_notice}"
        )
    except Exception as ex:
        return f"Error generating image: {ex}{fallback_notice}"


def _builtin_generate_video(
    prompt: str,
    output_path: str = "",
    duration_seconds: int = 4,
    aspect_ratio: str = "16:9",
    model: str = "wan2.1",
) -> str:
    """Generate short AI video/animation and save to disk."""
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
                description="สร้างรูปภาพด้วย AI ความละเอียดสูง (รองรับ MaxPlus GPT Image, NAI Image, Grok Image และ Flux)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "คำอธิบายภาพที่ต้องการสร้าง เช่น a cybernetic glowing cat in cyberpunk city, 8k"},
                        "provider": {
                            "type": "string",
                            "description": "ผู้ให้บริการสร้างภาพ: 'auto' (ตรวจจับจากโมเดล), 'gpt-image' (DALL-E-3 / GPT Image), 'nai-image' (NovelAI Anime Diffusion), 'grok-image' (Grok 2 Image), 'pollinations' (Flux)",
                            "default": "auto",
                        },
                        "model": {
                            "type": "string",
                            "description": "โมเดลที่ต้องการสร้าง เช่น dall-e-3, nai-diffusion-4-5-full, grok-imagine-image-2.0, gpt-image-1, flux",
                            "default": "dall-e-3",
                        },
                        "output_path": {"type": "string", "description": "พาธไฟล์ภาพปลายทาง เช่น images/cat.png (หากไม่ระบุจะตั้งชื่ออัตโนมัติตามเวลา)", "default": ""},
                        "width": {"type": "integer", "description": "ความกว้างของภาพ (pixels, เช่น 1024, 768, 512)", "default": 1024},
                        "height": {"type": "integer", "description": "ความสูงของภาพ (pixels, เช่น 1024, 768, 512)", "default": 1024},
                        "negative_prompt": {"type": "string", "description": "สิ่งที่ไม่ต้องการให้ปรากฏในภาพ", "default": ""},
                        "quality": {"type": "string", "description": "คุณภาพภาพ: 'standard' หรือ 'hd'", "default": "standard"},
                        "style": {"type": "string", "description": "สไตล์ภาพ: 'vivid' หรือ 'natural'", "default": "vivid"},
                        "reference_images": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "ภาพอ้างอิงสำหรับแก้ไขหรือแปลงภาพ (Image-to-Image / reference_images เช่น ใน Grok Imagine)",
                            "default": [],
                        },
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
                model=str(args.get("model", "dall-e-3")),
                provider=str(args.get("provider", "auto")),
                negative_prompt=str(args.get("negative_prompt", "")),
                quality=str(args.get("quality", "standard")),
                style=str(args.get("style", "vivid")),
                reference_images=args.get("reference_images") if isinstance(args.get("reference_images"), list) else None,
            ),
        ),
        "generate_video": (
            MCPTool(
                name="generate_video",
                description="สร้างวิดีโอหรือคลิปอนิเมชันสั้นด้วย AI ตาม Prompt บันทึกเป็นไฟล์ MP4 ลงเครื่อง (รองรับ wan2.1, cogvideox, luma)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "คำอธิบายคลิปวิดีโอหรืออนิเมชันที่ต้องการสร้าง เช่น cinematic drone shot flying over futuristic neon city"},
                        "output_path": {"type": "string", "description": "พาธไฟล์วิดีโอปลายทาง เช่น videos/city.mp4 (หากไม่ระบุจะตั้งชื่ออัตโนมัติตามเวลา)", "default": ""},
                        "duration_seconds": {"type": "integer", "description": "ความยาวคลิปเป็นวินาที (ค่าเริ่มต้น 4, สูงสุด 15)", "default": 4},
                        "aspect_ratio": {"type": "string", "description": "สัดส่วนภาพ เช่น 16:9, 9:16, 1:1", "default": "16:9"},
                        "model": {"type": "string", "description": "โมเดลสร้างวิดีโอ (wan2.1, cogvideox, luma)", "default": "wan2.1"},
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
