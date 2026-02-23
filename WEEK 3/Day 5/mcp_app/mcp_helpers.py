from __future__ import annotations

from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient


async def load_langchain_tools(
    client: MultiServerMCPClient, server_name: str | None
) -> list:
    """Load MCP tools as LangChain tool objects."""
    if hasattr(client, "get_langchain_tools"):
        return await client.get_langchain_tools(server_name=server_name)
    return await client.get_tools(server_name=server_name)


def verify_langchain_tools(tools: list) -> None:
    """Show tool availability and callable methods."""
    print(f"\nLangChain Tool Verification ({len(tools)}):")
    if not tools:
        print("- No tools loaded.")
        return

    for tool in tools:
        name = getattr(tool, "name", "unknown")
        has_invoke = hasattr(tool, "invoke")
        has_ainvoke = hasattr(tool, "ainvoke")
        print(f"- {name}: invoke={has_invoke}, ainvoke={has_ainvoke}")


def find_tool_by_suffix(tools: list, suffix: str):
    """Find tool by exact name or suffix with optional server prefix."""
    for tool in tools:
        name = getattr(tool, "name", "")
        if name == suffix or name.endswith(f"_{suffix}"):
            return tool
    return None


def print_server_inventory(tools: list, server_name: str = "google_calendar") -> None:
    """Print a compact inventory once to avoid repeated noisy logs."""
    print("\n=== MCP Server Inventory ===")
    print(f"\nServer: {server_name}")
    print(f"  tools_count: {len(tools)}")
    for tool in tools:
        print(f"  - tool: {getattr(tool, 'name', str(tool))}")
    print("  resources_count: not requested (calendar workflow)")


def _resource_uri(resource: Any) -> str:
    """Extract URI from MCP resource objects across adapter versions."""
    return str(
        getattr(resource, "uri", None)
        or getattr(resource, "id", None)
        or (getattr(resource, "metadata", {}) or {}).get("uri")
        or "unknown-uri"
    )


def _resource_mime(resource: Any) -> str:
    """Extract MIME type from MCP resource objects across adapter versions."""
    return str(
        getattr(resource, "mimeType", None)
        or (getattr(resource, "metadata", {}) or {}).get("mime_type")
        or "unknown-mime"
    )


async def print_full_inventory(
    client: MultiServerMCPClient, connections: dict[str, dict[str, Any]]
) -> None:
    """Print tools and resources overview for every configured server."""
    print("\n=== MCP Server Inventory ===")
    for server_name in connections:
        print(f"\nServer: {server_name}")

        tools: list[Any] = []
        tools_error: str | None = None
        try:
            tools = await load_langchain_tools(client, server_name=server_name)
        except Exception as exc:
            tools_error = str(exc)

        print(f"  tools_count: {len(tools)}")
        if tools_error:
            print(f"  tools_error: {tools_error}")
        else:
            for tool in tools:
                print(f"  - tool: {getattr(tool, 'name', str(tool))}")

        resources: list[Any] = []
        resources_error: str | None = None
        try:
            if not hasattr(client, "session"):
                raise RuntimeError(
                    "session API unavailable in this langchain-mcp-adapters version."
                )
            async with client.session(server_name) as session:
                listed = await session.list_resources()
                resources = getattr(listed, "resources", []) or []
        except Exception as exc:
            resources_error = str(exc)

        print(f"  resources_count: {len(resources)}")
        if resources_error:
            print(f"  resources_error: {resources_error}")
        elif not resources:
            print("  - resource: none")
        else:
            for resource in resources:
                print(f"  - resource: {_resource_uri(resource)} ({_resource_mime(resource)})")


def extract_tool_json_payload(result: Any) -> Any:
    """Parse common MCP tool result format into dict-like data."""
    if isinstance(result, dict):
        return result
    if isinstance(result, list) and result and isinstance(result[0], dict):
        text = result[0].get("text")
        if text:
            try:
                import json

                return json.loads(text)
            except Exception:
                return {"raw_text": text}
    return {"raw": result}


def tools_for_agent(tools: list) -> list:
    """Return agent-safe tool list by removing tools that cause account-switch side effects."""
    blocked_suffixes = {"manage-accounts"}
    filtered = []
    for tool in tools:
        name = getattr(tool, "name", "")
        if any(name == s or name.endswith(f"_{s}") for s in blocked_suffixes):
            continue
        filtered.append(tool)
    return filtered


async def close_mcp_client(client: Any) -> None:
    """Best-effort MCP client teardown for adapter-version compatibility.

    Current adapter versions may not expose explicit close methods, but this keeps
    teardown explicit and forward-compatible if `aclose()` or `close()` becomes
    available in future versions.
    """
    try:
        if hasattr(client, "aclose"):
            await client.aclose()
            print("\nMCP client disconnected via aclose().")
            return
        if hasattr(client, "close"):
            client.close()
            print("\nMCP client disconnected via close().")
            return
        print(
            "\nMCP client teardown: no explicit close API on this "
            "langchain-mcp-adapters version."
        )
    except Exception as exc:
        print(f"\nMCP client teardown warning: {exc}")
