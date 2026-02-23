from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

if __package__ is None or __package__ == "":
    # Support direct execution: python mcp_app/app.py
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from mcp_app.agent_flows import run_agent_tests, simulate_calendar_conversation
    from mcp_app.calendar_logic import smoke_test_current_time, test_today_primary_events
    from mcp_app.config import build_connections, load_environment
    from mcp_app.mcp_helpers import (
        load_langchain_tools,
        print_full_inventory,
        tools_for_agent,
        verify_langchain_tools,
    )
else:
    from .agent_flows import run_agent_tests, simulate_calendar_conversation
    from .calendar_logic import smoke_test_current_time, test_today_primary_events
    from .config import build_connections, load_environment
    from .mcp_helpers import (
        load_langchain_tools,
        print_full_inventory,
        tools_for_agent,
        verify_langchain_tools,
    )


async def async_main() -> None:
    """Main workflow for the Day 5 calendar MCP demo."""
    load_environment()

    print("\nConnecting MCP servers:")
    connections = build_connections()
    for server_name, connection in connections.items():
        cmd = connection.get("command", "")
        args = " ".join(connection.get("args", []))
        print(f"- {server_name}: {cmd} {args}")

    # Note: this langchain-mcp-adapters version does not support client context manager.
    client = MultiServerMCPClient(
        connections, tool_name_prefix=len(connections) > 1
    )

    # Load tools once and reuse them across all demo steps.
    loaded_tools = await load_langchain_tools(client, server_name=None)
    tools = tools_for_agent(loaded_tools)

    await print_full_inventory(client, connections)
    verify_langchain_tools(tools)

    #await smoke_test_current_time(tools)
    #await test_today_primary_events(tools)

    #await run_agent_tests(tools)
    await simulate_calendar_conversation(tools)


def main() -> None:
    """CLI entrypoint."""
    argparse.ArgumentParser(description="Google Calendar MCP LangChain demo").parse_args()

    try:
        asyncio.run(async_main())
    except FileNotFoundError as exc:
        cmd = os.getenv("MCP_SERVER_COMMAND", "npx")
        raise SystemExit(
            f"Failed to start MCP server command '{cmd}': {exc}. "
            "Install Node.js/npm (for npx) or set MCP_SERVER_COMMAND/MCP_SERVER_ARGS "
            "to a valid executable."
        ) from exc
    except Exception as exc:
        raise SystemExit(f"MCP connection test failed: {exc}") from exc


if __name__ == "__main__":
    main()
