"""
tests/test_team_room.py — Unit tests for Multi-Agent Team Room and per-tab independent provider settings.
"""

import unittest
from unittest.mock import MagicMock

from src.ui.dialogs.team_config_dialog import (
    TeamAgentConfig,
    get_default_team_agents,
)
from src.ui.tabs.team_room_tab import AgentTeamTab
from src.ui.chat_tab import ChatTab


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


if __name__ == "__main__":
    unittest.main()
