"""Windows DPAPI-backed local settings for MaxPlus AI."""

import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
from typing import Any, Optional


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = ctypes.create_string_buffer(data)
    value = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    return value, buffer


def _windows_apis() -> tuple[Any, Any]:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    blob_ptr = ctypes.POINTER(_DataBlob)
    crypt32.CryptProtectData.argtypes = (
        blob_ptr, wintypes.LPCWSTR, blob_ptr, ctypes.c_void_p,
        ctypes.c_void_p, wintypes.DWORD, blob_ptr,
    )
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = (
        blob_ptr, ctypes.c_void_p, blob_ptr, ctypes.c_void_p,
        ctypes.c_void_p, wintypes.DWORD, blob_ptr,
    )
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
    kernel32.LocalFree.restype = ctypes.c_void_p
    return crypt32, kernel32


def _protect(value: str) -> str:
    if os.name == "nt":
        source, keepalive = _blob(value.encode("utf-8"))
        output = _DataBlob()
        crypt32, kernel32 = _windows_apis()
        if not crypt32.CryptProtectData(ctypes.byref(source), "MaxPlus AI", None, None, None,
                                        0x1, ctypes.byref(output)):
            raise ctypes.WinError()
        try:
            encrypted = ctypes.string_at(output.pbData, output.cbData)
            return base64.b64encode(encrypted).decode("ascii")
        finally:
            kernel32.LocalFree(output.pbData)
            del keepalive
    else:
        # Non-Windows POSIX / Linux / Android Termux safe token format
        token = base64.b64encode(value.encode("utf-8")).decode("ascii")
        return f"posix:{token}"


def _unprotect(token: str) -> str:
    if token.startswith("posix:"):
        return base64.b64decode(token[6:].encode("ascii")).decode("utf-8")
    if os.name != "nt":
        try:
            return base64.b64decode(token.encode("ascii")).decode("utf-8")
        except Exception:
            return token
    encrypted = base64.b64decode(token)
    source, keepalive = _blob(encrypted)
    output = _DataBlob()
    crypt32, kernel32 = _windows_apis()
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None,
                                      0x1, ctypes.byref(output)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData).decode("utf-8")
    finally:
        kernel32.LocalFree(output.pbData)
        del keepalive


class SettingsStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        if path:
            self.path = path
        else:
            if os.name == "nt":
                base = Path(os.environ.get("APPDATA", Path.home()))
            else:
                base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            self.path = base / "MaxPlusAI" / "settings.json"

    def has_saved_key(self) -> bool:
        return self.path.exists()

    def load_provider_settings(
        self, defaults: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str]:
        """Load encrypted provider profiles, with migration from version 1."""
        from copy import deepcopy
        try:
            from .provider_profiles import normalize_profiles
        except (ImportError, ValueError):
            try:
                from core.provider_profiles import normalize_profiles
            except ImportError:
                from src.core.provider_profiles import normalize_profiles  # type: ignore[no-redef]

        profiles = deepcopy(defaults)
        selected_id = profiles[0]["id"] if profiles else ""
        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if payload.get("version") == 2 and payload.get("settings_dpapi"):
                    saved = json.loads(_unprotect(payload["settings_dpapi"]))
                    saved_profiles = normalize_profiles(saved.get("profiles"))
                    selected_id = str(saved.get("selected_profile_id") or (saved_profiles[0]["id"] if saved_profiles else ""))

                    # Merge missing default presets so new official pools (Grok, Chinese Specials, etc.) appear automatically
                    existing_ids = {p.get("id") for p in saved_profiles}
                    existing_urls = {str(p.get("base_url")).strip().rstrip("/").casefold() for p in saved_profiles}
                    for default_p in defaults:
                        d_url = str(default_p.get("base_url")).strip().rstrip("/").casefold()
                        if default_p.get("id") not in existing_ids and d_url not in existing_urls:
                            saved_profiles.append(deepcopy(default_p))
                    profiles = saved_profiles
                elif payload.get("api_key_dpapi") and profiles:
                    profiles[0]["api_key"] = _unprotect(payload["api_key_dpapi"]).strip()
            except Exception:
                pass
        env_key = os.environ.get("MAXPLUS_API_KEY", "").strip()
        if env_key and profiles:
            target = next((p for p in profiles if p.get("id") == "maxplus-gemini"), profiles[0])
            target["api_key"] = env_key
        if not any(p.get("id") == selected_id for p in profiles) and profiles:
            selected_id = profiles[0]["id"]
        return profiles, selected_id

    def save_provider_settings(
        self, profiles: list[dict[str, Any]], selected_profile_id: str, remember: bool
    ) -> None:
        """Encrypt all profile details (including every API key) as one DPAPI blob."""
        if not remember:
            if self.path.exists():
                self.path.unlink()
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        secret = json.dumps({
            "profiles": profiles,
            "selected_profile_id": selected_profile_id,
        }, ensure_ascii=False)
        payload = {"version": 2, "settings_dpapi": _protect(secret)}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_api_key(self) -> str:
        env_key = os.environ.get("MAXPLUS_API_KEY", "").strip()
        if env_key:
            return env_key
        if not self.path.exists():
            return ""
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("version") == 2 and payload.get("settings_dpapi"):
                saved = json.loads(_unprotect(payload["settings_dpapi"]))
                profiles = saved.get("profiles") or []
                return str(profiles[0].get("api_key", "")).strip() if profiles else ""
            return _unprotect(payload["api_key_dpapi"]).strip()
        except Exception:
            return ""

    def save_api_key(self, api_key: str, remember: bool) -> None:
        api_key = api_key.strip()
        if not remember or not api_key:
            if self.path.exists():
                self.path.unlink()
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "api_key_dpapi": _protect(api_key)}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_skipped_version(self) -> str:
        """Load the version string that the user chose to skip."""
        if not self.path.exists():
            return ""
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return str(payload.get("skipped_version", "")).strip()
        except Exception:
            return ""

    def save_skipped_version(self, version: str) -> None:
        """Save skipped version string to settings file without altering DPAPI credentials."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {}
        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
        payload["skipped_version"] = version.strip()
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    DEFAULT_TRUSTED_DOMAINS = [
        "github.com",
        "api.github.com",
        "raw.githubusercontent.com",
        "duckduckgo.com",
        "html.duckduckgo.com",
        "pollinations.ai",
        "image.pollinations.ai",
        "video.pollinations.ai",
    ]

    def load_web_security_settings(self) -> dict[str, Any]:
        """Load web security preferences (policy, allowed_domains, denied_domains)."""
        defaults = {
            "policy": "ask",  # "ask", "allow_all", "deny_all"
            "allowed_domains": list(self.DEFAULT_TRUSTED_DOMAINS),
            "denied_domains": [],
        }
        if not self.path.exists():
            return defaults
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            sec = payload.get("web_security", {})
            if isinstance(sec, dict):
                policy = sec.get("policy", "ask")
                if policy not in {"ask", "allow_all", "deny_all"}:
                    policy = "ask"
                raw_allowed = sec.get("allowed_domains", [])
                allowed = list(set(self.DEFAULT_TRUSTED_DOMAINS + [d.strip().lower() for d in raw_allowed if isinstance(d, str) and d.strip()]))
                raw_denied = sec.get("denied_domains", [])
                denied = [d.strip().lower() for d in raw_denied if isinstance(d, str) and d.strip()]
                return {
                    "policy": policy,
                    "allowed_domains": allowed,
                    "denied_domains": denied,
                }
            return defaults
        except Exception:
            return defaults

    def save_web_security_settings(
        self,
        allowed_domains: Optional[list[str]] = None,
        denied_domains: Optional[list[str]] = None,
        policy: Optional[str] = None,
    ) -> None:
        """Persist web security preferences without altering DPAPI credentials."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {}
        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}

        current = payload.get("web_security", {})
        if not isinstance(current, dict):
            current = {}

        if policy is not None:
            current["policy"] = policy if policy in {"ask", "allow_all", "deny_all"} else "ask"
        if allowed_domains is not None:
            current["allowed_domains"] = sorted(list({d.strip().lower() for d in allowed_domains if d.strip()}))
        if denied_domains is not None:
            current["denied_domains"] = sorted(list({d.strip().lower() for d in denied_domains if d.strip()}))

        payload["web_security"] = current
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_allowed_domain(self, domain: str) -> None:
        """Add a domain to the user's permanent allowlist."""
        d = domain.strip().lower()
        if not d:
            return
        settings = self.load_web_security_settings()
        allowed = set(settings.get("allowed_domains", []))
        allowed.add(d)
        denied = [x for x in settings.get("denied_domains", []) if x != d]
        self.save_web_security_settings(allowed_domains=list(allowed), denied_domains=denied)

    def add_denied_domain(self, domain: str) -> None:
        """Add a domain to the user's permanent denylist."""
        d = domain.strip().lower()
        if not d:
            return
        settings = self.load_web_security_settings()
        denied = set(settings.get("denied_domains", []))
        denied.add(d)
        allowed = [x for x in settings.get("allowed_domains", []) if x != d and x not in self.DEFAULT_TRUSTED_DOMAINS]
        self.save_web_security_settings(allowed_domains=allowed, denied_domains=list(denied))


