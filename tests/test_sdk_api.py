"""
tests/test_sdk_api.py — Comprehensive Unit Tests for MAX AI Python SDK & Public API.
"""

import asyncio
import unittest
from unittest.mock import patch, MagicMock

import max_ai
from max_ai import MaxAgent, MaxSession, MaxTeam, Agent, Session, Team


class TestMaxAISDK(unittest.TestCase):
    def setUp(self):
        self.agent = MaxAgent(
            model="gemini-2.5-flash",
            api_key="test-api-key",
            auto_load_settings=False,
        )

    def test_imports_and_aliases(self):
        self.assertIs(Agent, MaxAgent)
        self.assertIs(Session, MaxSession)
        self.assertIs(Team, MaxTeam)
        self.assertTrue(hasattr(max_ai, "__version__"))

    def test_agent_initialization(self):
        agent = MaxAgent(
            model="deepseek-v4.1-flash",
            api_key="custom-key",
            system_prompt="Custom System",
            temperature=0.5,
            max_tokens=2048,
            auto_load_settings=False,
        )
        self.assertEqual(agent.model, "deepseek-v4.1-flash")
        self.assertEqual(agent.api_key, "custom-key")
        self.assertEqual(agent.system_prompt, "Custom System")
        self.assertEqual(agent.temperature, 0.5)
        self.assertEqual(agent.max_tokens, 2048)

    @patch("src.core.ai_client.AIClient._call_response")
    def test_agent_ask_sync(self, mock_call):
        mock_call.return_value = {"role": "assistant", "content": "Hello from Mock AI!"}
        reply = self.agent.ask("Hello")
        self.assertEqual(reply, "Hello from Mock AI!")
        self.assertTrue(mock_call.called)

    @patch("src.core.ai_client.AIClient._call_response")
    def test_agent_ask_async(self, mock_call):
        mock_call.return_value = {"role": "assistant", "content": "Async Response"}
        
        async def _run():
            return await self.agent.ask_async("Async test")

        reply = asyncio.run(_run())
        self.assertEqual(reply, "Async Response")

    @patch("src.core.ai_client.AIClient._call_response")
    def test_session_multi_turn_memory(self, mock_call):
        mock_call.side_effect = [
            {"role": "assistant", "content": "I am MAX AI."},
            {"role": "assistant", "content": "You said your name is Alex."},
        ]

        session = self.agent.create_session("user-101", max_history=10)
        self.assertEqual(session.session_id, "user-101")
        self.assertEqual(len(session.history), 0)

        # First turn
        r1 = session.send("Hello, my name is Alex.")
        self.assertEqual(r1.text, "I am MAX AI.")
        self.assertEqual(len(session.history), 2)
        self.assertEqual(session.history[0]["role"], "user")
        self.assertEqual(session.history[1]["role"], "assistant")

        # Second turn
        r2 = session.send("What is my name?")
        self.assertEqual(r2.text, "You said your name is Alex.")
        self.assertEqual(len(session.history), 4)

        # Clear session
        session.clear()
        self.assertEqual(len(session.history), 0)

    def test_session_history_trimming(self):
        session = self.agent.create_session("trim-test", max_history=4)
        for i in range(10):
            session.add_message("user", f"msg {i}")
        self.assertEqual(len(session.history), 4)
        self.assertEqual(session.history[-1]["content"], "msg 9")

    @patch("src.core.ai_client.AIClient._call_response")
    def test_multi_agent_team_pipeline(self, mock_call):
        mock_call.side_effect = [
            {"role": "assistant", "content": "Architecture plan: 1. API 2. Database"},
            {"role": "assistant", "content": "Code: def app(): return 'ok'"},
            {"role": "assistant", "content": "Review: Code is secure and passes audit."},
        ]

        team = MaxTeam(name="Test Team")
        team.add_member(1, name="Architect", role="planner", api_key="k1")
        team.add_member(2, name="Dev", role="coder", api_key="k2")
        team.add_member(3, name="QA", role="reviewer", api_key="k3")
        team.link(1, 2)
        team.link(2, 3)

        results = team.run("Build microservice")
        self.assertEqual(results["total_steps"], 3)
        self.assertIn("Review: Code is secure", results["final_output"])
        self.assertEqual(len(results["steps"]), 3)
        self.assertEqual(results["steps"][0]["member_name"], "Architect")
        self.assertEqual(results["steps"][1]["member_name"], "Dev")
        self.assertEqual(results["steps"][2]["member_name"], "QA")

    @patch("src.core.ai_client.AIClient._call_response")
    def test_convenience_functions(self, mock_call):
        mock_call.return_value = {"role": "assistant", "content": "Convenience answer"}
        ans = max_ai.ask("test", api_key="key")
        self.assertEqual(ans, "Convenience answer")

        chat_hist = max_ai.chat("hello", history=[], api_key="key")
        self.assertEqual(len(chat_hist), 2)


if __name__ == "__main__":
    unittest.main()
