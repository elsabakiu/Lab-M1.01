"""Run a demonstrable LangSmith monitoring flow for ClinicIQ."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from dataset_creation import create_dataset
from eval_dataset import EVALUATORS, EVAL_CASES
from langsmith_config import configure_langsmith

RESULTS_DIR = PROJECT_ROOT / "langsmith" / "monitoring_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

LANGSMITH_CONFIG = configure_langsmith()
DEFAULT_DATASET_NAME = os.getenv(
    "LANGSMITH_DATASET_NAME",
    f"{LANGSMITH_CONFIG['project']} - Ops Insights Eval",
)


def _metric_text(metric_name: str) -> str:
    return metric_name.replace("_", " ")


def _build_monitored_output(metrics: dict[str, Any], scenario: str = "") -> dict[str, Any]:
    no_show = metrics.get("no_show", {})
    patterns = metrics.get("no_show_patterns", {})
    provider = metrics.get("provider_utilization", {})
    wait_times = metrics.get("wait_times", {})
    reminder = metrics.get("reminder_effectiveness", {})

    if reminder:
        gap = float(reminder.get("reminder_effect_size", 0.0))
        title = "Improve reminder targeting and timing"
        finding = (
            f"Reminder performance in scenario '{scenario}' shows a {abs(gap):.1%} gap between "
            "reminder and no-reminder no-show rates."
        )
        action = (
            "Review reminder timing, segment high-risk appointments, and increase coverage only "
            "where reminder performance is measurable."
        )
        evidence = (
            f"Reminder no-show rate is {float(reminder.get('reminder_sent_no_show_rate', 0.0)):.1%} "
            f"versus {float(reminder.get('no_reminder_no_show_rate', 0.0)):.1%} without reminders."
        )
        affected = "reminder_effectiveness"
    elif provider:
        title = "Rebalance overloaded provider capacity"
        finding = (
            f"{float(provider.get('overloaded_share', 0.0)):.1%} of provider records are overloaded "
            f"in scenario '{scenario}'."
        )
        action = (
            "Redistribute bookings, protect overloaded specialties, and review provider-day load "
            "before adding more appointment volume."
        )
        evidence = (
            f"Top overloaded provider is {provider.get('top_overloaded_provider', 'unknown')} in "
            f"{provider.get('top_overloaded_specialty', 'unknown')}."
        )
        affected = "provider_utilization"
    elif wait_times:
        title = "Address high wait-time pressure"
        finding = (
            f"Wait times peak at {float(wait_times.get('peak_wait_time_min', 0.0)):.1f} minutes "
            f"in scenario '{scenario}'."
        )
        action = (
            "Review staffing on high-delay days, separate longer visits from quick-turn blocks, "
            "and monitor overload alongside wait time."
        )
        evidence = (
            f"Average wait time is {float(wait_times.get('average_wait_time_min', 0.0)):.1f} minutes "
            f"with {int(wait_times.get('anomalous_days_count', 0))} anomalous days."
        )
        affected = "avg_wait_time_min"
    else:
        weekday = patterns.get("peak_weekday", "unknown")
        specialty = patterns.get("peak_specialty", "unknown")
        title = "Reduce no-show friction in high-risk segments"
        finding = (
            f"No-shows in scenario '{scenario}' concentrate around {weekday} and {specialty}."
        )
        action = (
            "Review no-show segments weekly, prioritize outreach in the riskiest slots, and track "
            "improvement against the no-show KPI."
        )
        evidence = (
            f"Overall no-show rate is {float(no_show.get('overall_no_show_rate', 0.0)):.1%} and "
            f"peak no-show rate is {float(no_show.get('peak_no_show_rate', 0.0)):.1%}."
        )
        affected = "no_show_rate"

    output = {
        "title": title,
        "finding": finding,
        "evidence": evidence,
        "likely_cause": (
            "Operational performance varies across scheduling patterns, resource allocation, "
            "and reminder strategy."
        ),
        "recommended_action": action,
        "priority": "high" if any(metric for metric in [provider, reminder]) else "medium",
        "confidence": "medium",
        "affected_metric": affected,
        "scenario": scenario,
        "source_metrics": sorted(_metric_text(key) for key in metrics.keys()),
    }
    return output


def _run_local_monitoring() -> dict[str, Any]:
    results = []
    metric_scores: dict[str, list[float]] = {}

    for case in EVAL_CASES:
        output = _build_monitored_output(case["inputs"], case["scenario"])
        run = type("LocalRun", (), {"outputs": output})()
        example = type("LocalExample", (), {"outputs": {"expected": case["expected"]}})()

        evaluator_results = []
        for evaluator in EVALUATORS:
            result = evaluator(run, example)
            evaluator_results.append(result)
            metric_scores.setdefault(result["key"], []).append(float(result["score"]))

        results.append(
            {
                "case_id": case["id"],
                "scenario": case["scenario"],
                "output": output,
                "evaluations": evaluator_results,
            }
        )

    summary = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "mode": "local_monitoring",
        "case_count": len(results),
        "metric_averages": {
            key: round(sum(values) / len(values), 3) for key, values in metric_scores.items()
        },
        "results": results,
    }
    _write_results(summary)
    _write_markdown_summary(summary)
    return summary


def _run_langsmith_monitoring(dataset_name: str) -> dict[str, Any]:
    try:
        from langsmith import traceable
        from langsmith.evaluation import evaluate
    except ImportError:
        return _run_local_monitoring()

    @traceable(
        name="cliniciq_monitored_eval_target",
        project_name=LANGSMITH_CONFIG["project"],
    )
    def monitored_target(inputs: dict[str, Any]) -> dict[str, Any]:
        metrics = inputs.get("metrics", {})
        scenario = inputs.get("scenario", "")
        return _build_monitored_output(metrics, scenario)

    evaluation_results = evaluate(
        monitored_target,
        data=dataset_name,
        evaluators=EVALUATORS,
        experiment_prefix="bi-dashboard-monitoring",
    )
    result_repr = str(evaluation_results)
    experiment_name = result_repr.removeprefix("<ExperimentResults ").removesuffix(">")

    summary = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "mode": "langsmith",
        "dataset_name": dataset_name,
        "experiment_name": experiment_name,
        "results": result_repr,
    }
    _write_results(summary)
    _write_markdown_summary(summary)
    return summary


def setup_monitoring(dataset_name: str = DEFAULT_DATASET_NAME) -> dict[str, Any]:
    manifest = create_dataset(dataset_name)
    api_key = LANGSMITH_CONFIG["api_key"]

    if not api_key:
        summary = _run_local_monitoring()
        summary["dataset_manifest"] = manifest
        return summary

    try:
        summary = _run_langsmith_monitoring(dataset_name)
    except Exception as exc:
        summary = _run_local_monitoring()
        summary["langsmith_error"] = str(exc)

    summary["dataset_manifest"] = manifest
    _write_results(summary)
    _write_markdown_summary(summary)
    return summary


def _write_results(summary: dict[str, Any]) -> None:
    output_path = RESULTS_DIR / "latest_monitoring_run.json"
    output_path.write_text(json.dumps(summary, indent=2))


def _write_markdown_summary(summary: dict[str, Any]) -> None:
    lines = [
        "# Monitoring Run Summary",
        "",
        f"- Run time: `{summary.get('ran_at', 'unknown')}`",
        f"- Mode: `{summary.get('mode', 'unknown')}`",
    ]
    if "dataset_name" in summary:
        lines.append(f"- Dataset: `{summary['dataset_name']}`")
    if "experiment_name" in summary:
        lines.append(f"- Experiment: `{summary['experiment_name']}`")
    if "case_count" in summary:
        lines.append(f"- Cases evaluated: `{summary['case_count']}`")
    if "metric_averages" in summary:
        lines.append("- Average evaluator scores:")
        for key, value in summary["metric_averages"].items():
            lines.append(f"  - `{key}`: `{value}`")
    if "langsmith_error" in summary:
        lines.append(f"- LangSmith fallback reason: `{summary['langsmith_error']}`")
    if "dataset_manifest" in summary:
        lines.append(f"- Dataset status: `{summary['dataset_manifest'].get('status', 'unknown')}`")

    output_path = RESULTS_DIR / "latest_monitoring_run.md"
    output_path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    result = setup_monitoring()
    print(json.dumps(result, indent=2))
