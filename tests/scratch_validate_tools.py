"""
scratch_validate_tools.py — Scratch script to validate MCP tools & schemas.
"""
import sys
from pathlib import Path

# Ensure root and src directory are in path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "src"))

try:
    from core.mcp.manager import MCPManager
except ImportError:
    from src.core.mcp.manager import MCPManager  # type: ignore[no-redef]


def main() -> None:
    mgr = MCPManager()
    tools = mgr.get_openai_tools()
    print(f"Total tools registered: {len(tools)}")
    for t in tools:
        fn = t.get("function", {})
        print(f" - {fn.get('name')}: {fn.get('description', '')[:50]}")


if __name__ == "__main__":
    main()
