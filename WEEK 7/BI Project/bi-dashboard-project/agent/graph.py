from __future__ import annotations

from typing import Any, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:
    END = "__end__"
    START = "__start__"
    StateGraph = None

try:
    from .chains import format_agent_output, route_operational_question
    from .tools import (
        get_operational_analysis_builders,
        load_processed_data,
        summarize_operational_facts,
    )
except ImportError:
    from chains import format_agent_output, route_operational_question
    from tools import (
        get_operational_analysis_builders,
        load_processed_data,
        summarize_operational_facts,
    )


class AgentState(TypedDict, total=False):
    question: str
    route: str
    datasets: dict[str, Any]
    facts: dict[str, Any]
    tool_result: dict[str, Any]
    response: dict[str, Any]


def _prepare_context(state: AgentState) -> AgentState:
    return {
        "route": route_operational_question(state["question"]),
        "datasets": load_processed_data(),
        "facts": summarize_operational_facts(),
    }


def _make_tool_node(route_name: str):
    builders = get_operational_analysis_builders()
    builder = builders[route_name]

    def _node(state: AgentState) -> AgentState:
        return {
            "tool_result": builder(
                state["question"],
                state["datasets"],
                state["facts"],
            )
        }

    return _node


def _format_output(state: AgentState) -> AgentState:
    return {
        "response": format_agent_output(
            state["question"],
            state["facts"],
            state["tool_result"],
        )
    }


def _route_to_tool(state: AgentState) -> str:
    return state["route"]


def _build_fallback_response(question: str) -> dict[str, Any]:
    prepared = _prepare_context({"question": question})
    route = prepared["route"]
    tool_result = _make_tool_node(route)({
        "question": question,
        "datasets": prepared["datasets"],
        "facts": prepared["facts"],
        "route": route,
    })["tool_result"]
    return _format_output(
        {
            "question": question,
            "facts": prepared["facts"],
            "tool_result": tool_result,
        }
    )["response"]


def build_operational_graph():
    if StateGraph is None:
        return None

    graph = StateGraph(AgentState)
    graph.add_node("prepare_context", _prepare_context)
    graph.add_node("no_show", _make_tool_node("no_show"))
    graph.add_node("provider_utilization", _make_tool_node("provider_utilization"))
    graph.add_node("wait_times", _make_tool_node("wait_times"))
    graph.add_node("reminders", _make_tool_node("reminders"))
    graph.add_node("overview", _make_tool_node("overview"))
    graph.add_node("format_output", _format_output)

    graph.add_edge(START, "prepare_context")
    graph.add_conditional_edges(
        "prepare_context",
        _route_to_tool,
        {
            "no_show": "no_show",
            "provider_utilization": "provider_utilization",
            "wait_times": "wait_times",
            "reminders": "reminders",
            "overview": "overview",
        },
    )
    graph.add_edge("no_show", "format_output")
    graph.add_edge("provider_utilization", "format_output")
    graph.add_edge("wait_times", "format_output")
    graph.add_edge("reminders", "format_output")
    graph.add_edge("overview", "format_output")
    graph.add_edge("format_output", END)
    return graph.compile()


def run_operational_graph(question: str) -> dict[str, Any]:
    graph = build_operational_graph()
    if graph is None:
        return _build_fallback_response(question)

    result = graph.invoke({"question": question})
    return result["response"]
