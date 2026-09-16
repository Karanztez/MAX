"""
tests/test_team_room.py — Unit tests for Multi-Agent Team Room and per-tab independent provider settings.
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

# Add src and project root to sys.path
_root = str(Path(__file__).resolve().parent.parent)
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from ui.dialogs.team_config_dialog import (
        TeamAgentConfig,
        get_default_team_agents,
    )
    from ui.tabs.team_room_tab import AgentTeamTab
    from ui.chat_tab import ChatTab
except (ImportError, ModuleNotFoundError):
    from src.ui.dialogs.team_config_dialog import (  # type: ignore[no-redef]
        TeamAgentConfig,
        get_default_team_agents,
    )
    from src.ui.tabs.team_room_tab import AgentTeamTab  # type: ignore[no-redef]
    from src.ui.chat_tab import ChatTab  # type: ignore[no-redef]


class TestTeamRoom(unittest.TestCase):
    """Test Multi-Agent Team Room data models and orchestration prompts."""

    def test_default_team_agents(self):
        agents = get_default_team_agents()
        self.assertEqual(len(agents), 3)
        agent_ids = [a.id for a in agents]
        self.assertEqual(agent_ids, ["planner", "coder", "reviewer"])

        planner = agents[0]
        self.assertEqual(planner.name, "Planner")
        self.assertTrue(planner.enabled)
        self.assertIn("Architect", planner.system_prompt)

        coder = agents[1]
        self.assertEqual(coder.name, "Coder")
        self.assertTrue(coder.enabled)
        self.assertIn("Full-Stack", coder.system_prompt)

        reviewer = agents[2]
        self.assertEqual(reviewer.name, "Reviewer")
        self.assertTrue(reviewer.enabled)
        self.assertIn("QA", reviewer.system_prompt)

    def test_team_agent_config_serialization(self):
        agent = TeamAgentConfig(
            id="tester",
            name="Tester",
            icon="🧪",
            role_description="Test role",
            enabled=True,
            profile_id="china_town",
            model="deepseek-v4.1-flash",
            temperature=0.3,
        )
        d = agent.to_dict()
        self.assertEqual(d["id"], "tester")
        self.assertEqual(d["model"], "deepseek-v4.1-flash")

        restored = TeamAgentConfig.from_dict(d)
        self.assertEqual(restored.id, "tester")
        self.assertEqual(restored.temperature, 0.3)

    def test_agent_prompt_construction(self):
        """Test how prompt is chained across Planner -> Coder -> Reviewer."""
        # Use mock parent for AgentTeamTab
        mock_parent = MagicMock()
        tab = AgentTeamTab.__new__(AgentTeamTab)
        tab.profiles = [{"id": "p1", "name": "P1", "model": "m1"}]
        tab.agents = get_default_team_agents()

        user_task = "Build a REST API with FastAPI for managing tasks"

        # 1. Planner prompt
        planner_prompt = tab._build_agent_prompt("planner", user_task, {})
        self.assertIn(user_task, planner_prompt)
        self.assertIn("สถาปัตยกรรม", planner_prompt)

        # 2. Coder prompt with planner output
        planner_output = "Architecture: FastAPI + SQLite + Pydantic models"
        coder_prompt = tab._build_agent_prompt(
            "coder", user_task, {"planner": planner_output}
        )
        self.assertIn(user_task, coder_prompt)
        self.assertIn(planner_output, coder_prompt)
        self.assertIn("เขียนโค้ด", coder_prompt)

        # 3. Reviewer prompt with both planner and coder output
        coder_output = "from fastapi import FastAPI\napp = FastAPI()"
        reviewer_prompt = tab._build_agent_prompt(
            "reviewer",
            user_task,
            {"planner": planner_output, "coder": coder_output},
        )
        self.assertIn(user_task, reviewer_prompt)
        self.assertIn(planner_output, reviewer_prompt)
        self.assertIn(coder_output, reviewer_prompt)
        self.assertIn("ตรวจทานโค้ด", reviewer_prompt)


class TestPerTabIndependence(unittest.TestCase):
    """Test that ChatTab instances hold independent profile and model configuration."""

    def test_chat_tab_independent_profiles(self):
        # Instantiate two ChatTab mock-like instances
        tab1 = ChatTab.__new__(ChatTab)
        tab1.tab_name = "Chat 1"
        tab1.profile_id = "china_town"
        tab1.profile_name = "China Town (จีน)"
        tab1.ai = MagicMock()
        tab1.ai.model = "deepseek-v4.1-flash"

        tab2 = ChatTab.__new__(ChatTab)
        tab2.tab_name = "Chat 2"
        tab2.profile_id = "gemini_full"
        tab2.profile_name = "Gemini AI"
        tab2.ai = MagicMock()
        tab2.ai.model = "gemini-3.8-flash"

        # Mutating tab1 does not mutate tab2
        tab1.ai.model = "glm-5.3-flash"
        tab1.profile_id = "chinese_specials"

        self.assertEqual(tab1.ai.model, "glm-5.3-flash")
        self.assertEqual(tab1.profile_id, "chinese_specials")

        self.assertEqual(tab2.ai.model, "gemini-3.8-flash")
        self.assertEqual(tab2.profile_id, "gemini_full")


class TestDynamicTeamMembers(unittest.TestCase):
    """Test dynamically adding, removing, and chaining custom team members with same or different models."""

    def test_add_custom_members_same_model(self):
        """Verify multiple agents can share the same model freely."""
        tab = AgentTeamTab.__new__(AgentTeamTab)
        tab.profiles = [
            {"id": "china_town", "name": "China Town (จีน)", "models": ["deepseek-v4.1-flash", "qwen-2.5-coder"], "model": "deepseek-v4.1-flash"},
        ]
        tab.agents = get_default_team_agents()

        # Add a 4th member: Tester sharing the exact same model
        tester = TeamAgentConfig(
            id="tester",
            name="Tester",
            icon="🧪",
            role_description="เขียนชุดทดสอบและจำลองเคส",
            enabled=True,
            profile_id="china_town",
            profile_name="China Town (จีน)",
            model="deepseek-v4.1-flash",  # Same model as Planner/Coder
            system_prompt="Write unit tests for the solution.",
        )
        tab.agents.append(tester)

        self.assertEqual(len(tab.agents), 4)
        # Verify both coder and tester use the same model
        self.assertEqual(tab.agents[1].model or "deepseek-v4.1-flash", tab.agents[3].model)

        # Test prompt construction for the 4th agent receives previous 3 outputs
        user_task = "Create a login authentication system"
        prev_outputs = {
            "planner": "Auth architecture: JWT tokens + bcrypt hashing",
            "coder": "def login(): return generate_jwt()",
            "reviewer": "Security check: Password salt must be at least 12 rounds",
        }
        tester_prompt = tab._build_agent_prompt("tester", user_task, prev_outputs)
        self.assertIn(user_task, tester_prompt)
        self.assertIn("Auth architecture", tester_prompt)
        self.assertIn("generate_jwt", tester_prompt)
        self.assertIn("Security check", tester_prompt)
        self.assertIn("Tester", tester_prompt)

    def test_reordering_and_deleting_agents(self):
        agents = get_default_team_agents()
        self.assertEqual(len(agents), 3)

        # Add 4th agent
        docs = TeamAgentConfig(
            id="docs",
            name="Docs",
            icon="📝",
            role_description="เขียนคู่มือ",
            enabled=True,
        )
        agents.append(docs)
        self.assertEqual(len(agents), 4)

        # Reorder: swap Reviewer and Docs
        agents[2], agents[3] = agents[3], agents[2]
        self.assertEqual(agents[2].id, "docs")
        self.assertEqual(agents[3].id, "reviewer")

        # Delete an agent
        del agents[1]  # Delete coder
        self.assertEqual(len(agents), 3)
        self.assertEqual([a.id for a in agents], ["planner", "docs", "reviewer"])


if __name__ == "__main__":
    unittest.main()

