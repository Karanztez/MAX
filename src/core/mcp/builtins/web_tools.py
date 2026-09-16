"""Web search, scraping, HTTP request, and domain permission security guard tools."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Optional

try:
    from ..types import MCPTool
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]

_web_permission_handler: Optional[Callable[[str, str, str], bool]] = None


def set_web_permission_handler(handler: Optional[Callable[[str, str, str], bool]]) -> None:
    """Register a callback for web access permission checks."""
    global _web_permission_handler
    _web_permission_handler = handler


def _get_settings_store() -> Any:
    try:
        from core.settings_store import SettingsStore
        return SettingsStore()
    except (ImportError, ModuleNotFoundError):
        pass

    try:
        from ...settings_store import SettingsStore
        return SettingsStore()
    except (ImportError, ModuleNotFoundError):
        return None


def check_web_permission(url: str, action: str = "read") -> tuple[bool, str]:
    """Check whether access to a given URL/domain is permitted by security settings or user."""
    try:
        store = _get_settings_store()
        if not store:
            return True, "No settings store available"

        domain = urllib.parse.urlparse(url).netloc.split(":")[0].lower()
        if not domain:
            domain = url.split("/")[0].split(":")[0].lower()

        settings = store.load_web_security_settings()
        allowed_list = [d.lower() for d in settings.get("allowed_domains", [])]
        denied_list = [d.lower() for d in settings.get("denied_domains", [])]
        policy = settings.get("policy", "ask")

        # 1. Denylist check
        if domain in denied_list:
            return False, f"โดเมน '{domain}' อยู่ในรายการที่ถูกบล็อก (Denylist)"

        # 2. Allowlist check
        if domain in allowed_list or any(domain == a or domain.endswith("." + a) for a in allowed_list):
            return True, f"โดเมน '{domain}' อยู่ในรายการที่อนุญาต (Whitelist)"

        # 3. Policy check
        if policy == "deny_all":
            return False, "นโยบายความปลอดภัยบล็อกการเข้าถึงเว็บไซต์ทั้งหมด (deny_all)"
        elif policy == "allow_all":
            return True, "นโยบายความปลอดภัยอนุญาตเว็บไซต์ทั้งหมด (allow_all)"

        # 4. Ask user / interactive handler
        if _web_permission_handler is not None:
            allowed = _web_permission_handler(domain, url, action)
            if allowed:
                return True, f"ผู้ใช้อนุญาตให้เข้าถึงโดเมน '{domain}'"
            else:
                return False, f"ผู้ใช้ไม่อนุญาตให้เข้าถึงโดเมน '{domain}'"

        return False, f"ผู้ใช้ไม่อนุญาตให้เข้าถึงโดเมน '{domain}'"
    except Exception as ex:
        return True, f"Security check skipped: {ex}"


def _builtin_search_web(query: str, count: int = 5) -> str:
    """Search DuckDuckGo HTML without external dependencies."""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        results: list[dict[str, str]] = []
        links = re.findall(r'<a[^>]+class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
        snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
        titles = re.findall(r'<a[^>]+class="result__title"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)

        for i in range(min(len(titles), count)):
            t = re.sub(r"<[^>]+>", "", titles[i]).strip()
            s = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
            raw_link = links[i][0] if i < len(links) else ""
            if "uddg=" in raw_link:
                m = re.search(r"uddg=([^&]+)", raw_link)
                if m:
                    raw_link = urllib.parse.unquote(m.group(1))
            results.append({"title": t, "snippet": s, "url": raw_link})

        if not results:
            clean = re.sub(r"<[^>]+>", " ", html)
            clean = re.sub(r"\s+", " ", clean).strip()
            return f"Search results for '{query}':\n" + clean[:2000]

        out = [f"Search Results for: '{query}'\n"]
        for idx, r in enumerate(results, 1):
            out.append(f"{idx}. {r['title']}\n   URL: {r['url']}\n   Summary: {r['snippet']}\n")
        return "\n".join(out)
    except Exception as ex:
        return f"Error searching web for '{query}': {ex}"


def _builtin_fetch_web(url: str, max_length: int = 8000) -> str:
    """Fetch URL and convert HTML to readable plain text."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    ok, reason = check_web_permission(url, action="read")
    if not ok:
        return f"🚫 ไม่อนุญาตให้เข้าถึงเว็บไซต์: {reason} (URL: {url})"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MAX-AI-Agent/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw_bytes = resp.read()

        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].split(";")[0].strip()

        html = raw_bytes.decode(charset, errors="replace")

        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        text = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"\n\n# \1\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n• \1", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        if len(text) > max_length:
            text = text[:max_length] + f"\n\n... [Truncated, total length was {len(text)} chars]"

        return f"Content from {url}:\n\n{text}"
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason} while fetching {url}"
    except Exception as ex:
        return f"Error fetching URL '{url}': {ex}"


def _builtin_http_request(url: str, method: str = "GET", headers: Optional[dict[str, str]] = None,
                          body: Optional[str] = None, timeout_seconds: int = 15) -> str:
    """Execute generic HTTP request."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    ok, reason = check_web_permission(url, action="http_request")
    if not ok:
        return f"🚫 ไม่อนุญาตให้เชื่อมต่อ HTTP: {reason} (URL: {url})"

    req_headers = {"User-Agent": "MAX-AI-Agent/1.0"}
    if headers:
        req_headers.update(headers)

    data = body.encode("utf-8") if body else None
    try:
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            status = resp.status
            resp_headers = dict(resp.headers)
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace")

        return f"Status: {status}\nHeaders: {json.dumps(resp_headers, indent=2)}\n\nBody:\n{text[:4000]}"
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        return f"HTTP Error {e.code}: {e.reason}\nBody: {raw[:2000]}"
    except Exception as ex:
        return f"Error executing HTTP {method} to '{url}': {ex}"


def get_web_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return dictionary of web tools."""
    return {
        "search_web": (
            MCPTool(
                name="search_web",
                description="ค้นหาข้อมูลบนอินเทอร์เน็ตผ่าน Search Engine (คืนค่าหัวข้อ ลิงก์ และคำอธิบายย่อ)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "คำค้นหาหรือสิ่งที่ต้องการสืบค้น"},
                        "count": {"type": "integer", "description": "จำนวนผลลัพธ์ที่ต้องการ (ค่าเริ่มต้น 5, สูงสุด 10)", "default": 5},
                    },
                    "required": ["query"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_search_web(str(args.get("query", "")), count=int(args.get("count", 5))),
        ),
        "fetch_web_content": (
            MCPTool(
                name="fetch_web_content",
                description="เปิดอ่านเนื้อหาหน้าเว็บหรือดึงข้อมูลจาก URL (แปลง HTML เป็นข้อความสะอาดที่อ่านง่าย)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL ของหน้าเว็บที่ต้องการอ่าน เช่น https://example.com"},
                        "max_length": {"type": "integer", "description": "ความยาวตัวอักษรสูงสุดที่ต้องการดึง (ค่าเริ่มต้น 8000)", "default": 8000},
                    },
                    "required": ["url"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_fetch_web(str(args.get("url", "")), max_length=int(args.get("max_length", 8000))),
        ),
        "http_request": (
            MCPTool(
                name="http_request",
                description="ส่งคำขอ HTTP (GET, POST, PUT, DELETE) ไปยัง REST API ภายนอก",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL ปลายทาง"},
                        "method": {"type": "string", "description": "HTTP Method (GET, POST, PUT, DELETE)", "default": "GET"},
                        "headers": {"type": "object", "description": "HTTP Headers ในรูปแบบ key-value", "additionalProperties": True, "properties": {}, "default": {}},
                        "body": {"type": "string", "description": "เนื้อหา JSON หรือ Payload ในคำขอ", "default": ""},
                        "timeout_seconds": {"type": "integer", "description": "ระยะเวลารอคอยสูงสุดเป็นวินาที", "default": 15},
                    },
                    "required": ["url"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_http_request(
                str(args.get("url", "")),
                method=str(args.get("method", "GET")),
                headers=args.get("headers") if isinstance(args.get("headers"), dict) else None,
                body=str(args.get("body", "")) if args.get("body") else None,
                timeout_seconds=int(args.get("timeout_seconds", 15)),
            ),
        ),
    }
