from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from contextlib import contextmanager

import pandas as pd
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.qa import answer_question
from agent.tools import summarize_operational_facts
from langsmith_config import configure_langsmith

try:
    from langsmith import traceable
except ImportError:
    traceable = None


PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LANGSMITH_CONFIG = configure_langsmith()

DEFAULT_N8N_WEBHOOK_URL = os.getenv(
    "N8N_WORKFLOW_URL",
    "https://ai-experiementation.app.n8n.cloud/webhook/087b4a0f-3057-42bb-a250-b7f4cd13b6c6",
).strip()

app = FastAPI(title="HealthAI Clinic Dashboard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name)


def _read_markdown(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return pd.read_json(path, typ="series").to_dict()
    except Exception:
        import json
        return json.loads(path.read_text(encoding="utf-8"))


def _clean_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    cleaned = df.copy()
    cleaned = cleaned.where(pd.notnull(cleaned), None)
    return cleaned.to_dict(orient="records")


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return _clean_records(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


@contextmanager
def _suspend_background_tracing():
    previous_langsmith = os.environ.get("LANGSMITH_TRACING")
    previous_langchain = os.environ.get("LANGCHAIN_TRACING_V2")
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    try:
        yield
    finally:
        if previous_langsmith is None:
            os.environ.pop("LANGSMITH_TRACING", None)
        else:
            os.environ["LANGSMITH_TRACING"] = previous_langsmith
        if previous_langchain is None:
            os.environ.pop("LANGCHAIN_TRACING_V2", None)
        else:
            os.environ["LANGCHAIN_TRACING_V2"] = previous_langchain


def _build_trace_payload(question: str, source: str, result: dict[str, Any]) -> dict[str, Any]:
    evidence = list(result.get("evidence") or [])
    support_table = result.get("support_table")
    chart_data = result.get("chart_data")
    facts = result.get("facts") or {}

    return {
        "question": question,
        "trace_source": source,
        "route": result.get("route", "unknown"),
        "answer": str(result.get("answer", ""))[:1500],
        "recommendation": str(result.get("recommendation", ""))[:500],
        "evidence": evidence[:5],
        "chart_title": result.get("chart_title"),
        "chart_kind": result.get("chart_kind"),
        "support_table_rows": int(len(support_table)) if isinstance(support_table, pd.DataFrame) else len(support_table or []),
        "chart_points": int(len(chart_data)) if isinstance(chart_data, pd.DataFrame) else len(chart_data or []),
        "fact_sections": sorted(facts.keys()),
    }


if traceable is not None:

    @traceable(
        name="healthai_dashboard_question",
        project_name=LANGSMITH_CONFIG["project"],
    )
    def _trace_question(question: str, source: str, trace_payload: dict[str, Any]) -> dict[str, Any]:
        return trace_payload

else:

    def _trace_question(question: str, source: str, trace_payload: dict[str, Any]) -> dict[str, Any]:
        return trace_payload


def _impact_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "title": "Scenario: Smart Reminder Targeting",
            "subtitle": "Use risk scoring to target reminder timing and channels more precisely.",
            "tag": "Fast ROI",
            "icon": "🎯",
            "points": [
                {"label": "Current lost visits", "value": 2211, "fill": "#e55353"},
                {"label": "Recovered with targeting", "value": 420, "fill": "#14aab7"},
                {"label": "Operational follow-up", "value": 180, "fill": "#17b26a"},
            ],
        },
        {
            "title": "Scenario: Capacity Balancing",
            "subtitle": "Rebalance provider load using utilization and lead-time patterns.",
            "tag": "Ops Efficiency",
            "icon": "⚖️",
            "points": [
                {"label": "Overloaded provider-days", "value": 97, "fill": "#e55353"},
                {"label": "Balanced after rebooking", "value": 58, "fill": "#14aab7"},
                {"label": "Underused capacity captured", "value": 31, "fill": "#7c6cf2"},
            ],
        },
        {
            "title": "Scenario: Outreach Automation",
            "subtitle": "Use n8n to turn high-risk appointments into a real outreach queue.",
            "tag": "Workflow",
            "icon": "🤖",
            "points": [
                {"label": "High-risk queue", "value": 145, "fill": "#f59e0b"},
                {"label": "Auto-prepared reminders", "value": 118, "fill": "#14aab7"},
                {"label": "Escalated for human review", "value": 27, "fill": "#e55353"},
            ],
        },
    ]


def _use_case_comparison() -> list[dict[str, str]]:
    return [
        {
            "useCase": "No-show risk scoring",
            "aiType": "Classification + rules",
            "phiRisk": "Low",
            "roiSpeed": "Fast",
            "cost": "Low",
        },
        {
            "useCase": "Reminder prioritization",
            "aiType": "Agent + workflow",
            "phiRisk": "Low",
            "roiSpeed": "Fast",
            "cost": "Low",
        },
        {
            "useCase": "Provider capacity balancing",
            "aiType": "Analytics + optimization",
            "phiRisk": "Low",
            "roiSpeed": "Medium",
            "cost": "Medium",
        },
        {
            "useCase": "Operational copilot",
            "aiType": "LLM + retrieval",
            "phiRisk": "Medium",
            "roiSpeed": "Medium",
            "cost": "Medium",
        },
    ]


def build_dashboard_payload() -> dict[str, Any]:
    daily_kpis = _load_csv("daily_kpis.csv")
    no_show_patterns = _load_csv("no_show_patterns.csv")
    provider_utilization = _load_csv("provider_utilization.csv")
    reminder_effectiveness = _load_csv("reminder_effectiveness.csv")
    appointments = _load_csv("appointments_clean.csv")
    risk_report = _load_csv("daily_risk_report.csv") if (PROCESSED_DIR / "daily_risk_report.csv").exists() else pd.DataFrame()
    insights = _load_csv("agent_insights_latest.csv") if (PROCESSED_DIR / "agent_insights_latest.csv").exists() else pd.DataFrame()

    facts = summarize_operational_facts()
    latest_day = daily_kpis.sort_values("date").iloc[-1]
    monitoring_run = _read_json(PROJECT_ROOT / "langsmith" / "monitoring_results" / "latest_monitoring_run.json")

    return {
        "facts": facts,
        "summary": {
            "title": "Clinic Intelligence Dashboard",
            "subtitle": "Transparent analytics and AI-assisted operations for a medium-sized clinic.",
            "footer": {
                "left": "HealthAI · Clinic Intelligence Dashboard · March 2026",
                "middle": "Data: Synthetic · 1,000 appointments · Monitoring and workflow demo enabled",
                "right": "No PHI processed · For demonstration purposes",
            },
            "latestDate": str(latest_day["date"]),
        },
        "datasets": {
            "dailyKpis": _clean_records(daily_kpis),
            "noShowPatterns": _clean_records(no_show_patterns),
            "providerUtilization": _clean_records(provider_utilization),
            "reminderEffectiveness": _clean_records(reminder_effectiveness),
            "appointments": _clean_records(appointments),
            "riskReport": _clean_records(risk_report),
            "insights": _clean_records(insights),
        },
        "documents": {
            "workflowSummary": _read_markdown(PROJECT_ROOT / "n8n" / "workflow_documentation.md"),
            "monitoringSummary": _read_markdown(
                PROJECT_ROOT / "langsmith" / "monitoring_results" / "latest_monitoring_run.md"
            ),
            "costSummary": _read_markdown(PROJECT_ROOT / "cost_estimation" / "cost_analysis.md"),
            "timelineSummary": _read_markdown(PROJECT_ROOT / "cost_estimation" / "timeline_estimate.md"),
            "sourceSummary": _read_markdown(PROJECT_ROOT / "research" / "source_summary.md"),
        },
        "content": {
            "impactScenarios": _impact_scenarios(),
            "useCaseComparison": _use_case_comparison(),
            "workflowHandoff": [
                {
                    "step": "Insight",
                    "title": "High-risk appointment identified",
                    "body": "The dashboard or agent flags a high-risk appointment from the no-show risk layer.",
                },
                {
                    "step": "Decision",
                    "title": "Staff review the recommendation",
                    "body": "Clinic staff decide whether reminder outreach, follow-up, or manual escalation is appropriate.",
                },
                {
                    "step": "Workflow",
                    "title": "n8n prepares outreach",
                    "body": "The workflow prepares the reminder or follow-up message and routes it through Airtable, Gmail, or Telegram.",
                },
                {
                    "step": "Audit trail",
                    "title": "Communication is logged",
                    "body": "Delivery status and communication details are written back to Airtable for traceability and human review.",
                },
            ],
            "monitoringStatus": {
                "project": LANGSMITH_CONFIG["project"],
                "tracingEnabled": LANGSMITH_CONFIG["tracing"].lower() in {"1", "true", "yes", "on"},
                "endpoint": LANGSMITH_CONFIG["endpoint"],
                "dataset": monitoring_run.get("dataset_name", "BI Dashboard Project - Ops Insights Eval"),
                "experiment": monitoring_run.get("experiment_name", "not yet run"),
                "lastRunAt": monitoring_run.get("ran_at", "unknown"),
                "mode": monitoring_run.get("mode", "unknown"),
                "loggedFields": [
                    "user question input",
                    "routed analysis path",
                    "AI/generated response output",
                    "evaluation dataset and experiment metadata",
                ],
            },
            "oversightCards": [
                {
                    "icon": "👁️",
                    "title": "Every AI decision is logged",
                    "body": "LangSmith records model inputs, outputs, and evaluation traces for auditability.",
                    "variant": "teal",
                },
                {
                    "icon": "✋",
                    "title": "Human review remains in place",
                    "body": "The AI produces recommendations, while clinic staff retain operational control.",
                    "variant": "green",
                },
                {
                    "icon": "🔒",
                    "title": "Sensitive data handled with controls",
                    "body": "This proof of concept uses synthetic and de-identified operational data only.",
                    "variant": "amber",
                },
                {
                    "icon": "🚨",
                    "title": "Urgent cases always escalate",
                    "body": "High-risk or urgent situations route to staff review instead of silent automation.",
                    "variant": "purple",
                },
            ],
        },
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    return build_dashboard_payload()


@app.post("/api/ask")
def ask(payload: AskRequest) -> dict[str, Any]:
    with _suspend_background_tracing():
        result = answer_question(payload.question)
    result["trace_source"] = "react_dashboard"
    _trace_question(
        payload.question,
        "react_dashboard",
        _build_trace_payload(payload.question, "react_dashboard", result),
    )
    return _json_safe(result)


@app.post("/api/workflow/trigger")
def trigger_workflow(payload: AskRequest | None = None) -> dict[str, Any]:
    params = {
        "source": "HealthAI React Dashboard",
        "latest_question": payload.question if payload else "",
        "handoff_type": "high_risk_appointment",
    }
    try:
        response = requests.get(DEFAULT_N8N_WEBHOOK_URL, params=params, timeout=20)
        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "preview": response.text[:300].strip(),
        }
    except Exception as exc:
        return {"ok": False, "status_code": 500, "preview": str(exc)}
