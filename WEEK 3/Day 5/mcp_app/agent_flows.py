from __future__ import annotations

import os

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI


def get_agent_queries() -> list[str]:
    """Agent demo queries (can be overridden via AGENT_TEST_QUERIES env var)."""
    queries_raw = os.getenv("AGENT_TEST_QUERIES", "").strip()
    if queries_raw:
        return [q.strip() for q in queries_raw.split("||") if q.strip()]
    return [
        "What is the current time according to my calendar account? Use tools.",
        "What events do I have today on my primary calendar?",
        "What events do I have tomorrow on my primary calendar?",
    ]


def extract_agent_answer(result: dict) -> str:
    """Extract final assistant answer text from agent output."""
    messages = result.get("messages", [])
    if not messages:
        return "(No messages returned)"

    final = messages[-1]
    content = getattr(final, "content", "")
    return content if isinstance(content, str) else str(content)


def count_tool_calls(result: dict) -> int:
    """Count tool calls used in one agent response."""
    count = 0
    for message in result.get("messages", []):
        calls = getattr(message, "tool_calls", None) or []
        count += len(calls)
    return count


async def run_agent_tests(tools: list) -> None:
    """Run simple agent tests on primary calendar."""
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name, temperature=0)

    system_prompt = (
        "You are a calendar assistant focused on the primary Google Calendar only. "
        "Use MCP calendar tools and be concise."
    )
    agent = create_agent(model=llm, tools=tools, system_prompt=system_prompt)
    print(f"\nAgent created with model: {model_name}")

    for idx, query in enumerate(get_agent_queries(), start=1):
        print(f"\nAgent Test {idx}: {query}")
        result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
        print(f"Tool calls used: {count_tool_calls(result)}")
        print(f"Answer: {extract_agent_answer(result)}")


async def simulate_calendar_conversation(tools: list) -> None:
    """Simulate two-turn conversation with prompt-driven scheduling behavior."""
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name, temperature=0)
    calendar_account = os.getenv("GOOGLE_CALENDAR_ACCOUNT", "normal")

    system_prompt = (
        "You are a scheduling assistant. Use MCP tools to inspect calendar availability, "
        "read events, create events on calendarId='primary', and use Google Drive MCP tools when file lookup is requested. "
        f"Use account='{calendar_account}' when account selection is required."
    )
    agent = create_agent(model=llm, tools=tools, system_prompt=system_prompt)

    print("\n=== Simulated Conversation Results ===")

    turn_1 = "Please retrieve my calendar events for tomorrow."
    print(f"\nTurn 1 User: {turn_1}")
    result_1 = await agent.ainvoke({"messages": [{"role": "user", "content": turn_1}]})
    print(f"Turn 1 Assistant tool_calls: {count_tool_calls(result_1)}")
    print(f"Turn 1 Assistant answer: {extract_agent_answer(result_1)}")

    turn_2 = (
        "Please create a 1-hour event on my primary calendar for tomorrow called "
        "'Review AI concepts'. Schedule it in the earliest available time slot between "
        "08:00 and 20:00 in my calendar timezone, and make sure it does not overlap "
        "with any existing event. If no 1-hour slot is available in that window, "
        "do not create anything and tell me that no valid slot is available. "
        "Also, find the file 'ACFT02_AI Dictionary.pptx' in Google Drive and use its "
        "PDF version in the event: attach it if possible, otherwise include the PDF "
        "Google Drive link in the event description. "
        "When done, tell me the event title, start and end times, confirm there is "
        "no overlap, and mention which Google Drive result you used."
    )
    print(f"\nTurn 2 User: {turn_2}")
    try:
        result_2 = await agent.ainvoke({"messages": [{"role": "user", "content": turn_2}]})
        print(f"Turn 2 Assistant tool_calls: {count_tool_calls(result_2)}")
        print(f"Turn 2 Assistant answer: {extract_agent_answer(result_2)}")
    except Exception as exc:
        print(f"Turn 2 first attempt failed: {exc}")
        retry_prompt = (
            "Retry with strict schema-safe tool calls only. "
            "Use google_drive_search with ONLY {'query':'ACFT02_AI Dictionary.pptx'}. "
            "Use google_calendar_list-events (not get-freebusy) to find earliest free 1-hour slot between 08:00 and 20:00 tomorrow on calendarId='primary'. "
            "Then call google_calendar_create-event with only: calendarId, summary, description, start, end, attachments. "
            "No unknown keys. If no slot exists, do not create."
        )
        try:
            result_2_retry = await agent.ainvoke(
                {"messages": [{"role": "user", "content": retry_prompt}]}
            )
            print(f"Turn 2 Assistant tool_calls (retry): {count_tool_calls(result_2_retry)}")
            print(f"Turn 2 Assistant answer (retry): {extract_agent_answer(result_2_retry)}")
        except Exception as retry_exc:
            print(f"Turn 2 retry failed: {retry_exc}")
            print(
                "Turn 2 could not complete because one or more MCP tool calls returned "
                "'invalid_request' (currently observed on google_drive_search)."
            )
