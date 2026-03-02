from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from investment_agent.reporting import build_markdown_report, build_report_json
from investment_agent.schemas import ReportJSON
from investment_agent.state import AgentState
from investment_agent.strategies import MomentumStrategy, QualityStrategy
from investment_agent.tools.base import ToolResponse


@dataclass
class ToolBundle:
    market_data: Any
    fundamentals: Any
    news: Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _with_step(state: AgentState, step: str) -> AgentState:
    state.workflow_path.append(step)
    return state


def _fetch_with_log(
    state: AgentState, tool_name: str, fetch_fn: Any, request_payload: dict[str, Any]
) -> ToolResponse:
    started_at = _now_iso()
    response = fetch_fn()
    ended_at = _now_iso()
    state.tool_calls.append(
        {
            "tool": tool_name,
            "attempt": int(response.meta.retries) + 1,
            "started_at": started_at,
            "ended_at": ended_at,
            "ok": bool(response.meta.success),
            "request": request_payload,
            "response_summary": (
                "success"
                if response.meta.success
                else str(response.meta.error or "failed")
            ),
        }
    )
    return response


def _store_tool_result(state: AgentState, tool_name: str, response: ToolResponse) -> None:
    state.tool_health[tool_name] = response.meta.model_dump(mode="json")
    if response.meta.success and response.payload is not None:
        state.errors = [err for err in state.errors if not err.startswith(f"{tool_name}:")]
        if tool_name == "market_data":
            state.collected_market_data = response.payload
        elif tool_name == "fundamentals":
            state.collected_financials = response.payload
        elif tool_name == "news":
            state.collected_news = response.payload
        state.evidence_chunks.append(
            {
                "tool": tool_name,
                "endpoint": response.meta.endpoint,
                "requested_at": response.meta.requested_at,
                "status": "success",
            }
        )
    else:
        message = f"{tool_name}: {response.meta.error or 'failed'}"
        if message not in state.errors:
            state.errors.append(message)


def _count_collected(state: AgentState) -> int:
    return int(state.collected_market_data is not None) + int(
        state.collected_financials is not None
    ) + int(state.collected_news is not None)


def build_workflow(
    tools: ToolBundle,
    max_graph_retries: int = 1,
    max_react_iterations: int = 3,
):
    quality = QualityStrategy()
    momentum = MomentumStrategy()

    def validate_input(raw_state: dict[str, Any]) -> dict[str, Any]:
        state = _with_step(AgentState.model_validate(raw_state), "validate_input")
        ticker = state.ticker.strip().upper()
        state.ticker = ticker
        if not ticker or any(ch for ch in ticker if not (ch.isalnum() or ch in {".", "-"})):
            state.errors.append("validate_input: invalid ticker format")
            state.retries["validate_input"] = state.retries.get("validate_input", 0) + 1
        return state.model_dump(mode="json")

    def gather_data(raw_state: dict[str, Any]) -> dict[str, Any]:
        state = _with_step(AgentState.model_validate(raw_state), "gather_data")

        if state.collected_market_data is None:
            response = _fetch_with_log(
                state,
                "market_data",
                lambda: tools.market_data.fetch(state.ticker),
                {"ticker": state.ticker, "lookback_days": 365},
            )
            _store_tool_result(state, "market_data", response)
        if state.collected_financials is None:
            response = _fetch_with_log(
                state,
                "fundamentals",
                lambda: tools.fundamentals.fetch(state.ticker),
                {"ticker": state.ticker},
            )
            _store_tool_result(state, "fundamentals", response)
        if state.collected_news is None:
            response = _fetch_with_log(
                state,
                "news",
                lambda: tools.news.fetch(state.ticker),
                {"ticker": state.ticker, "lookback_days": 30},
            )
            _store_tool_result(state, "news", response)

        if _count_collected(state) < 2:
            state.retries["gather_data"] = state.retries.get("gather_data", 0) + 1

        state.confidence = min(1.0, 0.15 + (_count_collected(state) * 0.2))
        return state.model_dump(mode="json")

    def gather_route(raw_state: dict[str, Any]) -> str:
        state = AgentState.model_validate(raw_state)
        if any(err.startswith("validate_input") for err in state.errors):
            return "synthesize"

        collected = _count_collected(state)
        retries = state.retries.get("gather_data", 0)
        if collected >= 2:
            return "react_analysis"
        if retries <= max_graph_retries:
            return "gather_data"
        return "react_analysis"

    def react_analysis(raw_state: dict[str, Any]) -> dict[str, Any]:
        state = _with_step(AgentState.model_validate(raw_state), "react_analysis")

        def missing_tools() -> list[str]:
            missing = []
            if state.collected_market_data is None:
                missing.append("market_data")
            if state.collected_financials is None:
                missing.append("fundamentals")
            if state.collected_news is None:
                missing.append("news")
            return missing

        for i in range(max_react_iterations):
            need = missing_tools()
            if not need:
                state.react_trace.append(
                    {
                        "iteration": i + 1,
                        "time": _now_iso(),
                        "thought": "Sufficient evidence collected.",
                        "action": "stop",
                        "observation": "All required datasets available.",
                    }
                )
                break

            action = need[0]
            thought = f"Missing {', '.join(need)}. Fetch {action} next."
            if action == "market_data":
                response = _fetch_with_log(
                    state,
                    "market_data",
                    lambda: tools.market_data.fetch(state.ticker),
                    {"ticker": state.ticker, "lookback_days": 365},
                )
            elif action == "fundamentals":
                response = _fetch_with_log(
                    state,
                    "fundamentals",
                    lambda: tools.fundamentals.fetch(state.ticker),
                    {"ticker": state.ticker},
                )
            else:
                response = _fetch_with_log(
                    state,
                    "news",
                    lambda: tools.news.fetch(state.ticker),
                    {"ticker": state.ticker, "lookback_days": 30},
                )

            _store_tool_result(state, action, response)
            observation = (
                "tool succeeded"
                if response.meta.success
                else f"tool failed: {response.meta.error or 'unknown_error'}"
            )
            state.react_trace.append(
                {
                    "iteration": i + 1,
                    "time": _now_iso(),
                    "thought": thought,
                    "action": action,
                    "observation": observation,
                }
            )

            if _count_collected(state) >= 2:
                break

        if _count_collected(state) < 2:
            state.retries["react_analysis"] = state.retries.get("react_analysis", 0) + 1

        penalty = min(0.35, 0.05 * len(state.errors))
        state.confidence = max(0.0, min(1.0, 0.2 + (_count_collected(state) * 0.25) - penalty))
        return state.model_dump(mode="json")

    def react_route(raw_state: dict[str, Any]) -> str:
        state = AgentState.model_validate(raw_state)
        if _count_collected(state) == 0 and state.retries.get("react_analysis", 0) <= max_graph_retries:
            return "gather_data"
        return "score"

    def score(raw_state: dict[str, Any]) -> dict[str, Any]:
        state = _with_step(AgentState.model_validate(raw_state), "score")

        quality_result = quality.evaluate(state.collected_financials)
        momentum_result = momentum.evaluate(state.collected_market_data)

        state.scores[quality_result.name] = quality_result.score
        state.scores[momentum_result.name] = momentum_result.score
        state.score_explanations[quality_result.name] = quality_result.explanation
        state.score_explanations[momentum_result.name] = momentum_result.explanation
        state.score_factors[quality_result.name] = quality_result.factors
        state.score_factors[momentum_result.name] = momentum_result.factors
        state.score_notes[quality_result.name] = quality_result.notes
        state.score_notes[momentum_result.name] = momentum_result.notes

        if quality_result.score == 0 and momentum_result.score == 0:
            state.errors.append("score: no usable strategy inputs")

        return state.model_dump(mode="json")

    def synthesize(raw_state: dict[str, Any]) -> dict[str, Any]:
        state = _with_step(AgentState.model_validate(raw_state), "synthesize")
        report = build_report_json(state)
        state.report_json = report.model_dump(mode="json")
        return state.model_dump(mode="json")

    def write_report(raw_state: dict[str, Any]) -> dict[str, Any]:
        state = _with_step(AgentState.model_validate(raw_state), "write_report")
        report = ReportJSON.model_validate(state.report_json or build_report_json(state).model_dump())
        state.report_markdown = build_markdown_report(report, state)
        state.report_json = report.model_dump(mode="json")
        return state.model_dump(mode="json")

    def persist(raw_state: dict[str, Any]) -> dict[str, Any]:
        state = _with_step(AgentState.model_validate(raw_state), "persist")
        output_dir = Path(state.run_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "state.json").write_text(
            json.dumps(state.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        (output_dir / "report.json").write_text(
            json.dumps(state.report_json, indent=2),
            encoding="utf-8",
        )
        (output_dir / "report.md").write_text(state.report_markdown, encoding="utf-8")

        trace_lines = [f"# ReAct Trace: {state.ticker}", ""]
        if not state.react_trace:
            trace_lines.append("No ReAct iterations recorded.")
        else:
            for entry in state.react_trace:
                trace_lines.extend(
                    [
                        f"## Iteration {entry.get('iteration')}",
                        f"- Time: {entry.get('time')}",
                        f"- Thought: {entry.get('thought')}",
                        f"- Action: {entry.get('action')}",
                        f"- Observation: {entry.get('observation')}",
                        "",
                    ]
                )
        (output_dir / "react_trace.md").write_text("\n".join(trace_lines).strip() + "\n", encoding="utf-8")
        return state.model_dump(mode="json")

    graph = StateGraph(dict)
    graph.add_node("validate_input", validate_input)
    graph.add_node("gather_data", gather_data)
    graph.add_node("react_analysis", react_analysis)
    graph.add_node("score", score)
    graph.add_node("synthesize", synthesize)
    graph.add_node("write_report", write_report)
    graph.add_node("persist", persist)

    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "gather_data")
    graph.add_conditional_edges(
        "gather_data",
        gather_route,
        {
            "gather_data": "gather_data",
            "react_analysis": "react_analysis",
            "synthesize": "synthesize",
        },
    )
    graph.add_conditional_edges(
        "react_analysis",
        react_route,
        {
            "gather_data": "gather_data",
            "score": "score",
        },
    )
    graph.add_edge("score", "synthesize")
    graph.add_edge("synthesize", "write_report")
    graph.add_edge("write_report", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


def run_workflow(
    ticker: str,
    run_dir: Path,
    tools: ToolBundle,
    max_graph_retries: int = 1,
    max_react_iterations: int = 3,
    run_id: str = "",
    universe_id: str = "US_MegaCaps_v1",
    risk_profile: str = "balanced",
    quality_weight: float = 0.6,
    momentum_weight: float = 0.4,
    previous_total_score: float | None = None,
) -> AgentState:
    app = build_workflow(
        tools=tools,
        max_graph_retries=max_graph_retries,
        max_react_iterations=max_react_iterations,
    )
    initial = AgentState(
        ticker=ticker,
        run_dir=str(run_dir),
        run_id=run_id,
        universe_id=universe_id,
        risk_profile=risk_profile,
        quality_weight=quality_weight,
        momentum_weight=momentum_weight,
        previous_total_score=previous_total_score,
    ).model_dump(mode="json")
    final_state = app.invoke(initial)
    return AgentState.model_validate(final_state)
