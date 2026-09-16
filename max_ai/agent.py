"""
max_ai.agent — High-level MaxAgent SDK interface.
Provides simple, unified sync & async AI interactions with tool execution and multi-provider support.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable, Iterator, Optional, Union

try:
    from core.ai_client import AIClient
    from core.provider_profiles import default_profiles
    from core.settings_store import SettingsStore
    from core.mcp_manager import MCPManager
    from core.skill_manager import SkillManager
except (ImportError, ModuleNotFoundError):
    from src.core.ai_client import AIClient  # type: ignore[no-redef]
    from src.core.provider_profiles import default_profiles  # type: ignore[no-redef]
    from src.core.settings_store import SettingsStore  # type: ignore[no-redef]
    from src.core.mcp_manager import MCPManager  # type: ignore[no-redef]
    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]

try:
    from .session import MaxSession, Response
except (ImportError, ModuleNotFoundError):
    from max_ai.session import MaxSession, Response  # type: ignore[no-redef]


class MaxAgent:
    """
    High-level MAX AI Agent.
    Supports single-turn ask, streaming, stateful sessions, tool execution, and multi-provider profiles.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
        enable_tools: bool = False,
        skills: Optional[list[str]] = None,
        api_mode: str = "chat_completions",
        auto_load_settings: bool = True,
    ):
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.enable_tools = enable_tools
        self._sessions: dict[str, MaxSession] = {}

        # Resolve provider profile settings
        resolved_api_key = api_key or ""
        resolved_base_url = base_url or ""
        resolved_model = model or ""
        resolved_api_mode = api_mode

        if auto_load_settings:
            try:
                store = SettingsStore()
                profiles, selected_id = store.load_provider_settings()
                active_profile = None
                if provider:
                    active_profile = next(
                        (p for p in profiles if str(p.get("id", "")).lower() == provider.lower()
                         or str(p.get("name", "")).lower() == provider.lower()),
                        None,
                    )
                if not active_profile:
                    active_profile = next((p for p in profiles if p.get("id") == selected_id), None)
                if not active_profile and profiles:
                    active_profile = profiles[0]

                if active_profile:
                    if not resolved_api_key and active_profile.get("api_key"):
                        resolved_api_key = active_profile["api_key"]
                    if not resolved_base_url and active_profile.get("base_url"):
                        resolved_base_url = active_profile["base_url"]
                    if not resolved_model and active_profile.get("model"):
                        resolved_model = active_profile["model"]
                    if active_profile.get("api_mode"):
                        resolved_api_mode = active_profile["api_mode"]
            except Exception:
                pass

        # Default fallback
        if not resolved_base_url:
            resolved_base_url = "https://api.maxplus-ai.cc/gemini-full/v1"
        if not resolved_model:
            resolved_model = "gemini-2.5-flash"

        self.client = AIClient(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            system_prompt=system_prompt,
            timeout=timeout,
            api_mode=resolved_api_mode,
        )

        # Initialize tools & skill manager if enabled
        self.mcp_manager: Optional[MCPManager] = None
        self.skill_manager: Optional[SkillManager] = None
        if enable_tools:
            self.mcp_manager = MCPManager()
            self.skill_manager = SkillManager()
            if skills:
                for s in skills:
                    skill_obj = self.skill_manager.get_skill(s)
                    if skill_obj and self.skill_manager:
                        self.skill_manager.activate_skill(skill_obj.name)

    @property
    def model(self) -> str:
        return self.client.model

    @model.setter
    def model(self, value: str) -> None:
        self.client.model = value

    @property
    def api_key(self) -> str:
        return self.client.api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        self.client.api_key = value

    def _call_messages(
        self,
        messages: list[dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Internal helper to dispatch messages through AIClient with optional tool resolution."""
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        tools_schema = None
        if self.enable_tools and self.mcp_manager:
            tools_schema = self.mcp_manager.get_openai_tools()

        # Call LLM
        res = self.client._call_response(messages, temperature=temp, max_tokens=tokens, tools=tools_schema)
        
        # Handle autonomous tool calls if requested
        tool_calls = res.get("tool_calls", [])
        if tool_calls and self.enable_tools and self.mcp_manager:
            # Autonomous execution loop
            updated_messages = list(messages)
            updated_messages.append(res)
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                tool_id = tc.get("id", "call_default")
                import json
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except Exception:
                    args = {}
                tool_output = self.mcp_manager.execute_tool(name, args)
                updated_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": str(tool_output),
                })
            # Second turn to synthesize final output
            final_res = self.client._call_response(updated_messages, temperature=temp, max_tokens=tokens)
            return str(final_res.get("content") or "")

        return str(res.get("content") or "")

    def ask(
        self,
        prompt: Union[str, list[dict[str, Any]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Ask a single question synchronously and return the answer string.
        
        Example:
            agent = max_ai.Agent()
            answer = agent.ask("สวัสดีครับ")
        """
        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._call_messages(messages, temperature=temperature, max_tokens=max_tokens)

    async def ask_async(
        self,
        prompt: Union[str, list[dict[str, Any]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Ask a question asynchronously. Safe for Discord bots and async servers.
        """
        return await asyncio.to_thread(self.ask, prompt, temperature, max_tokens)

    def stream(
        self,
        prompt: Union[str, list[dict[str, Any]]],
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """
        Stream the answer token-by-token synchronously.
        """
        return self.create_session("__temp_stream__").stream(
            prompt, on_chunk=on_chunk, temperature=temperature, max_tokens=max_tokens
        )

    async def stream_async(
        self,
        prompt: Union[str, list[dict[str, Any]]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream the answer asynchronously token-by-token.
        """
        session = self.create_session("__temp_stream_async__")
        async for chunk in session.stream_async(prompt, temperature=temperature, max_tokens=max_tokens):
            yield chunk

    def chat(
        self,
        user_message: Union[str, list[dict[str, Any]]],
        history: Optional[list[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Multi-turn chat function that receives and returns the updated history list.
        """
        hist = list(history or [])
        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(hist)
        messages.append({"role": "user", "content": user_message})

        reply = self._call_messages(messages, temperature=temperature, max_tokens=max_tokens)
        hist.append({"role": "user", "content": user_message})
        hist.append({"role": "assistant", "content": reply})
        return hist

    def create_session(
        self,
        session_id: str = "default",
        system_prompt: Optional[str] = None,
        max_history: int = 40,
    ) -> MaxSession:
        """Create and register an isolated stateful conversation session."""
        session = MaxSession(
            agent=self,
            session_id=session_id,
            system_prompt=system_prompt,
            max_history=max_history,
        )
        self._sessions[session_id] = session
        return session

    def get_session(
        self,
        session_id: str,
        create_if_missing: bool = True,
        system_prompt: Optional[str] = None,
    ) -> MaxSession:
        """Retrieve an existing session by ID or create a new one automatically."""
        if session_id not in self._sessions and create_if_missing:
            return self.create_session(session_id=session_id, system_prompt=system_prompt)
        return self._sessions[session_id]

    def clear_sessions(self) -> None:
        """Clear all registered sessions."""
        self._sessions.clear()
