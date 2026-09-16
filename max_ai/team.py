"""
max_ai.team — Programmatic Multi-Agent Team Pipeline API.
Allows chaining multiple specialized agents (Planner -> Coder -> Reviewer) in code.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional, Union

from src.core.screen_manager import ScreenManager, Screen
from max_ai.agent import MaxAgent


class TeamMember:
    """Represents a member in a multi-agent team pipeline."""

    def __init__(
        self,
        id: int,
        name: str,
        role: str = "general",
        model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.role = role
        self.model = model
        self.agent = MaxAgent(
            model=model,
            api_key=api_key,
            system_prompt=system_prompt or f"You are {name}, a specialized {role} agent in the MAX AI team pipeline.",
        )
        self.linked_to: Optional[int] = None

    def __repr__(self) -> str:
        return f"TeamMember(id={self.id}, name={self.name!r}, role={self.role!r}, linked_to={self.linked_to})"


class MaxTeam:
    """
    Programmatic Multi-Agent Team Pipeline.
    
    Example:
        team = max_ai.Team()
        team.add_member(1, name="Architect", role="planner", model="gemini-2.5-pro")
        team.add_member(2, name="Engineer", role="coder", model="deepseek-v4.1-flash")
        team.link(1, 2)
        
        result = team.run("สร้าง REST API ด้วย FastAPI")
    """

    def __init__(self, name: str = "Default Team"):
        self.name = name
        self.members: dict[int, TeamMember] = {}

    def add_member(
        self,
        id: int,
        name: str,
        role: str = "general",
        model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> TeamMember:
        """Add or update a team member."""
        member = TeamMember(
            id=id,
            name=name,
            role=role,
            model=model,
            api_key=api_key,
            system_prompt=system_prompt,
        )
        self.members[id] = member
        return member

    def link(self, from_id: int, to_id: int) -> None:
        """Link output of from_id to feed into to_id."""
        if from_id in self.members:
            self.members[from_id].linked_to = to_id

    def unlink(self, from_id: int) -> None:
        """Unlink member output."""
        if from_id in self.members:
            self.members[from_id].linked_to = None

    def create_default_pipeline(self, model: str = "gemini-2.5-flash") -> None:
        """Initialize standard 3-stage team: Planner (1) -> Coder (2) -> Reviewer (3)."""
        self.members.clear()
        self.add_member(
            1,
            "Planner",
            role="planner",
            model=model,
            system_prompt="You are a Lead Software Architect. Create a step-by-step implementation plan for the user request.",
        )
        self.add_member(
            2,
            "Coder",
            role="coder",
            model=model,
            system_prompt="You are an Expert Full-Stack Developer. Write production-ready code based on the architecture plan.",
        )
        self.add_member(
            3,
            "Reviewer",
            role="reviewer",
            model=model,
            system_prompt="You are a Senior QA and Security Reviewer. Audit the code for bugs, edge cases, and optimizations.",
        )
        self.link(1, 2)
        self.link(2, 3)

    def run(
        self,
        task: str,
        start_id: int = 1,
        max_hops: int = 6,
        on_step: Optional[Callable[[TeamMember, str], None]] = None,
    ) -> dict[str, Any]:
        """
        Execute the team pipeline sequentially across linked members.
        """
        if not self.members:
            self.create_default_pipeline()

        current_id: Optional[int] = start_id
        current_input = task
        hops = 0
        execution_log: list[dict[str, Any]] = []

        visited: set[int] = set()

        while current_id is not None and hops < max_hops:
            if current_id not in self.members:
                break
            if current_id in visited:
                break

            member = self.members[current_id]
            visited.add(current_id)
            hops += 1

            # Dispatch task to member
            prompt = (
                f"Your task / previous input is:\n\n{current_input}\n\n"
                f"Please produce your specialized contribution as the {member.role} ({member.name})."
            )
            response_text = member.agent.ask(prompt)

            execution_log.append({
                "step": hops,
                "member_id": member.id,
                "member_name": member.name,
                "member_role": member.role,
                "model": member.model,
                "input": current_input,
                "output": response_text,
            })

            if on_step:
                on_step(member, response_text)

            current_input = response_text
            current_id = member.linked_to

        return {
            "task": task,
            "final_output": current_input,
            "steps": execution_log,
            "total_steps": hops,
        }

    async def run_async(
        self,
        task: str,
        start_id: int = 1,
        max_hops: int = 6,
        on_step: Optional[Callable[[TeamMember, str], None]] = None,
    ) -> dict[str, Any]:
        """Run team pipeline asynchronously."""
        return await asyncio.to_thread(self.run, task, start_id, max_hops, on_step)
