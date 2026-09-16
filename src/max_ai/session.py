"""
max_ai.session — Conversation Session & Memory Manager.
Maintains stateful multi-turn conversation history per user, channel, or thread.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable, Iterator, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from max_ai.agent import MaxAgent


class Response:
    """Represents an AI response with text content and metadata."""

    def __init__(self, text: str, raw_response: Optional[dict[str, Any]] = None, session_id: Optional[str] = None):
        self.text = text
        self.raw_response = raw_response or {}
        self.session_id = session_id

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f"Response(text={self.text[:40]!r}...)"


class MaxSession:
    """
    Manages an isolated conversation history state.
    Ideal for Discord bot channels, user DMs, Telegram chats, and web sessions.
    """

    def __init__(
        self,
        agent: "MaxAgent",
        session_id: str = "default",
        system_prompt: Optional[str] = None,
        max_history: int = 40,
    ):
        self.agent = agent
        self.session_id = session_id
        self.system_prompt = system_prompt
        self.max_history = max_history
        self._history: list[dict[str, Any]] = []

    @property
    def history(self) -> list[dict[str, Any]]:
        """Return a copy of the current conversation history."""
        return list(self._history)

    def add_message(self, role: str, content: Union[str, list[dict[str, Any]]]) -> None:
        """Add a message dict to the session history."""
        self._history.append({"role": role, "content": content})
        self._trim_history()

    def clear(self) -> None:
        """Clear all conversation history in this session."""
        self._history.clear()

    def _trim_history(self) -> None:
        """Ensure history does not exceed max_history items."""
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

    def send(
        self,
        message: Union[str, list[dict[str, Any]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Response:
        """
        Send a message within this session context synchronously.
        Updates internal history with both user message and assistant reply.
        """
        prompt_sys = self.system_prompt or self.agent.system_prompt
        messages: list[dict[str, Any]] = []
        if prompt_sys:
            messages.append({"role": "system", "content": prompt_sys})
        messages.extend(self._history)
        messages.append({"role": "user", "content": message})

        reply_text = self.agent._call_messages(
            messages,
            temperature=temperature or self.agent.temperature,
            max_tokens=max_tokens or self.agent.max_tokens,
        )

        self.add_message("user", message)
        self.add_message("assistant", reply_text)
        return Response(text=reply_text, session_id=self.session_id)

    async def send_async(
        self,
        message: Union[str, list[dict[str, Any]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Response:
        """
        Send a message asynchronously within this session.
        Safe for use in asyncio event loops (e.g. Discord bots, FastAPI).
        """
        return await asyncio.to_thread(self.send, message, temperature, max_tokens)

    def stream(
        self,
        message: Union[str, list[dict[str, Any]]],
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """
        Stream the assistant reply token-by-token synchronously.
        Automatically records the complete reply into session history upon completion.
        """
        prompt_sys = self.system_prompt or self.agent.system_prompt
        messages: list[dict[str, Any]] = []
        if prompt_sys:
            messages.append({"role": "system", "content": prompt_sys})
        messages.extend(self._history)
        messages.append({"role": "user", "content": message})

        collected: list[str] = []

        def _handle_chunk(chunk: str) -> None:
            collected.append(chunk)
            if on_chunk:
                on_chunk(chunk)

        reply_text = self.agent.client.stream_ask(
            prompt=message if not self._history and not prompt_sys else messages,
            on_chunk=_handle_chunk,
            temperature=temperature or self.agent.temperature,
            max_tokens=max_tokens or self.agent.max_tokens,
        )

        self.add_message("user", message)
        self.add_message("assistant", reply_text)
        for c in collected:
            yield c

    async def stream_async(
        self,
        message: Union[str, list[dict[str, Any]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream the assistant reply asynchronously token-by-token.
        """
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        def _producer() -> None:
            try:
                for chunk in self.stream(message, temperature=temperature, max_tokens=max_tokens):
                    queue.put_nowait(chunk)
            finally:
                queue.put_nowait(None)

        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _producer)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk
