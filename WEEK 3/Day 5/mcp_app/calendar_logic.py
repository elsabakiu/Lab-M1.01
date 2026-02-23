from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .mcp_helpers import extract_tool_json_payload, find_tool_by_suffix


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime text returned by calendar tools."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def extract_events_from_result(result: Any) -> list[dict[str, Any]]:
    """Extract event list from list-events tool output."""
    payload = extract_tool_json_payload(result)
    if isinstance(payload, dict):
        return payload.get("events", []) or payload.get("items", []) or []
    return []


async def smoke_test_current_time(tools: list) -> None:
    """Quick runtime check that time tool works."""
    tool = find_tool_by_suffix(tools, "get-current-time")
    if not tool:
        print("\nSmoke test skipped: 'get-current-time' tool not found.")
        return

    try:
        result = await tool.ainvoke({})
        preview = str(result).replace("\n", " ")[:160]
        print(f"\nSmoke test passed for 'get-current-time': {preview}")
    except Exception as exc:
        print(f"\nSmoke test failed for 'get-current-time': {exc}")


async def test_today_primary_events(tools: list) -> list[dict[str, Any]]:
    """Fetch and print today's events from primary calendar."""
    tool = find_tool_by_suffix(tools, "list-events")
    if not tool:
        print("\nToday events test skipped: 'list-events' tool not found.")
        return []

    now = datetime.now().astimezone()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_next_day = start_of_day + timedelta(days=1)

    payload = {
        "calendarId": "primary",
        "timeMin": start_of_day.isoformat(),
        "timeMax": start_of_next_day.isoformat(),
    }

    print(
        "\nToday events query:"
        f" calendarId=primary, timeMin={payload['timeMin']},"
        f" timeMax={payload['timeMax']}"
    )

    try:
        result = await tool.ainvoke(payload)
    except Exception as exc:
        print(f"Today events test failed: {exc}")
        return []

    events = extract_events_from_result(result)
    print(f"Today events found: {len(events)}")
    for event in events:
        summary = event.get("summary", "(No title)")
        start = (event.get("start") or {}).get("dateTime") or (event.get("start") or {}).get("date")
        end = (event.get("end") or {}).get("dateTime") or (event.get("end") or {}).get("date")
        print(f"- {summary} | {start} -> {end}")

    return events
