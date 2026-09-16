"""
MAX AI — Multi-Provider AI Agent & Autonomous Tool Runner SDK.

Quick Start:
    import max_ai

    # Simple ask
    print(max_ai.ask("สวัสดีครับ"))

    # Agent with session memory
    agent = max_ai.Agent(model="gemini-2.5-flash")
    session = agent.create_session("my-chat")
    res = session.send("ช่วยแนะนำไอเดียสร้างเกม")
    print(res.text)

    # Multi-Agent Pipeline
    team = max_ai.Team()
    result = team.run("สร้าง Discord bot")
"""

from __future__ import annotations

from typing import Any, Optional

from max_ai.agent import MaxAgent
from max_ai.session import MaxSession, Response
from max_ai.team import MaxTeam, TeamMember
from max_ai.async_api import ask_async, stream_async
from core.ai_client import AIClient

# Convenient short aliases
Agent = MaxAgent
Session = MaxSession
Team = MaxTeam

__version__ = "1.0.4"


def ask(
    prompt: str,
    model: str = "gemini-2.5-flash",
    api_key: str = "",
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Convenience function to ask a single question synchronously."""
    agent = MaxAgent(
        model=model,
        api_key=api_key or None,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return agent.ask(prompt)


def stream(
    prompt: str,
    model: str = "gemini-2.5-flash",
    api_key: str = "",
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    """Convenience function to stream response tokens synchronously."""
    agent = MaxAgent(
        model=model,
        api_key=api_key or None,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return agent.stream(prompt)


def chat(
    message: str,
    history: Optional[list[dict[str, Any]]] = None,
    model: str = "gemini-2.5-flash",
    api_key: str = "",
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> list[dict[str, Any]]:
    """Convenience function for multi-turn chat updating history."""
    agent = MaxAgent(
        model=model,
        api_key=api_key or None,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return agent.chat(message, history=history)


__all__ = [
    "Agent",
    "MaxAgent",
    "Session",
    "MaxSession",
    "Team",
    "MaxTeam",
    "TeamMember",
    "Response",
    "AIClient",
    "ask",
    "ask_async",
    "stream",
    "stream_async",
    "chat",
    "__version__",
]
