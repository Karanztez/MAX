"""
test_mcp_integration.py — Integration and unit tests for MCP support and new skills in MaxPlus AI.
"""

import sys
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.skill_manager import SkillManager
    from core.mcp_manager import MCPManager, MCPTool
    from core.ai_client import AIClient
except ImportError:
    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]
    from src.core.mcp_manager import MCPManager, MCPTool  # type: ignore[no-redef]
    from src.core.ai_client import AIClient  # type: ignore[no-redef]


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

            # Test edit_file_snippet
            edit_res = mgr.execute_tool("edit_file_snippet", {
                "path": demo_path,
                "target": "MAX Agent AI",
                "replacement": "MAX Super Agent AI"
            })
            self.assertIn("สำเร็จ", edit_res)
            updated_content = Path(demo_path).read_text(encoding="utf-8")
            self.assertIn("MAX Super Agent AI", updated_content)

            # Test get_file_info
            info_res = mgr.execute_tool("get_file_info", {"path": demo_path})
            self.assertIn("Lines: 2", info_res)

            # Test json_format
            json_res = mgr.execute_tool("json_format", {"json_text": '{"max":1,"mode":"turbo"}'})
            self.assertIn('"turbo"', json_res)

            # Test hash_data
            hash_res = mgr.execute_tool("hash_data", {"text": "MAX_AGENT"})
            self.assertTrue(len(hash_res) == 64)

            # Test base64_codec
            b64_enc = mgr.execute_tool("base64_codec", {"text": "hello_max", "action": "encode"})
            b64_dec = mgr.execute_tool("base64_codec", {"text": b64_enc, "action": "decode"})
            self.assertEqual(b64_dec, "hello_max")

            # Check tools list
            all_tools = mgr.get_all_tools()
            tool_names = {t.name for t in all_tools}
            expected_names = {
                "calculate", "get_current_time", "get_system_info",
                "search_web", "fetch_web_content", "list_directory",
                "read_file", "write_file", "search_files",
                "run_command", "run_python_code",
                "edit_file_snippet", "get_file_info", "delete_file",
                "http_request", "git_status", "git_diff", "git_log",
                "list_processes", "get_environment_variable",
                "json_format", "hash_data", "base64_codec",
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

    def test_selected_workspace_is_used_for_relative_file_and_command_tools(self):
        """Relative file paths and commands must use the selected project directory."""
        with TemporaryDirectory() as tmpdir:
            mgr = MCPManager(config_path=Path(tmpdir) / "mcp_servers.json")
            previous_root = mgr.workspace_root
            try:
                mgr.set_workspace_root(tmpdir)
                result = mgr.execute_tool("write_file", {
                    "path": "src/example.py",
                    "content": "VALUE = 42\n",
                })
                expected = Path(tmpdir) / "src" / "example.py"
                self.assertTrue(expected.exists())
                self.assertEqual(expected.read_text(encoding="utf-8"), "VALUE = 42\n")
                self.assertNotIn("Error", result)

                command = mgr.execute_tool("run_command", {
                    "command": f'{sys.executable} -c "from pathlib import Path; print(Path.cwd())"',
                })
                self.assertIn(str(Path(tmpdir).resolve()), command)
            finally:
                mgr.set_workspace_root(previous_root if previous_root.exists() else Path.cwd())

    def test_frozen_app_never_uses_its_exe_as_python_interpreter(self):
        try:
            from core.mcp.builtins import system_tools
            _python_interpreter_command = system_tools._python_interpreter_command
            sys_tools_target = "core.mcp.builtins.system_tools"
        except (ImportError, ModuleNotFoundError):
            from src.core.mcp.builtins import system_tools  # type: ignore[no-redef]
            _python_interpreter_command = system_tools._python_interpreter_command
            sys_tools_target = "src.core.mcp.builtins.system_tools"

        with patch.object(sys, "frozen", True, create=True):
            with patch(f"{sys_tools_target}.shutil.which", return_value=None):
                self.assertIsNone(_python_interpreter_command())

            with patch(f"{sys_tools_target}.shutil.which", side_effect=lambda name: "C:/Python/python.exe" if name == "python" else None):
                self.assertEqual(_python_interpreter_command(), ["C:/Python/python.exe"])

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

    def test_responses_mode_executes_tools_and_converts_function_history(self):
        """Responses API profiles must participate in the autonomous tool loop."""
        client = AIClient(api_key="mock-key", api_mode="responses")
        calls = 0

        def mock_call_response(messages, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "call_write",
                        "type": "function",
                        "function": {"name": "write_file", "arguments": '{"path":"demo.txt","content":"ok"}'},
                    }],
                }
            converted = AIClient._response_input_items(messages)
            self.assertTrue(any(item.get("type") == "function_call" for item in converted))
            self.assertTrue(any(item.get("type") == "function_call_output" for item in converted))
            return {"role": "assistant", "content": "File updated."}

        client._call_response = mock_call_response  # type: ignore[method-assign]
        executed = []
        history, _logs = client.chat_with_tools(
            "Update demo.txt",
            tools=[{"type": "function", "function": {"name": "write_file", "parameters": {"type": "object"}}}],
            tool_executor=lambda name, args: executed.append((name, args)) or "Write verified",
        )

        self.assertEqual(executed[0][0], "write_file")
        self.assertEqual(executed[0][1]["content"], "ok")
        self.assertEqual(history[-1]["content"], "File updated.")

    def test_ai_client_chat_with_tools_synthesis_fallback(self):
        """Verify that when tool loop finishes with empty content, a synthesis call is triggered."""
        client = AIClient(api_key="mock-key")

        # Simulate round that returns tool calls up to max_tool_rounds
        def mock_call_response(messages, **kwargs):
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "lookup",
                            "arguments": json.dumps({"q": "test"}),
                        },
                    }
                ],
            }

        client._call_response = mock_call_response  # type: ignore

        # The synthesis call should be called to generate the final text
        client._call = lambda msgs, **kwargs: "สรุปผลลัพธ์จากการค้นหาสำเร็จ"  # type: ignore

        history, logs = client.chat_with_tools(
            user_message="ช่วยค้นหาข้อมูลหน่อย",
            tools=[{"type": "function", "function": {"name": "lookup"}}],
            tool_executor=lambda name, args: "พบข้อมูลเวอร์ชัน 1.0",
            max_tool_rounds=2,
        )

        self.assertEqual(history[-1]["role"], "assistant")
        self.assertEqual(history[-1]["content"], "สรุปผลลัพธ์จากการค้นหาสำเร็จ")
        self.assertTrue(any("กำลังประมวลผลและสรุปคำตอบ" in log for log in logs))


if __name__ == "__main__":
    unittest.main()
