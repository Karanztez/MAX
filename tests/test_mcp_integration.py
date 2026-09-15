"""
test_mcp_integration.py — Integration and unit tests for MCP support and new skills in MaxPlus AI.
"""

import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.skill_manager import SkillManager
from src.core.mcp_manager import MCPManager, MCPTool
from src.core.ai_client import AIClient


class TestSkillsAndMCP(unittest.TestCase):

    def test_skill_manager_discovers_all_skills(self):
        """Verify SkillManager discovers existing and newly added skills."""
        sm = SkillManager()
        skill_ids = set(sm.skills.keys())
        expected = {
            "code-reviewer",
            "image-analyst",
            "blender-3d",
            "overblock-minecraft",
            "pixel-artist",
            "interface-designer",
        }
        for exp in expected:
            self.assertIn(exp, skill_ids, f"Skill '{exp}' should be discovered")

        # Check prompt composition
        composed = sm.compose_system_prompt("Base instructions", ["blender-3d", "pixel-artist"])
        self.assertIn("Base instructions", composed)
        self.assertIn("Active skill: Blender 3D Specialist", composed)
        self.assertIn("Active skill: Pixel Artist", composed)

    def test_mcp_tool_to_openai_format(self):
        """Verify MCPTool formats correctly for OpenAI / Gemini function calling."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            server_name="test_server",
        )
        schema = tool.to_openai_tool()
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "test_tool")
        self.assertEqual(schema["function"]["description"], "A test tool")
        self.assertIn("query", schema["function"]["parameters"]["properties"])

    def test_mcp_builtins_execution(self):
        """Verify built-in tools (calculator, datetime, sysinfo) work accurately."""
        with TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "mcp_servers.json"
            mgr = MCPManager(config_path=cfg_file)

            # Test calculate
            calc_res = mgr.execute_tool("calculate", {"expression": "12 * 5 + 8"})
            self.assertEqual(calc_res, "68")

            # Test invalid calculate
            calc_err = mgr.execute_tool("calculate", {"expression": "__import__('os').system('dir')"})
            self.assertIn("invalid characters", calc_err)

            # Test datetime
            dt_res = mgr.execute_tool("get_current_time", {})
            self.assertTrue(len(dt_res) > 5)

            # Test system info
            sys_res = mgr.execute_tool("get_system_info", {})
            self.assertIn("Python", sys_res)

    def test_mcp_config_persistence(self):
        """Verify adding and removing MCP server configurations."""
        with TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "mcp_servers.json"
            mgr = MCPManager(config_path=cfg_file)
            mgr.add_server("demo_server", "python", ["server.py"])

            # Reload to verify saved to disk
            mgr2 = MCPManager(config_path=cfg_file)
            self.assertIn("demo_server", mgr2.server_configs.get("servers", {}))
            self.assertEqual(mgr2.server_configs["servers"]["demo_server"]["command"], "python")

            mgr2.remove_server("demo_server")
            mgr3 = MCPManager(config_path=cfg_file)
            self.assertNotIn("demo_server", mgr3.server_configs.get("servers", {}))

    def test_ai_client_chat_with_tools_mock(self):
        """Simulate autonomous tool loop in AIClient."""
        client = AIClient(api_key="mock-key")

        # Mock _call_response:
        # Turn 1: model returns tool_call for 'calculate'
        # Turn 2: model returns final text summarizing calculation
        call_count = 0

        def mock_call_response(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "type": "function",
                            "function": {
                                "name": "calculate",
                                "arguments": json.dumps({"expression": "25 * 4"}),
                            },
                        }
                    ],
                }
            else:
                return {
                    "role": "assistant",
                    "content": "ผลการคำนวณคือ 100",
                }

        client._call_response = mock_call_response  # type: ignore

        executed = {}
        def mock_executor(name, args):
            executed[name] = args
            return "100"

        history, logs = client.chat_with_tools(
            user_message="25 คูณ 4 ได้เท่าไหร่?",
            tools=[{"type": "function", "function": {"name": "calculate"}}],
            tool_executor=mock_executor,
        )

        self.assertIn("calculate", executed)
        self.assertEqual(executed["calculate"], {"expression": "25 * 4"})
        self.assertEqual(history[-1]["role"], "assistant")
        self.assertEqual(history[-1]["content"], "ผลการคำนวณคือ 100")
        self.assertTrue(len(logs) > 0)


if __name__ == "__main__":
    unittest.main()
