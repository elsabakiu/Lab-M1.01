"""Beginner-friendly LangChain 1.x agent with themed tools.

Read this file top-to-bottom:
1) Configure prompts/input
2) Define tools
3) Build agent + helpers
4) Run in main()
"""

from __future__ import annotations

import os
import random
import sys
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool

# ----------------------------
# 1) Global configuration
# ----------------------------
CREATIVE_SYSTEM_PROMPT = (
    "You are the Normal Objects investigator for Hawkins anomalies.\n"
    "Solve problems creatively but coherently.\n"
    "Use available tools flexibly in any order, and combine multiple tools when useful.\n"
    "If tool outputs conflict, explain the conflict and propose a practical next step.\n"
    "End with a concise action plan."
)

SAMPLE_USER_MESSAGE = (
    "The portal flickers, monsters act differently at night, and power "
    "keeps cutting out. Give a creative diagnosis and fix."
)

SAMPLE_COMPLAINTS = [
    "Why do demogorgons sometimes eat people and sometimes don't?",
    "The portal opens on different days-is there a schedule?",
    "Why can some psychics see the Downside Up and others can't?",
    "Why do creatures and power lines react so strangely together?",
]

# ----------------------------
# 2) Tool definitions
# ----------------------------
# Each @tool function becomes something the agent can call during reasoning.
@tool
def consult_demogorgon(complaint: str) -> str:
    """Get the Demogorgon's perspective on a complaint about the Upside Down.

    The Demogorgon is a creature from the Upside Down. It might have insights
    about interdimensional inconsistencies, but its perspective is... unique.

    Args:
        complaint: The complaint about the Upside Down

    Returns:
        The Demogorgon's perspective (creative and possibly chaotic)
    """
    responses = [
        f"The Demogorgon tilts its head at '{complaint}'. Maybe the issue is trying to force three-dimensional logic on a shadow dimension.",
        f"The Demogorgon growls in agreement. It hints that time flows differently there, so consistency may look like chaos to us.",
        f"The Demogorgon ignores '{complaint}' and keeps hunting. It suggests consistency is not a priority in survival-first ecosystems.",
    ]
    return random.choice(responses)


@tool
def check_hawkins_records(query: str) -> str:
    """Search Hawkins historical records for information.

    Hawkins has a long history of strange occurrences. These records
    might contain clues about patterns or explanations.

    Args:
        query: What to search for in the records

    Returns:
        Information from Hawkins historical records
    """
    records = {
        "portal": (
            "Records show portals opened on multiple dates with no single trigger. "
            "Weather, electromagnetic spikes, and unknown events are recurring factors."
        ),
        "monsters": (
            "Historical notes indicate Upside Down creatures adapt behavior based on "
            "environment, fear response, and proximity to rifts."
        ),
        "psychics": (
            "Psychic abilities vary widely; emotional load and exhaustion strongly "
            "influence reliability and precision."
        ),
        "electricity": (
            "Hawkins has recurring electrical anomalies. Evidence suggests coupling "
            "between dimensional boundaries and local power fluctuations."
        ),
    }

    lower_query = query.lower()
    for key, value in records.items():
        if key in lower_query:
            return value

    return (
        f"No exact match for '{query}' in Hawkins records, but unresolved "
        "anomalies are repeatedly documented."
    )


@tool
def cast_interdimensional_spell(problem: str, creativity_level: str = "medium") -> str:
    """Suggest a creative interdimensional spell to fix a problem.

    Sometimes the best solution is a creative one that doesn't follow normal rules.
    This tool suggests imaginative fixes for Upside Down problems.

    Args:
        problem: The problem to solve
        creativity_level: How creative to be (low, medium, high)

    Returns:
        A creative spell or solution suggestion
    """
    level = creativity_level.lower().strip()
    creativity_multiplier = {"low": 1, "medium": 2, "high": 3}.get(level, 2)

    spells = [
        f"Chant 'Vecna Vecta Vector' three times while holding a Walkman to recalibrate dimensional static around: {problem}",
        f"Draw a salt circle with a compass at center to stabilize field distortion linked to: {problem}",
        f"Play 'Running Up That Hill' in reverse at the anomaly site to induce temporal resonance for: {problem}",
        f"Arrange a lighter, compass, and personal keepsake in a triangle to anchor intent and resolve: {problem}",
    ]

    selected = random.sample(spells, min(creativity_multiplier, len(spells)))
    return "\n".join(selected)


@tool
def gather_party_wisdom(question: str) -> str:
    """Ask the D&D party (Mike, Dustin, Lucas, Will) for their collective wisdom.

    The party has solved many mysteries together. Their combined knowledge
    and different perspectives can provide insights.

    Args:
        question: The question or problem to ask the party about

    Returns:
        The party's collective wisdom and suggestions
    """
    party_responses = {
        "portal": (
            "Mike: Portals cluster around intense events. Dustin: They may track Mind "
            "Flayer activity cycles."
        ),
        "monsters": (
            "Lucas: Demogorgons are opportunistic. Will: They react to fear and psychic noise."
        ),
        "psychics": (
            "Mike: Powers scale with focus. Dustin: Energy drain is a hard limit."
        ),
        "electricity": (
            "Lucas: The Upside Down disrupts circuits. Dustin: It behaves like a feedback loop."
        ),
    }

    lower_question = question.lower()
    for key, response in party_responses.items():
        if key in lower_question:
            return response

    return (
        "The party huddles up: Mike says map known clues, Dustin says test assumptions, "
        "Lucas says verify risks, and Will says trust pattern anomalies."
    )


def build_tools() -> list:
    """Return tools in one place so agent setup is easy to read/edit."""
    return [
        consult_demogorgon,
        check_hawkins_records,
        cast_interdimensional_spell,
        gather_party_wisdom,
    ]


# ----------------------------
# 3) Agent construction helpers
# ----------------------------
def build_agent_executor():
    """Create the LangChain 1.x agent executor (compiled graph)."""
    return create_agent(
        model="gpt-4o-mini",
        tools=build_tools(),
        system_prompt=CREATIVE_SYSTEM_PROMPT,
    )


def _extract_last_message_text(result: dict) -> str:
    """Get plain text from the agent result payload."""
    messages = result.get("messages", [])
    if not messages:
        return ""

    last = messages[-1]
    content = getattr(last, "content", "")
    if isinstance(content, list):
        return " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        ).strip()
    return str(content).strip()


def _extract_tool_calls(result: dict[str, Any]) -> list[str]:
    """Extract tool-call names from LangChain agent result messages."""
    tool_names: list[str] = []
    for message in result.get("messages", []):
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            continue
        for call in tool_calls:
            if isinstance(call, dict):
                name = call.get("name")
            else:
                name = getattr(call, "name", None)
            if name:
                tool_names.append(name)
    return tool_names


class ToolUsageTracker:
    """Track tool usage and chaining patterns for analysis."""

    def __init__(self, tools: list):
        self.usage_count = {tool.name: 0 for tool in tools}
        self.tool_sequences: list[str] = []
        self.complaint_chains: list[list[str]] = []

    def track_usage(self, tool_name: str) -> None:
        """Track one tool call."""
        if tool_name in self.usage_count:
            self.usage_count[tool_name] += 1
            self.tool_sequences.append(tool_name)

    def track_sequence(self, sequence: list[str]) -> None:
        """Track all tools used for one complaint in call order."""
        self.complaint_chains.append(sequence)
        for tool_name in sequence:
            self.track_usage(tool_name)

    def get_statistics(self) -> dict[str, Any]:
        """Return aggregate usage stats."""
        most_used = None
        if self.usage_count and any(count > 0 for count in self.usage_count.values()):
            most_used = max(self.usage_count.items(), key=lambda x: x[1])[0]
        return {
            "total_tool_calls": sum(self.usage_count.values()),
            "tool_counts": self.usage_count,
            "most_used": most_used,
            "tool_sequences": self.tool_sequences,
            "complaint_chains": self.complaint_chains,
        }


def _print_tool_analysis(stats: dict[str, Any]) -> None:
    """Print tracker stats and a quick agentic-vs-structured comparison."""
    print("\n=== Tool Usage Analysis ===")
    print(f"Total tool calls: {stats['total_tool_calls']}")
    print(f"Tool usage counts: {stats['tool_counts']}")
    print(f"Most used tool: {stats['most_used']}")

    print("\nTool chain examples:")
    chains = stats["complaint_chains"]
    for i, chain in enumerate(chains[:3], start=1):
        if chain:
            print(f"  Chain {i}: {' -> '.join(chain)}")
        else:
            print(f"  Chain {i}: (no tool calls)")

    print("\nAgentic vs structured approach:")
    print("  Agentic: chooses tools dynamically and can reorder/skip tools per complaint.")
    print("  Structured: follows fixed steps every time, easier to debug but less adaptive.")


def handle_complaint(agent_executor, complaint: str, tracker: ToolUsageTracker | None = None) -> str:
    """Handle a single complaint with the current agent executor."""
    print(f"\n{'=' * 60}")
    print(f"COMPLAINT: {complaint}")
    print(f"{'=' * 60}\n")

    result = agent_executor.invoke(
        {"messages": [{"role": "user", "content": complaint}]}
    )
    if tracker is not None:
        tracker.track_sequence(_extract_tool_calls(result))
    return _extract_last_message_text(result)


# ----------------------------
# 4) Program entry point
# ----------------------------
def main() -> int:
    # Load environment variables from .env (for OPENAI_API_KEY).
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("Missing OPENAI_API_KEY. Add it to your environment or .env file.")
        return 1

    # Show available tools so beginners can see what the agent can use.
    tools = build_tools()
    print(f"Created {len(tools)} creative tools:")
    for tool_fn in tools:
        print(f"  - {tool_fn.name}: {tool_fn.description[:60]}...")

    # Build the agent and ask one sample question.
    agent_executor = build_agent_executor()
    result = agent_executor.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": SAMPLE_USER_MESSAGE,
                }
            ]
        }
    )
    reply = _extract_last_message_text(result)

    print(f"User: {SAMPLE_USER_MESSAGE}")
    print(f"Assistant: {reply}")

    # Test the agent with sample complaints (first 2).
    tracker = ToolUsageTracker(tools)
    print("\nTesting agent with sample complaints...\n")
    for complaint in SAMPLE_COMPLAINTS[:2]:
        response = handle_complaint(agent_executor, complaint, tracker)
        print(f"\nRESPONSE: {response}\n")

    stats = tracker.get_statistics()
    _print_tool_analysis(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
