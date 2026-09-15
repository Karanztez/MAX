"""
test_mcp_integration.py — Integration and unit tests for MCP support and new skills in MaxPlus AI.
"""

import sys
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
        """Verify built-in tools (calculator, datetime, sysinfo, file ops, shell, python) work accurately."""
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

            # Test write_file & read_file
            demo_path = str(Path(tmpdir) / "sub" / "hello.py")
            write_res = mgr.execute_tool("write_file", {"path": demo_path, "content": "print('MAX Agent AI')\n# Second line"})
            self.assertIn("สำเร็จ", write_res)

            read_res = mgr.execute_tool("read_file", {"path": demo_path})
            self.assertIn("MAX Agent AI", read_res)
            self.assertIn("Lines 1-2", read_res)

            # Test search_files
            search_res = mgr.execute_tool("search_files", {"query": "Agent AI", "path": tmpdir})
            self.assertIn("hello.py", search_res)

            # Test list_directory
            list_res = mgr.execute_tool("list_directory", {"path": tmpdir})
            self.assertIn("hello.py", list_res)

            # Test run_python_code
            py_res = mgr.execute_tool("run_python_code", {"code": "print('HELLO_FROM_SANDBOX')"})
            self.assertIn("HELLO_FROM_SANDBOX", py_res)

            # Test run_command
            cmd_res = mgr.execute_tool("run_command", {"command": f"{sys.executable} -c \"print('CMD_OK')\""})
            self.assertIn("CMD_OK", cmd_res)
            self.assertIn("Exit Code: 0", cmd_res)

            # Check tools list
            all_tools = mgr.get_all_tools()
            tool_names = {t.name for t in all_tools}
            expected_names = {
                "calculate", "get_current_time", "get_system_info",
                "search_web", "fetch_web_content", "list_directory",
                "read_file", "write_file", "search_files",
                "run_command", "run_python_code",
            }
            for name in expected_names:
                self.assertIn(name, tool_names, f"Built-in tool '{name}' must be registered")

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
