"""
max_ai.async_api — Asynchronous helpers for asyncio applications (FastAPI, Discord, Aiohttp).
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Optional, Union

try:
    from .agent import MaxAgent
except (ImportError, ModuleNotFoundError):
    from max_ai.agent import MaxAgent  # type: ignore[no-redef]


async def ask_async(
    prompt: Union[str, list[dict[str, Any]]],
    model: str = "gemini-2.5-flash",
    api_key: Optional[str] = None,
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Async single-turn question."""
    agent = MaxAgent(
        model=model,
        api_key=api_key,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return await agent.ask_async(prompt)


async def stream_async(
    prompt: Union[str, list[dict[str, Any]]],
    model: str = "gemini-2.5-flash",
    api_key: Optional[str] = None,
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """Async token streaming iterator."""
    agent = MaxAgent(
        model=model,
        api_key=api_key,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    async for chunk in agent.stream_async(prompt):
        yield chunk
