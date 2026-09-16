"""
mcp — Model Context Protocol (MCP) modular package for MAX AI Agent.
"""

from __future__ import annotations

from .builtins.file_tools import (
    _builtin_delete_file,
    _builtin_edit_file_snippet,
    _builtin_get_file_info,
    _builtin_list_dir,
    _builtin_read_file,
    _builtin_replace_file_content,
    _builtin_search_files,
    _builtin_write_file,
    get_file_tools,
)
from .builtins.git_tools import (
    _builtin_github_clone_repo,
    _builtin_github_get_repo,
    _builtin_github_list_issues,
    _builtin_github_read_file,
    _builtin_github_search_repos,
    get_git_tools,
)
from .builtins.media_tools import (
    _builtin_export_to_download,
    _builtin_generate_image,
    _builtin_generate_video,
    get_media_tools,
)
from .builtins.skill_tools import (
    _builtin_install_skill,
    _builtin_list_skills,
    _builtin_remove_skill,
    get_skill_tools,
)
from .builtins.system_tools import (
    _builtin_base64_codec,
    _builtin_calculate,
    _builtin_get_clipboard,
    _builtin_get_current_time,
    _builtin_get_environment_variable,
    _builtin_git_diff,
    _builtin_git_log,
    _builtin_git_status,
    _builtin_hash_data,
    _builtin_json_format,
    _builtin_list_processes,
    _builtin_run_command,
    _builtin_run_python_code,
    _builtin_set_clipboard,
    _builtin_system_info,
    _builtin_task_status,
    get_system_tools,
)
from .builtins.web_tools import (
    _builtin_fetch_web,
    _builtin_http_request,
    _builtin_search_web,
    check_web_permission,
    get_web_tools,
    set_web_permission_handler,
)
from .connection import MCPServerConnection
from .diff_engine import DiffColors, render_diff, replace_content_chunk
from .manager import MCPManager
from .types import MCPTool

__all__ = [
    "MCPManager",
    "MCPTool",
    "MCPServerConnection",
    "set_web_permission_handler",
    "check_web_permission",
    "render_diff",
    "replace_content_chunk",
    "DiffColors",
    # Builtin functions for backward compatibility
    "_builtin_calculate",
    "_builtin_get_current_time",
    "_builtin_system_info",
    "_builtin_run_command",
    "_builtin_run_python_code",
    "_builtin_git_status",
    "_builtin_git_diff",
    "_builtin_git_log",
    "_builtin_list_processes",
    "_builtin_get_environment_variable",
    "_builtin_json_format",
    "_builtin_hash_data",
    "_builtin_base64_codec",
    "_builtin_task_status",
    "_builtin_get_clipboard",
    "_builtin_set_clipboard",
    "_builtin_list_dir",
    "_builtin_read_file",
    "_builtin_write_file",
    "_builtin_replace_file_content",
    "_builtin_edit_file_snippet",
    "_builtin_get_file_info",
    "_builtin_delete_file",
    "_builtin_search_files",
    "_builtin_search_web",
    "_builtin_fetch_web",
    "_builtin_http_request",
    "_builtin_github_search_repos",
    "_builtin_github_get_repo",
    "_builtin_github_read_file",
    "_builtin_github_list_issues",
    "_builtin_github_clone_repo",
    "_builtin_generate_image",
    "_builtin_generate_video",
    "_builtin_export_to_download",
    "_builtin_install_skill",
    "_builtin_remove_skill",
    "_builtin_list_skills",
]
