from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv

from agent.qa import answer_question
from agent.tools import summarize_operational_facts
from dashboard.plotly_charts import (
    chart_no_show_by_specialty,
    chart_no_show_by_weekday,
    chart_no_show_trend,
    chart_provider_utilization_heatmap,
    chart_reminder_effectiveness,
    chart_risk_score_distribution,
    chart_roi_impact,
)


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

PRESET_QUESTIONS = [
    "Why are no-shows high on Mondays?",
    "Which providers are most overloaded?",
    "Are reminders improving attendance?",
    "What are the worst wait-time days?",
]

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "").strip()
AIRTABLE_APPOINTMENTS_TABLE = os.getenv("AIRTABLE_APPOINTMENTS_TABLE", "").strip()
AIRTABLE_COMMUNICATION_LOGS_TABLE = os.getenv("AIRTABLE_COMMUNICATION_LOGS_TABLE", "").strip()
DEFAULT_APPOINTMENTS_URL = os.getenv(
    "AIRTABLE_APPOINTMENTS_URL",
    "https://airtable.com/appqZYgYFZfGfdGK8/tblBkoJHIdBxGsGZU/viwwPy1Emh6iqcXO4?blocks=hide",
).strip()
DEFAULT_COMMUNICATION_LOGS_URL = os.getenv(
    "AIRTABLE_COMMUNICATION_LOGS_URL",
    "https://airtable.com/appqZYgYFZfGfdGK8/tblwXZ3zGBmONz89k/viwnu9rnpaUiXoG64?blocks=hide",
).strip()
DEFAULT_N8N_WEBHOOK_URL = os.getenv(
    "N8N_WORKFLOW_URL",
    "https://ai-experiementation.app.n8n.cloud/webhook/087b4a0f-3057-42bb-a250-b7f4cd13b6c6",
).strip()

REQUIRED_PROCESSED_FILES = [
    "appointments_clean.csv",
    "daily_kpis.csv",
    "no_show_patterns.csv",
    "provider_utilization.csv",
    "reminder_effectiveness.csv",
]


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap');

        :root {
            --bg: #f8fbfc;
            --panel: #ffffff;
            --panel-strong: #ffffff;
            --ink: #1b2b3a;
            --muted: #6b7a88;
            --line: rgba(186, 201, 214, 0.62);
            --accent: #14aab7;
            --accent-soft: #edf8fa;
            --accent-deep: #0f8b96;
            --alert: #e55353;
            --gold: #f59e0b;
        }

        html, body, [class*="css"] {
            font-family: "DM Sans", sans-serif;
        }

        #MainMenu, header, footer {
            display: none !important;
        }

        .stApp {
            background: var(--bg);
            color: var(--ink);
        }

        .block-container {
            max-width: 90rem;
            padding-top: 1.4rem;
            padding-bottom: 1.8rem;
        }

        .app-shell {
            padding: 0;
        }

        .hero {
            background: transparent;
            color: var(--ink);
            border-radius: 0;
            padding: 0;
            margin-bottom: 1rem;
            border: none;
        }

        .hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 10px;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent-deep);
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.9rem;
            border: 1px solid rgba(20, 170, 183, 0.18);
        }

        .hero-grid {
            display: grid;
            grid-template-columns: 1.35fr 0.9fr;
            gap: 1rem;
            align-items: start;
        }

        .hero-title {
            font-size: 2.35rem;
            line-height: 1.05;
            font-weight: 700;
            margin: 0 0 0.45rem 0;
            letter-spacing: -0.04em;
        }

        .hero-subtitle {
            color: var(--muted);
            font-size: 0.98rem;
            line-height: 1.6;
            max-width: 44rem;
        }

        .hero-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 18px;
        }

        .hero-chip {
            border-radius: 999px;
            background: #ffffff;
            border: 1px solid var(--line);
            color: var(--muted);
            padding: 0.5rem 0.75rem;
            font-size: 0.8rem;
            font-weight: 500;
        }

        .hero-note {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 1rem;
            padding: 1rem;
            box-shadow: 0 10px 24px rgba(32, 65, 92, 0.06);
        }

        .hero-note-label {
            color: var(--accent-deep);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }

        .hero-note h4 {
            margin: 0 0 0.4rem 0;
            font-size: 1rem;
        }

        .hero-note p {
            margin: 0;
            color: var(--muted);
            line-height: 1.55;
            font-size: 0.86rem;
        }

        .metric-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 1rem;
            padding: 1rem;
            box-shadow: 0 10px 24px rgba(32, 65, 92, 0.05);
            min-height: 118px;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 12px;
        }

        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            letter-spacing: -0.04em;
            color: var(--ink);
            margin-bottom: 0.55rem;
        }

        .metric-delta {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .metric-delta.good {background: #ecfbf7; color: #169b76;}
        .metric-delta.warn {background: #fff3f3; color: #d94a4a;}
        .metric-delta.note {background: #fff7e7; color: #c28b11;}

        .metric-footnote {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.45;
        }

        .panel-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 1rem;
            padding: 18px;
            box-shadow: 0 10px 24px rgba(32, 65, 92, 0.05);
            height: 100%;
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: flex-start;
            margin-bottom: 14px;
        }

        .panel-eyebrow {
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .panel-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: var(--ink);
            margin-top: 3px;
            letter-spacing: -0.03em;
        }

        .panel-copy {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.5;
            margin-top: 6px;
        }

        .insight-card {
            background: var(--panel-strong);
            border: 1px solid var(--line);
            border-radius: 0.95rem;
            padding: 14px;
            margin-bottom: 12px;
        }

        .insight-top {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: start;
            margin-bottom: 8px;
        }

        .insight-title {
            font-weight: 700;
            color: var(--ink);
            font-size: 0.92rem;
            line-height: 1.35;
        }

        .insight-badge {
            white-space: nowrap;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.74rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .insight-badge.high {background: #fde9e2; color: #b64f2e;}
        .insight-badge.medium {background: #f7efd9; color: #896918;}
        .insight-badge.low {background: #e6f5ee; color: #237656;}

        .insight-meta {
            color: var(--muted);
            font-size: 0.84rem;
            margin-bottom: 8px;
        }

        .insight-body {
            color: var(--ink);
            font-size: 0.93rem;
            line-height: 1.55;
        }

        .insight-action {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px dashed var(--line);
            color: var(--accent-deep);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .mini-stat-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
        }

        .mini-stat {
            background: var(--panel-strong);
            border: 1px solid var(--line);
            border-radius: 0.9rem;
            padding: 14px;
        }

        .mini-stat-label {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .mini-stat-value {
            color: var(--ink);
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: -0.03em;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: #ffffff;
            padding: 6px;
            border-radius: 0.9rem;
            border: 1px solid var(--line);
            margin: 0.5rem 0 1rem 0;
        }

        .stTabs [data-baseweb="tab"] {
            height: 40px;
            border-radius: 0.75rem;
            color: var(--muted);
            font-weight: 500;
            padding: 0 16px;
        }

        .stTabs [aria-selected="true"] {
            background: var(--accent-soft) !important;
            color: var(--accent-deep) !important;
        }

        .stChatMessage {
            background: var(--panel-strong);
            border: 1px solid var(--line);
            border-radius: 0.9rem;
        }

        .stButton > button, .stLinkButton > a {
            border-radius: 0.85rem !important;
            border: 1px solid var(--line) !important;
            background: var(--panel-strong) !important;
            color: var(--ink) !important;
            font-weight: 500 !important;
            box-shadow: none !important;
        }

        .stButton > button:hover, .stLinkButton > a:hover {
            border-color: rgba(20, 170, 183, 0.35) !important;
            color: var(--accent-deep) !important;
            background: var(--accent-soft) !important;
        }

        .stChatInputContainer {
            border-top: none !important;
        }

        [data-testid="stDataFrame"] {
            border-radius: 0.9rem;
            overflow: hidden;
        }

        .footer-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            border-top: 1px solid var(--line);
            margin-top: 1.25rem;
            padding-top: 0.9rem;
            color: var(--muted);
            font-size: 0.68rem;
            font-family: "DM Mono", monospace;
        }

        .footer-strip div:last-child {
            text-align: right;
        }

        @media (max-width: 980px) {
            .hero-grid {
                grid-template-columns: 1fr;
            }

            .mini-stat-grid {
                grid-template-columns: 1fr;
            }

            .footer-strip {
                grid-template-columns: 1fr;
            }

            .footer-strip div:last-child {
                text-align: left;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _airtable_ready(table_name: str) -> bool:
    return bool(AIRTABLE_TOKEN and AIRTABLE_BASE_ID and table_name)


def _fetch_airtable_table(table_name: str) -> pd.DataFrame | None:
    if not _airtable_ready(table_name):
        return None

    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    rows: list[dict[str, object]] = []
    offset = None

    try:
        for _ in range(10):
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
            for record in payload.get("records", []):
                row = {"record_id": record.get("id")}
                row.update(record.get("fields", {}))
                rows.append(row)
            offset = payload.get("offset")
            if not offset:
                break
    except Exception:
        return None

    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROJECT_ROOT / "data" / "processed" / name)


def _missing_processed_files() -> list[str]:
    processed_dir = PROJECT_ROOT / "data" / "processed"
    return [name for name in REQUIRED_PROCESSED_FILES if not (processed_dir / name).exists()]


def _render_setup_instructions(missing_files: list[str]) -> None:
    st.error("The processed dashboard files are missing, so the workspace cannot load yet.")
    st.markdown(
        "Run the setup steps from the project root, then refresh this page:\n"
        "1. `python data/data_prep.py`\n"
        "2. `python agent/run_agent.py`"
    )
    st.caption(f"Missing files: {', '.join(missing_files)}")


def _load_recommendations() -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "processed" / "agent_insights_latest.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def _load_markdown(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _figure_demand_vs_completed() -> go.Figure:
    daily = _load_csv("daily_kpis.csv").copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily[daily["date"] != pd.Timestamp("2016-05-14")].sort_values("date")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["total_appointments"],
            mode="lines",
            name="Booked appointments",
            line=dict(color="#0d8f72", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["attended_appointments"],
            mode="lines",
            name="Completed visits",
            line=dict(color="#c7912f", width=2.5),
        )
    )
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Manrope, sans-serif", color="#1c241f"),
        margin=dict(l=16, r=16, t=48, b=16),
        title="Appointment demand vs completed visits",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="", gridcolor="rgba(68, 83, 73, 0.10)"),
        yaxis=dict(title="", gridcolor="rgba(68, 83, 73, 0.10)"),
    )
    return fig


def _figure_no_show_heatmap() -> go.Figure:
    patterns = _load_csv("no_show_patterns.csv").copy()
    heat = (
        patterns.groupby(["weekday", "hour"], as_index=False)
        .agg(no_show_count=("no_show_count", "sum"), total_appointments=("total_appointments", "sum"))
        .assign(no_show_rate=lambda df: df["no_show_count"] / df["total_appointments"])
    )
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    pivot = (
        heat.pivot(index="weekday", columns="hour", values="no_show_rate")
        .reindex(weekday_order)
        .fillna(0)
    )
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=[f"{int(hour)}:00" for hour in pivot.columns.tolist()],
            y=pivot.index.tolist(),
            colorscale=[[0, "#e8f8f4"], [0.5, "#7ad1bc"], [1, "#d95d39"]],
            text=[[f"{value:.0%}" for value in row] for row in pivot.values],
            texttemplate="%{text}",
            hovertemplate="Day: %{y}<br>Hour: %{x}<br>No-show rate: %{z:.1%}<extra></extra>",
            colorbar=dict(tickformat=".0%", title="No-show"),
        )
    )
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Manrope, sans-serif", color="#1c241f"),
        margin=dict(l=16, r=16, t=48, b=16),
        title="No-show hotspots by day and hour",
        xaxis=dict(title=""),
        yaxis=dict(title=""),
    )
    return fig


def _figure_lead_time_by_specialty() -> go.Figure:
    appointments = _load_csv("appointments_clean.csv").copy()
    lead_time = (
        appointments.groupby("specialty", as_index=False)
        .agg(
            avg_lead_time_days=("lead_time_days", "mean"),
            appointments=("appointment_id", "count"),
        )
        .sort_values("avg_lead_time_days", ascending=False)
    )
    fig = px.bar(
        lead_time,
        x="avg_lead_time_days",
        y="specialty",
        orientation="h",
        color="appointments",
        color_continuous_scale=["#dff5ec", "#0d8f72"],
        title="Average lead time by specialty",
        labels={"avg_lead_time_days": "Days from booking to appointment", "specialty": ""},
    )
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Manrope, sans-serif", color="#1c241f"),
        margin=dict(l=16, r=16, t=48, b=16),
        coloraxis_colorbar_title="Volume",
        yaxis=dict(categoryorder="total ascending"),
        xaxis=dict(gridcolor="rgba(68, 83, 73, 0.10)"),
    )
    return fig


def _run_question(question_text: str) -> None:
    cleaned = question_text.strip()
    if not cleaned:
        return
    st.session_state.messages.append({"role": "user", "content": cleaned})
    with st.spinner("Analyzing clinic operations..."):
        result = answer_question(cleaned)
    st.session_state.messages.append({"role": "assistant", "content": result})


def _trigger_n8n_workflow() -> tuple[bool, str]:
    payload = {
        "source": "ClinicIQ Streamlit Workspace",
        "triggered_at": pd.Timestamp.utcnow().isoformat(),
        "latest_question": "",
    }
    for message in reversed(st.session_state.messages):
        if message["role"] == "user":
            payload["latest_question"] = message["content"]
            break

    try:
        response = requests.get(DEFAULT_N8N_WEBHOOK_URL, params=payload, timeout=20)
        preview = response.text[:300].strip()
        if response.ok:
            return True, preview or "Workflow accepted."
        return False, f"HTTP {response.status_code}: {preview}"
    except Exception as exc:
        return False, str(exc)


def _render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">HealthAI</div>
            <div class="hero-grid">
                <div>
                    <div class="hero-title">Clinic Intelligence Dashboard</div>
                    <div class="hero-subtitle">
                        Transparent analytics and AI-assisted operations for a medium-sized clinic.
                        Review performance, identify access pressure, and show where AI can create
                        measurable value without touching clinical judgment.
                    </div>
                    <div class="hero-chip-row">
                        <div class="hero-chip">Healthcare SME</div>
                        <div class="hero-chip">Synthetic dataset</div>
                        <div class="hero-chip">AI transparency</div>
                        <div class="hero-chip">March 2026 demo</div>
                    </div>
                </div>
                <div class="hero-note">
                    <div class="hero-note-label">How to read this</div>
                    <h4>Start with the top tabs.</h4>
                    <p>Move from executive summary to scheduling pressure to AI opportunities. The page is designed to read like a CEO meeting flow.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_section_header(eyebrow: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="panel-header">
            <div>
                <div class="panel-eyebrow">{eyebrow}</div>
                <div class="panel-title">{title}</div>
                <div class="panel-copy">{copy}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_metric_card(label: str, value: str, delta: str, tone: str, footnote: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-delta {tone}">{delta}</div>
            <div class="metric-footnote">{footnote}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_status_strip(facts: dict[str, object]) -> None:
    cols = st.columns(4)
    with cols[0]:
        _render_metric_card(
            "No-show rate",
            f"{facts['no_show']['overall_no_show_rate']:.1%}",
            f"Peak day {facts['no_show']['peak_no_show_rate']:.1%}",
            "warn",
            "Use this as the headline indicator for scheduling friction and missed revenue.",
        )
    with cols[1]:
        _render_metric_card(
            "Average wait time",
            f"{facts['wait_times']['average_wait_time_min']:.1f} min",
            f"{facts['wait_times']['anomalous_days_count']} high-delay days",
            "warn",
            "Long waits usually signal a combination of provider overload and afternoon demand.",
        )
    with cols[2]:
        _render_metric_card(
            "Overloaded provider share",
            f"{facts['provider_utilization']['overloaded_share']:.1%}",
            f"Top strain: {facts['provider_utilization']['top_overloaded_specialty']}",
            "note",
            "This is the best single metric for whether clinic capacity is balanced or brittle.",
        )
    with cols[3]:
        reminder_gap = facts["reminder_effectiveness"]["reminder_effect_size"]
        _render_metric_card(
            "Reminder gap",
            f"{abs(reminder_gap):.1%}",
            f"With reminder: {facts['reminder_effectiveness']['reminder_sent_no_show_rate']:.1%}",
            "good" if reminder_gap > 0 else "warn",
            "Read this alongside targeting logic so you do not confuse correlation with operational impact.",
        )


def _priority_class(priority: str) -> str:
    lowered = str(priority).lower()
    return lowered if lowered in {"high", "medium", "low"} else "low"


def _render_insight_cards(recs: pd.DataFrame, limit: int = 3) -> None:
    if recs.empty:
        st.info("Run `python agent/run_agent.py` to generate the latest AI recommendations.")
        return

    for _, row in recs.head(limit).iterrows():
        priority = str(row.get("priority", "low")).title()
        badge_class = _priority_class(priority)
        st.markdown(
            f"""
            <div class="insight-card">
                <div class="insight-top">
                    <div class="insight-title">{row.get('title', 'Insight')}</div>
                    <div class="insight-badge {badge_class}">{priority} priority</div>
                </div>
                <div class="insight-meta">{str(row.get('affected_metric', '')).replace('_', ' ').title()}</div>
                <div class="insight-body">{row.get('finding', '')}</div>
                <div class="insight-action"><strong>Recommended action:</strong> {row.get('recommended_action', '')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_plotly_card(title: str, description: str, figure) -> None:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    _render_section_header("Visual analysis", title, description)
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def _render_overview_snapshot(facts: dict[str, object]) -> None:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    _render_section_header(
        "Executive summary",
        "Operational snapshot",
        "A quick read on the clinic’s current pressure points so non-technical stakeholders can orient themselves in under a minute.",
    )
    st.markdown(
        f"""
        <div class="mini-stat-grid">
            <div class="mini-stat">
                <div class="mini-stat-label">Worst hotspot</div>
                <div class="mini-stat-value">{facts['no_show_patterns']['peak_hotspot_weekday']} {facts['no_show_patterns']['peak_hotspot_hour']}:00</div>
            </div>
            <div class="mini-stat">
                <div class="mini-stat-label">Highest-risk specialty</div>
                <div class="mini-stat-value">{facts['no_show_patterns']['peak_hotspot_specialty']}</div>
            </div>
            <div class="mini-stat">
                <div class="mini-stat-label">Top overloaded provider</div>
                <div class="mini-stat-value">{facts['provider_utilization']['top_overloaded_provider']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_access_snapshot() -> None:
    appointments = _load_csv("appointments_clean.csv")
    provider = _load_csv("provider_utilization.csv")

    avg_lead_time = appointments["lead_time_days"].mean()
    high_pressure_days = int((provider["utilization_status"] == "Overloaded").sum())
    avg_utilization = provider["utilization_rate"].mean()

    st.markdown(
        f"""
        <div class="mini-stat-grid">
            <div class="mini-stat">
                <div class="mini-stat-label">Average lead time</div>
                <div class="mini-stat-value">{avg_lead_time:.1f} days</div>
            </div>
            <div class="mini-stat">
                <div class="mini-stat-label">Overloaded provider-days</div>
                <div class="mini-stat-value">{high_pressure_days}</div>
            </div>
            <div class="mini-stat">
                <div class="mini-stat-label">Average utilization</div>
                <div class="mini-stat-value">{avg_utilization:.0%}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_impact_snapshot() -> None:
    risk_path = PROJECT_ROOT / "data" / "processed" / "daily_risk_report.csv"
    risk_df = pd.read_csv(risk_path) if risk_path.exists() else pd.DataFrame()
    workflow_doc = _load_markdown(PROJECT_ROOT / "n8n" / "workflow_documentation.md")
    langsmith_summary = _load_markdown(
        PROJECT_ROOT / "langsmith" / "monitoring_results" / "latest_monitoring_run.md"
    )

    high_risk = int((risk_df["Risk Tier"] == "High").sum()) if not risk_df.empty else 0
    monitored_cases = len(risk_df) if not risk_df.empty else 15

    st.markdown(
        f"""
        <div class="mini-stat-grid">
            <div class="mini-stat">
                <div class="mini-stat-label">High-risk appointments today</div>
                <div class="mini-stat-value">{high_risk}</div>
            </div>
            <div class="mini-stat">
                <div class="mini-stat-label">Monitored evaluation cases</div>
                <div class="mini-stat-value">{monitored_cases}</div>
            </div>
            <div class="mini-stat">
                <div class="mini-stat-label">Automation readiness</div>
                <div class="mini-stat-value">Workflow ready</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Workflow summary", expanded=False):
        st.markdown(workflow_doc or "Workflow documentation not found.")
    with st.expander("Latest LangSmith monitoring summary", expanded=False):
        st.markdown(langsmith_summary or "Monitoring summary not found.")


def _render_chat_panel() -> None:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    _render_section_header(
        "Clinic Intelligence Agent",
        "Ask about the clinic's operations & data",
        "This mirrors the prototype's assistant layer and lets you move from dashboard summaries into supporting evidence.",
    )

    if not st.session_state.messages:
        st.info(
            "Ask about no-shows, provider utilization, reminder effectiveness, wait-time spikes, or next-step recommendations."
        )

    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            result = message["content"]
            with st.chat_message("assistant"):
                st.write(result["answer"])
                st.caption("Evidence")
                for line in result["evidence"]:
                    st.write(f"- {line}")
                st.caption("Recommended Action")
                st.write(result["recommendation"])
                support_table = result.get("support_table")
                if isinstance(support_table, pd.DataFrame):
                    with st.expander("Supporting Data"):
                        st.dataframe(support_table, width="stretch")

    st.caption("Suggested prompts")
    prompt_cols = st.columns(2)
    for index, prompt in enumerate(PRESET_QUESTIONS):
        with prompt_cols[index % 2]:
            if st.button(prompt, key=f"prompt_{index}", width="stretch"):
                _run_question(prompt)
                st.rerun()

    question = st.chat_input("Ask about clinic operations...")
    if question:
        _run_question(question)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_footer() -> None:
    st.markdown(
        """
        <div class="footer-strip">
            <div>HealthAI · Clinic Intelligence Dashboard · March 2026</div>
            <div>Data: Synthetic · 1,000 appointments · Monitoring and workflow demo enabled</div>
            <div>No PHI processed · For demonstration purposes</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_dashboard_tab(facts: dict[str, object]) -> None:
    top_left, top_right = st.columns([1.22, 0.92])
    with top_left:
        _render_plotly_card(
            "No-show trend over time",
            "The strongest executive trend line for showing operational consistency and missed-demand risk.",
            chart_no_show_trend(),
        )
    with top_right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        _render_section_header(
            "Action queue",
            "Top recommended next steps",
            "A short list of the most useful actions to discuss in the meeting before diving into the detailed charts.",
        )
        _render_insight_cards(_load_recommendations())
        st.markdown("</div>", unsafe_allow_html=True)

    mid_left, mid_right = st.columns(2)
    with mid_left:
        _render_plotly_card(
            "No-show pattern by weekday",
            "This helps stakeholders see whether the issue is systemic or concentrated into a few recurring time windows.",
            chart_no_show_by_weekday(),
        )
    with mid_right:
        _render_plotly_card(
            "Reminder effectiveness",
            "Compare attendance and no-show performance for reminder versus no-reminder segments.",
            chart_reminder_effectiveness(),
        )

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        _render_plotly_card(
            "No-show rate by specialty",
            "Use this to explain where targeted interventions should start instead of spreading effort evenly.",
            chart_no_show_by_specialty(),
        )
    with bottom_right:
        _render_plotly_card(
            "Provider utilization heatmap",
            "A cleaner capacity view that makes overloaded specialties easier to spot at a glance.",
            chart_provider_utilization_heatmap(),
        )

    lower_left, lower_right = st.columns([0.95, 1.05])
    with lower_left:
        _render_overview_snapshot(facts)
    with lower_right:
        _render_plotly_card(
            "Estimated commercial upside",
            "A board-friendly value frame for discussing why operational AI is worth piloting.",
            chart_roi_impact(),
        )


def _render_executive_tab(facts: dict[str, object]) -> None:
    top_left, top_right = st.columns([1.18, 0.82])
    with top_left:
        _render_plotly_card(
            "No-show trend over time",
            "The best single chart for explaining the operational cost of missed appointments to leadership.",
            chart_no_show_trend(),
        )
    with top_right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        _render_section_header(
            "Executive summary",
            "Top AI recommendations",
            "A short, high-signal action list for Chloe before getting into operational detail.",
        )
        _render_insight_cards(_load_recommendations())
        st.markdown("</div>", unsafe_allow_html=True)

    mid_left, mid_right = st.columns(2)
    with mid_left:
        _render_plotly_card(
            "No-show rate by specialty",
            "Use specialty as the operating lens for where targeted intervention should begin.",
            chart_no_show_by_specialty(),
        )
    with mid_right:
        _render_plotly_card(
            "Reminder effectiveness",
            "This compares attendance performance between reminder and no-reminder cohorts.",
            chart_reminder_effectiveness(),
        )

    bottom_left, bottom_right = st.columns([0.95, 1.05])
    with bottom_left:
        _render_overview_snapshot(facts)
    with bottom_right:
        _render_plotly_card(
            "Estimated commercial upside",
            "These are modeled gains, included to frame the value of a focused operational AI pilot.",
            chart_roi_impact(),
        )


def _render_access_tab(facts: dict[str, object]) -> None:
    top_left, top_right = st.columns([1.05, 0.95])
    with top_left:
        _render_plotly_card(
            "Appointment demand vs completed visits",
            "Demand is not the same as realized care. This gap is the clearest sign of scheduling pressure.",
            _figure_demand_vs_completed(),
        )
    with top_right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        _render_section_header(
            "Pressure snapshot",
            "How access friction shows up in the data",
            "This tab focuses on where demand, lead time, no-shows, and capacity strain cluster together.",
        )
        _render_access_snapshot()
        st.markdown(
            f"""
            <div class="insight-card">
                <div class="insight-title">Hotspot to watch</div>
                <div class="insight-body">
                    {facts['no_show_patterns']['peak_hotspot_weekday']} at {facts['no_show_patterns']['peak_hotspot_hour']}:00
                    in {facts['no_show_patterns']['peak_hotspot_specialty']} is the most concentrated no-show window in the current dataset.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    mid_left, mid_right = st.columns(2)
    with mid_left:
        _render_plotly_card(
            "No-show hotspots by day and hour",
            "This is the clearest operational view for when reminder timing and outreach prioritization should change.",
            _figure_no_show_heatmap(),
        )
    with mid_right:
        _render_plotly_card(
            "Provider utilization heatmap",
            "A specialty-level capacity map for spotting recurring overload instead of one-off busy days.",
            chart_provider_utilization_heatmap(),
        )

    lower_left, lower_right = st.columns(2)
    with lower_left:
        _render_plotly_card(
            "Average lead time by specialty",
            "Use this when the discussion shifts from in-clinic waiting to days between booking and appointment.",
            _figure_lead_time_by_specialty(),
        )
    with lower_right:
        _render_plotly_card(
            "No-show pattern by weekday",
            "This keeps the day-of-week story simple for leadership before drilling into hours and specialties.",
            chart_no_show_by_weekday(),
        )


def _render_impact_tab() -> None:
    risk_chart = chart_risk_score_distribution()
    top_left, top_right = st.columns([1.05, 0.95])
    with top_left:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        _render_section_header(
            "AI opportunities",
            "Where AI creates practical value for the clinic",
            "The goal is not to automate clinical judgment. It is to support operational decisions with clearer prioritization and faster follow-through.",
        )
        _render_impact_snapshot()
        st.markdown("</div>", unsafe_allow_html=True)
    with top_right:
        if risk_chart is not None:
            _render_plotly_card(
                "Today's no-show risk distribution",
                "This turns the AI layer into something inspectable: each appointment gets a visible risk score and tier.",
                risk_chart,
            )
        else:
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            _render_section_header(
                "Transparency",
                "No risk distribution available yet",
                "Generate the daily risk file to show how appointment-level scoring is monitored and surfaced to operations teams.",
            )
            st.info("Run `python agent/run_daily_risk.py` to populate the risk distribution view.")
            st.markdown("</div>", unsafe_allow_html=True)

    lower_left, lower_right = st.columns([1.05, 0.95])
    with lower_left:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        _render_section_header(
            "Risk board",
            "High-priority outreach queue",
            "This is the handoff point between analytics and action for the operations team.",
        )
        risk_path = PROJECT_ROOT / "data" / "processed" / "daily_risk_report.csv"
        if risk_path.exists():
            risk_df = pd.read_csv(risk_path)
            st.dataframe(risk_df.head(12), width="stretch", hide_index=True)
        else:
            st.info("Run `python agent/run_daily_risk.py` to generate the daily risk board.")
        st.markdown("</div>", unsafe_allow_html=True)
    with lower_right:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        _render_section_header(
            "Workflow handoff",
            "Trigger the n8n workflow",
            "Once a high-risk pattern is identified, the workflow closes the loop with reminders and follow-up actions.",
        )
        st.code(DEFAULT_N8N_WEBHOOK_URL, language="text")
        if st.button("Run n8n Workflow", width="stretch"):
            success, message = _trigger_n8n_workflow()
            st.session_state.workflow_status = (success, message)
        status = st.session_state.get("workflow_status")
        if status:
            success, message = status
            if success:
                st.success(f"Workflow triggered. Response: {message}")
            else:
                st.error(f"Workflow trigger failed: {message}")
        st.markdown("</div>", unsafe_allow_html=True)


def _render_risk_tab() -> None:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    _render_section_header(
        "Risk board",
        "Daily no-show prioritization",
        "This view turns the model output into a practical outreach queue for operations staff.",
    )

    risk_path = PROJECT_ROOT / "data" / "processed" / "daily_risk_report.csv"
    if not risk_path.exists():
        st.info("Run `python agent/run_daily_risk.py` to generate the daily risk board.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    risk_df = pd.read_csv(risk_path)
    risk_chart = chart_risk_score_distribution()
    top_left, top_right = st.columns([0.95, 1.05])
    with top_left:
        high_count = int((risk_df["Risk Tier"] == "High").sum())
        medium_count = int((risk_df["Risk Tier"] == "Medium").sum())
        st.markdown(
            f"""
            <div class="mini-stat-grid">
                <div class="mini-stat">
                    <div class="mini-stat-label">Appointments scored</div>
                    <div class="mini-stat-value">{len(risk_df)}</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-label">High risk</div>
                    <div class="mini-stat-value">{high_count}</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-label">Medium risk</div>
                    <div class="mini-stat-value">{medium_count}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_right:
        if risk_chart is not None:
            st.plotly_chart(risk_chart, use_container_width=True, config={"displayModeBar": False})

    st.dataframe(risk_df, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_appointments_tab() -> None:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    _render_section_header(
        "Operations data",
        "Appointment activity",
        "Browse the underlying appointment mix to validate that the operational story matches the source records.",
    )

    airtable_df = _fetch_airtable_table(AIRTABLE_APPOINTMENTS_TABLE)
    if airtable_df is not None and not airtable_df.empty:
        st.success("Loaded live Airtable appointments data.")
        st.dataframe(airtable_df, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    appointments = _load_csv("appointments_clean.csv")
    top_left, top_right = st.columns(2)
    with top_left:
        weekday = (
            appointments.groupby("weekday", as_index=False)["appointment_id"]
            .count()
            .rename(columns={"appointment_id": "appointments"})
            .set_index("weekday")
        )
        st.bar_chart(weekday, width="stretch")
    with top_right:
        specialty = (
            appointments.groupby("specialty", as_index=False)["appointment_id"]
            .count()
            .rename(columns={"appointment_id": "appointments"})
            .sort_values("appointments", ascending=False)
            .head(8)
            .set_index("specialty")
        )
        st.bar_chart(specialty, width="stretch")

    st.dataframe(
        appointments.loc[
            :, ["appointment_id", "date", "weekday", "hour", "provider", "specialty", "attended", "no_show"]
        ].head(100),
        width="stretch",
        hide_index=True,
    )
    st.link_button("Open Airtable View", DEFAULT_APPOINTMENTS_URL, width="stretch")
    st.info(
        "Real Airtable rows will load here automatically when `AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`, and `AIRTABLE_APPOINTMENTS_TABLE` are available and valid."
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_logs_tab() -> None:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    _render_section_header(
        "Communication audit",
        "Reminder and outreach logs",
        "Keep the communication layer close to the outcomes so the relationship between reminders and attendance is easier to explain.",
    )

    airtable_df = _fetch_airtable_table(AIRTABLE_COMMUNICATION_LOGS_TABLE)
    if airtable_df is not None and not airtable_df.empty:
        st.success("Loaded live Airtable communication log data.")
        st.dataframe(airtable_df, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    appointments = _load_csv("appointments_clean.csv")
    reminder = _load_csv("reminder_effectiveness.csv")

    top_left, top_right = st.columns(2)
    with top_left:
        reminder_weekday = (
            appointments.groupby("weekday", as_index=False)["reminder_sent"]
            .mean()
            .rename(columns={"reminder_sent": "reminder_coverage"})
            .set_index("weekday")
        )
        st.bar_chart(reminder_weekday, width="stretch")
    with top_right:
        reminder_status = (
            reminder.groupby("reminder_status", as_index=False)["no_show_rate"]
            .mean()
            .set_index("reminder_status")
        )
        st.bar_chart(reminder_status, width="stretch")

    summary = reminder.groupby("reminder_status", as_index=False)[["attendance_rate", "no_show_rate"]].mean()
    st.dataframe(summary, width="stretch", hide_index=True)
    st.link_button("Open Airtable View", DEFAULT_COMMUNICATION_LOGS_URL, width="stretch")
    st.info(
        "Real Airtable communication logs will load here automatically when `AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`, and `AIRTABLE_COMMUNICATION_LOGS_TABLE` are available and valid."
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_workflow_tab() -> None:
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    _render_section_header(
        "Automation handoff",
        "Trigger the n8n workflow",
        "Once you’ve reviewed the insight story, use this action to hand the latest context into the operational workflow.",
    )
    st.code(DEFAULT_N8N_WEBHOOK_URL, language="text")

    if st.button("Run n8n Workflow", width="stretch"):
        success, message = _trigger_n8n_workflow()
        st.session_state.workflow_status = (success, message)

    status = st.session_state.get("workflow_status")
    if status:
        success, message = status
        if success:
            st.success(f"Workflow triggered. Response: {message}")
        else:
            st.error(f"Workflow trigger failed: {message}")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_workspace_panel(facts: dict[str, object]) -> None:
    tab_overview, tab_access, tab_impact = st.tabs(
        ["Executive Overview", "Access & Scheduling Pressure", "AI Opportunities & Impact"]
    )
    with tab_overview:
        _render_executive_tab(facts)
    with tab_access:
        _render_access_tab(facts)
    with tab_impact:
        _render_impact_tab()


st.set_page_config(page_title="ClinicIQ Workspace", page_icon=":stethoscope:", layout="wide")
_inject_styles()

missing_files = _missing_processed_files()
if missing_files:
    _render_header()
    _render_setup_instructions(missing_files)
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

facts = summarize_operational_facts()

st.markdown('<div class="app-shell">', unsafe_allow_html=True)
_render_header()
_render_status_strip(facts)
_render_workspace_panel(facts)
st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
_render_chat_panel()
_render_footer()
st.markdown("</div>", unsafe_allow_html=True)
