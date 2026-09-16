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

CLAUDE_NATIVE_MODELS = [
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

CLAUDE_CURSOR_MODELS = [
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

CLAUDE_ANTIGRAVITY_MODELS = [
    "claude-haiku-4-5-20251001",
    "claude-opus-4-5-20251101",
    "claude-opus-4-6",
    "claude-opus-4-6-thinking",
    "claude-sonnet-4-6",
]

CLAUDE_MODELS = CLAUDE_NATIVE_MODELS

CHINESE_SPECIALS_MODELS = [
    "deepseek-v4.1-flash",
    "glm-5.3",
    "glm-5.3-flash",
    "glm-5.2",
    "glm-5.1",
    "kimi-k3",
    "kimi-k2.7-code",
    "kimi-k2.6",
    "qwen3.8-max",
    "qwen3.8-flash",
    "qwen3.7-max",
    "deepseek-v4-pro-0813",
    "deepseek-v4-flash-0731",
    "deepseek-v4-flash-vision-exp",
    "minimax-m3",
    "minimax-m2.7-highspeed",
    "minimax-m2.7",
    "mimo-v2.5-pro",
    "mimo-v2.5",
    "hy4-preview",
    "hy3",
]

CHINA_TOWN_MODELS = [
    "deepseek-v4.1-flash",
    "glm-5.3-flash",
    "deepseek-v4-pro-0813",
    "qwen-3.8-max",
    "deepseek-v4-flash",
    "glm-5.3",
    "kimi-k3",
]

GROK_MODELS = [
    "grok-4.6",
    "grok-4.5",
]

GPT_PRO_SUPREME_MODELS = [
    "gpt-6-astra",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
]

OPENAI_MODELS = [
    "gpt-6-astra",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
]

GPT_IMAGE_MODELS = [
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "dall-e-3",
]

NAI_IMAGE_MODELS = [
    "nai-diffusion-4-5-full",
    "nai-diffusion-3",
    "nai-diffusion-furry-3",
    "nai-diffusion",
    "nai-diffusion-anime",
]

GROK_IMAGE_MODELS = [
    "grok-imagine-image-2.0",
    "grok-2-image",
    "grok-image-1",
    "grok-image",
]

NATIVE_POOL_MODELS = [
    "haiku",
    "sonnet-4-5",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
]


def default_profiles() -> list[dict[str, Any]]:
    return [
        {
            "id": "maxplus-native",
            "name": "Native (Claude + GPT)",
            "base_url": "https://api.maxplus-ai.cc/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(NATIVE_POOL_MODELS),
            "model": "gpt-5.6-sol",
        },
        {
            "id": "maxplus-claude-native",
            "name": "Claude Native",
            "base_url": "https://api.maxplus-ai.cc/claude-native/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(CLAUDE_NATIVE_MODELS),
            "model": "claude-sonnet-4-6",
        },
        {
            "id": "maxplus-chinese-specials",
            "name": "Chinese Specials",
            "base_url": "https://api.maxplus-ai.cc/chinese-specials/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(CHINESE_SPECIALS_MODELS),
            "model": CHINESE_SPECIALS_MODELS[0],
        },
        {
            "id": "maxplus-china-town",
            "name": "China Town (จีน)",
            "base_url": "https://api.maxplus-ai.cc/china-town/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(CHINA_TOWN_MODELS),
            "model": CHINA_TOWN_MODELS[0],
        },
        {
            "id": "maxplus-grok-heavy",
            "name": "Grok Heavy",
            "base_url": "https://api.maxplus-ai.cc/grok-heavy-claude-code/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(GROK_MODELS),
            "model": GROK_MODELS[0],
        },
        {
            "id": "maxplus-claude-cursor",
            "name": "Claude Cursor Full",
            "base_url": "https://api.maxplus-ai.cc/claude-cursor-full/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(CLAUDE_CURSOR_MODELS),
            "model": "claude-sonnet-4-6",
        },
        {
            "id": "maxplus-claude-antigravity",
            "name": "Claude Antigravity Full",
            "base_url": "https://api.maxplus-ai.cc/claude-antigravity-full/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(CLAUDE_ANTIGRAVITY_MODELS),
            "model": "claude-sonnet-4-6",
        },
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
            "id": "maxplus-gpt-pro-supreme",
            "name": "GPT PRO Supreme",
            "base_url": "https://api.maxplus-ai.cc/gpt-pro-supreme/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(GPT_PRO_SUPREME_MODELS),
            "model": GPT_PRO_SUPREME_MODELS[0],
        },
        {
            "id": "maxplus-gpt-image",
            "name": "GPT Image (สร้างภาพ)",
            "base_url": "https://api.maxplus-ai.cc/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(GPT_IMAGE_MODELS),
            "model": GPT_IMAGE_MODELS[0],
        },
        {
            "id": "maxplus-nai-image",
            "name": "NAI Image (สร้างภาพ)",
            "base_url": "https://api.maxplus-ai.cc/nai-image/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(NAI_IMAGE_MODELS),
            "model": NAI_IMAGE_MODELS[0],
        },
        {
            "id": "maxplus-grok-image",
            "name": "Grok Image (สร้างภาพ)",
            "base_url": "https://api.maxplus-ai.cc/grok-image/v1",
            "api_mode": "chat_completions",
            "api_key": "",
            "models": list(GROK_IMAGE_MODELS),
            "model": GROK_IMAGE_MODELS[0],
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
