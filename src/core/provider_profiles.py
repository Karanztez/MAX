"""Provider profile presets and normalization for MaxPlus AI."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4


GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite",
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

CLAUDE_MODELS = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "claude-sonnet-5",
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-opus-5",
    "claude-fable-5",
    "claude-fable-5-1",
]

OPENAI_MODELS = [
    "gpt-6-astra",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.3-codex",
]


def default_profiles() -> list[dict[str, Any]]:
    return [
        {
            "id": "maxplus-gemini",
            "name": "MaxPlus Gemini",
            "base_url": "https://api.maxplus-ai.cc/gemini-full/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(GEMINI_MODELS),
            "model": GEMINI_MODELS[0],
        },
        {
            "id": "maxplus-claude",
            "name": "MaxPlus Claude",
            "base_url": "https://api.maxplus-ai.cc/claude-cursor-full/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(CLAUDE_MODELS),
            "model": "claude-sonnet-4-6",
        },
        {
            "id": "openai",
            "name": "OpenAI GPT / Codex",
            "base_url": "https://api.openai.com/v1",
            "api_mode": "responses",
            "api_key": "",
            "models": list(OPENAI_MODELS),
            "model": OPENAI_MODELS[0],
        },
    ]


def normalize_profile(value: dict[str, Any]) -> dict[str, Any]:
    """Return a safe, complete profile dictionary from persisted/UI data."""
    models_value = value.get("models", [])
    if isinstance(models_value, str):
        models = [part.strip() for part in models_value.replace(",", "\n").splitlines()
                  if part.strip()]
    else:
        models = [str(item).strip() for item in models_value if str(item).strip()]
    model = str(value.get("model", "")).strip()
    if model and model not in models:
        models.insert(0, model)
    if not models:
        models = ["model-name"]
    return {
        "id": str(value.get("id") or uuid4().hex),
        "name": str(value.get("name") or "Custom API").strip() or "Custom API",
        "base_url": str(value.get("base_url") or "").strip().rstrip("/"),
        "api_mode": "responses" if value.get("api_mode") == "responses" else "chat_completions",
        "api_key": str(value.get("api_key") or "").strip(),
        "models": models,
        "model": model or models[0],
    }


def normalize_profiles(values: object) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return default_profiles()
    profiles = [normalize_profile(item) for item in values if isinstance(item, dict)]
    profiles = profiles or deepcopy(default_profiles())
    used: set[str] = set()
    for profile in profiles:
        base = profile["name"]
        name, suffix = base, 2
        while name.casefold() in used:
            name = f"{base} ({suffix})"
            suffix += 1
        profile["name"] = name
        used.add(name.casefold())
    return profiles


def new_custom_profile(number: int = 1) -> dict[str, Any]:
    return normalize_profile({
        "name": f"Custom API {number}",
        "base_url": "https://api.example.com/v1",
        "api_mode": "chat_completions",
        "models": ["model-name"],
    })
