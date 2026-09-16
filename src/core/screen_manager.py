"""
src/core/screen_manager.py — MAX Virtual Screen & Multi-Agent Linked Screen Manager.
Enables CLI and API to manage independent screens (1, 2, 3...), link screens in pipeline
(e.g. Screen 1: Planner -> Screen 2: Coder -> Screen 3: Reviewer), and switch between screens seamlessly.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
import time
from typing import Any, Callable, Optional


@dataclass
class Screen:
    id: str
    name: str
    role: str = "general"
    model: str = ""
    profile_id: str = ""
    system_prompt: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)
    linked_to: Optional[str] = None  # Next screen ID in pipeline
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Screen":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ScreenManager:
    """Manages virtual terminal screens (IDs 1, 2, 3...) and chaining/linking."""

    def __init__(self) -> None:
        self.screens: dict[str, Screen] = {}
        self.active_id: str = "1"
        self._next_num: int = 1
        # Initialize default main screen
        self.create_screen(name="Main", role="general")

    def create_screen(
        self,
        name: str,
        role: str = "general",
        model: str = "",
        profile_id: str = "",
        system_prompt: str = "",
        linked_to: Optional[str] = None,
    ) -> Screen:
        """Create a new screen with the next sequential ID."""
        # Find lowest unused positive integer ID
        num = 1
        while str(num) in self.screens:
            num += 1
        screen_id = str(num)

        screen = Screen(
            id=screen_id,
            name=name,
            role=role,
            model=model,
            profile_id=profile_id,
            system_prompt=system_prompt,
            linked_to=linked_to,
        )
        self.screens[screen_id] = screen
        return screen

    def get_screen(self, screen_id: str) -> Optional[Screen]:
        """Get screen by ID."""
        return self.screens.get(str(screen_id).strip())

    @property
    def active_screen(self) -> Screen:
        """Return the currently selected active screen."""
        if self.active_id not in self.screens:
            if self.screens:
                self.active_id = next(iter(self.screens.keys()))
            else:
                self.create_screen(name="Main")
                self.active_id = "1"
        return self.screens[self.active_id]

    def switch_screen(self, screen_id: str) -> bool:
        """Switch active screen to the given ID."""
        sid = str(screen_id).strip()
        if sid in self.screens:
            self.active_id = sid
            return True
        return False

    def list_screens(self) -> list[Screen]:
        """Return all screens sorted by numeric ID where possible."""
        def _sort_key(s: Screen) -> int:
            try:
                return int(s.id)
            except ValueError:
                return 9999
        return sorted(self.screens.values(), key=_sort_key)

    def link_screens(self, from_id: str, to_id: str) -> bool:
        """Link from_screen to to_screen to form an execution pipeline."""
        fid, tid = str(from_id).strip(), str(to_id).strip()
        if fid in self.screens and tid in self.screens and fid != tid:
            self.screens[fid].linked_to = tid
            return True
        return False

    def unlink_screen(self, screen_id: str) -> bool:
        """Unlink screen from any pipeline target."""
        sid = str(screen_id).strip()
        if sid in self.screens:
            self.screens[sid].linked_to = None
            return True
        return False

    def remove_screen(self, screen_id: str) -> bool:
        """Close/remove a screen. Cannot delete last remaining screen."""
        sid = str(screen_id).strip()
        if sid in self.screens and len(self.screens) > 1:
            del self.screens[sid]
            # Clean any dangling links
            for s in self.screens.values():
                if s.linked_to == sid:
                    s.linked_to = None
            if self.active_id == sid:
                self.active_id = next(iter(self.screens.keys()))
            return True
        return False

    def setup_team_screens(self, default_model: str = "") -> list[Screen]:
        """
        Setup standard 3-agent linked team screens:
        Screen 1: 📋 Planner  -> linked to Screen 2
        Screen 2: 💻 Coder    -> linked to Screen 3
        Screen 3: 🔍 Reviewer -> end of pipeline
        """
        # Reset to clean 3 screens
        self.screens.clear()

        s1 = Screen(
            id="1",
            name="Planner",
            role="planner",
            model=default_model,
            system_prompt=(
                "You are an expert Software Architect & Technical Planner. "
                "Analyze user requirements, formulate technical specifications, "
                "and design clean implementation plans for the Coder."
            ),
            linked_to="2",
        )
        s2 = Screen(
            id="2",
            name="Coder",
            role="coder",
            model=default_model,
            system_prompt=(
                "You are a Senior Full-Stack Software Engineer. "
                "Implement complete, production-ready, clean, and robust code "
                "based on the Planner's specifications."
            ),
            linked_to="3",
        )
        s3 = Screen(
            id="3",
            name="Reviewer",
            role="reviewer",
            model=default_model,
            system_prompt=(
                "You are a Staff QA Engineer & Security Auditor. "
                "Inspect the Coder's implementation, find bugs, check security, "
                "and give a final quality verdict."
            ),
            linked_to=None,
        )

        self.screens["1"] = s1
        self.screens["2"] = s2
        self.screens["3"] = s3
        self.active_id = "1"
        return [s1, s2, s3]
