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


def _windows_apis() -> tuple[object, object]:
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
    if os.name != "nt":
        raise RuntimeError("การบันทึก API key แบบเข้ารหัสรองรับ Windows เท่านั้น")
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


def _unprotect(token: str) -> str:
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
        appdata = Path(os.environ.get("APPDATA", Path.home()))
        self.path = path or appdata / "MaxPlusAI" / "settings.json"

    def has_saved_key(self) -> bool:
        return self.path.exists()

    def load_provider_settings(
        self, defaults: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str]:
        """Load encrypted provider profiles, with migration from version 1."""
        from copy import deepcopy
        try:
            from src.core.provider_profiles import normalize_profiles
        except ImportError:
            from provider_profiles import normalize_profiles

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

