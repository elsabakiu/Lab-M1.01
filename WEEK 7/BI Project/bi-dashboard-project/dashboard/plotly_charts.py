"""Plotly chart functions for ClinicIQ Operations Analytics dashboard.

Each function returns a plotly Figure ready to render with st.plotly_chart().
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ClinicIQ colour palette
TEAL = "#1bb8c8"
TEAL_DARK = "#2b9db1"
RED = "#e74c4c"
AMBER = "#f39c12"
GREEN = "#27ae60"
GREY_BG = "#f6f8fb"
GREY_LINE = "#e0e6ed"

RISK_COLORS = {"High": RED, "Medium": AMBER, "Low": GREEN}

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

_CHART_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Inter, Arial, sans-serif", color="#1f2a37"),
    margin=dict(l=16, r=16, t=48, b=16),
    hoverlabel=dict(bgcolor="white", bordercolor=GREY_LINE, font_size=13),
)


# ---------------------------------------------------------------------------
# Chart 1: No-show rate over time
# ---------------------------------------------------------------------------

def chart_no_show_trend() -> go.Figure:
    daily = pd.read_csv(PROCESSED_DIR / "daily_kpis.csv")
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["no_show_rate"],
            mode="lines",
            name="No-Show Rate",
            line=dict(color=TEAL, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(27,184,200,0.08)",
            hovertemplate="%{x|%d %b}<br>No-show rate: %{y:.1%}<extra></extra>",
        )
    )
    # Avg line
    avg = daily["no_show_rate"].mean()
    fig.add_hline(
        y=avg,
        line_dash="dot",
        line_color=RED,
        annotation_text=f"Avg {avg:.1%}",
        annotation_position="top right",
        annotation_font_color=RED,
    )
    fig.update_layout(
        **_CHART_LAYOUT,
        title="No-Show Rate Over Time",
        yaxis=dict(tickformat=".0%", gridcolor=GREY_LINE, title=""),
        xaxis=dict(gridcolor=GREY_LINE, title=""),
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 2: No-show rate by day of week
# ---------------------------------------------------------------------------

def chart_no_show_by_weekday() -> go.Figure:
    patterns = pd.read_csv(PROCESSED_DIR / "no_show_patterns.csv")
    weekday = (
        patterns.groupby("weekday", as_index=False)
        .agg(no_show_count=("no_show_count", "sum"), total=("total_appointments", "sum"))
        .assign(no_show_rate=lambda d: d["no_show_count"] / d["total"])
    )
    weekday["weekday"] = pd.Categorical(weekday["weekday"], categories=WEEKDAY_ORDER, ordered=True)
    weekday = weekday.sort_values("weekday")

    colors = [RED if r >= 0.25 else TEAL for r in weekday["no_show_rate"]]
    fig = go.Figure(
        go.Bar(
            x=weekday["weekday"],
            y=weekday["no_show_rate"],
            marker_color=colors,
            text=weekday["no_show_rate"].apply(lambda v: f"{v:.1%}"),
            textposition="outside",
            hovertemplate="%{x}<br>No-show rate: %{y:.1%}<extra></extra>",
        )
    )
    fig.update_layout(
        **_CHART_LAYOUT,
        title="No-Show Rate by Day of Week",
        yaxis=dict(tickformat=".0%", gridcolor=GREY_LINE, title=""),
        xaxis=dict(title=""),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 3: No-show rate by specialty (horizontal bar)
# ---------------------------------------------------------------------------

def chart_no_show_by_specialty() -> go.Figure:
    patterns = pd.read_csv(PROCESSED_DIR / "no_show_patterns.csv")
    spec = (
        patterns.groupby("specialty", as_index=False)
        .agg(no_show_count=("no_show_count", "sum"), total=("total_appointments", "sum"))
        .assign(no_show_rate=lambda d: d["no_show_count"] / d["total"])
        .sort_values("no_show_rate")
    )

    fig = go.Figure(
        go.Bar(
            x=spec["no_show_rate"],
            y=spec["specialty"],
            orientation="h",
            marker_color=TEAL,
            text=spec["no_show_rate"].apply(lambda v: f"{v:.1%}"),
            textposition="outside",
            hovertemplate="%{y}<br>No-show rate: %{x:.1%}<extra></extra>",
        )
    )
    fig.update_layout(
        **_CHART_LAYOUT,
        title="No-Show Rate by Specialty",
        xaxis=dict(tickformat=".0%", gridcolor=GREY_LINE, title=""),
        yaxis=dict(title=""),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 4: Reminder effectiveness — grouped bar
# ---------------------------------------------------------------------------

def chart_reminder_effectiveness() -> go.Figure:
    reminder = pd.read_csv(PROCESSED_DIR / "reminder_effectiveness.csv")
    summary = (
        reminder.groupby("reminder_status", as_index=False)
        .agg(
            total=("total_appointments", "sum"),
            no_show=("no_show_appointments", "sum"),
            attended=("attended_appointments", "sum"),
        )
        .assign(
            no_show_rate=lambda d: d["no_show"] / d["total"],
            attendance_rate=lambda d: d["attended"] / d["total"],
        )
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="No-Show Rate",
            x=summary["reminder_status"],
            y=summary["no_show_rate"],
            marker_color=RED,
            text=summary["no_show_rate"].apply(lambda v: f"{v:.1%}"),
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Attendance Rate",
            x=summary["reminder_status"],
            y=summary["attendance_rate"],
            marker_color=GREEN,
            text=summary["attendance_rate"].apply(lambda v: f"{v:.1%}"),
            textposition="outside",
        )
    )
    fig.update_layout(
        **_CHART_LAYOUT,
        title="Reminder Effectiveness: Attendance vs No-Show",
        barmode="group",
        yaxis=dict(tickformat=".0%", gridcolor=GREY_LINE, title=""),
        xaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 5: Provider utilization heatmap (specialty × weekday)
# ---------------------------------------------------------------------------

def chart_provider_utilization_heatmap() -> go.Figure:
    provider = pd.read_csv(PROCESSED_DIR / "provider_utilization.csv")
    provider["date"] = pd.to_datetime(provider["date"])
    provider["weekday"] = provider["date"].dt.day_name()

    heat = (
        provider.groupby(["specialty", "weekday"], as_index=False)["utilization_rate"]
        .mean()
        .pivot(index="specialty", columns="weekday", values="utilization_rate")
        .reindex(columns=WEEKDAY_ORDER)
        .fillna(0)
    )

    fig = go.Figure(
        go.Heatmap(
            z=heat.values,
            x=heat.columns.tolist(),
            y=heat.index.tolist(),
            colorscale=[[0, "#e8f8f5"], [0.6, TEAL], [1.0, RED]],
            zmin=0,
            zmax=1.2,
            text=[[f"{v:.0%}" for v in row] for row in heat.values],
            texttemplate="%{text}",
            hovertemplate="Specialty: %{y}<br>Day: %{x}<br>Utilization: %{z:.0%}<extra></extra>",
            colorbar=dict(tickformat=".0%", title="Utilization"),
        )
    )
    heatmap_layout = {**_CHART_LAYOUT, "margin": dict(l=140, r=16, t=48, b=16)}
    fig.update_layout(
        **heatmap_layout,
        title="Provider Utilization by Specialty & Day",
        xaxis=dict(title=""),
        yaxis=dict(title=""),
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 6: Predicted no-show risk distribution (histogram)
# ---------------------------------------------------------------------------

def chart_risk_score_distribution() -> go.Figure | None:
    risk_path = PROCESSED_DIR / "daily_risk_report.csv"
    if not risk_path.exists():
        return None
    report = pd.read_csv(risk_path)
    if "No-Show Risk" not in report.columns:
        return None

    fig = px.histogram(
        report,
        x="No-Show Risk",
        nbins=20,
        color_discrete_sequence=[TEAL],
        title="Today's Appointment Risk Score Distribution",
        labels={"No-Show Risk": "Predicted No-Show Probability"},
    )
    fig.add_vline(x=0.35, line_dash="dot", line_color=AMBER, annotation_text="Medium threshold")
    fig.add_vline(x=0.60, line_dash="dot", line_color=RED, annotation_text="High threshold")
    fig.update_layout(
        **_CHART_LAYOUT,
        yaxis=dict(title="# Appointments", gridcolor=GREY_LINE),
        xaxis=dict(tickformat=".0%", title="Predicted No-Show Risk"),
    )
    return fig


# ---------------------------------------------------------------------------
# Chart 7: ROI impact waterfall
# ---------------------------------------------------------------------------

def chart_roi_impact() -> go.Figure:
    """
    Illustrates potential revenue recovery from AI-driven no-show reduction.
    Assumptions (documented inline for transparency):
    - 110,527 appointments per dataset period (≈ 8 weeks → ~13,816/week)
    - No-show rate: 20%
    - AI reduces no-show rate by 15% (conservative estimate from literature)
    - Average revenue per appointment: £80
    """
    weekly_appts = 13_816
    baseline_no_show_rate = 0.20
    ai_reduction_pct = 0.15  # 15% relative reduction
    revenue_per_appt = 80  # GBP

    weekly_no_shows = weekly_appts * baseline_no_show_rate
    recovered = weekly_no_shows * ai_reduction_pct
    weekly_revenue_gain = recovered * revenue_per_appt
    annual_revenue_gain = weekly_revenue_gain * 52

    fig = go.Figure(
        go.Waterfall(
            name="Revenue Impact",
            orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=[
                "Current weekly revenue<br>at risk from no-shows",
                "AI reminder targeting<br>(−8% no-show rate)",
                "Risk-board call prioritisation<br>(−7% no-show rate)",
                "Annual recovered revenue",
            ],
            y=[
                weekly_no_shows * revenue_per_appt,
                -(weekly_no_shows * 0.08 * revenue_per_appt),
                -(weekly_no_shows * 0.07 * revenue_per_appt),
                annual_revenue_gain,
            ],
            connector=dict(line=dict(color=GREY_LINE, width=1)),
            decreasing=dict(marker_color=GREEN),
            increasing=dict(marker_color=RED),
            totals=dict(marker_color=TEAL),
            text=[
                f"£{weekly_no_shows * revenue_per_appt:,.0f}/wk",
                f"−£{weekly_no_shows * 0.08 * revenue_per_appt:,.0f}/wk",
                f"−£{weekly_no_shows * 0.07 * revenue_per_appt:,.0f}/wk",
                f"£{annual_revenue_gain:,.0f}/yr",
            ],
            textposition="outside",
        )
    )
    layout = {**_CHART_LAYOUT, "margin": dict(l=16, r=16, t=48, b=60)}
    fig.update_layout(
        **layout,
        title="Estimated Annual Revenue Recovery from AI No-Show Reduction",
        yaxis=dict(tickprefix="£", tickformat=",.0f", gridcolor=GREY_LINE, title=""),
        showlegend=False,
    )
    return fig
