from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(*_args, **_kwargs):
        def decorator(func):
            return func
        return decorator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def load_processed_data() -> dict[str, pd.DataFrame]:
    return {
        "appointments_clean": pd.read_csv(PROCESSED_DIR / "appointments_clean.csv"),
        "daily_kpis": pd.read_csv(PROCESSED_DIR / "daily_kpis.csv"),
        "no_show_patterns": pd.read_csv(PROCESSED_DIR / "no_show_patterns.csv"),
        "provider_utilization": pd.read_csv(PROCESSED_DIR / "provider_utilization.csv"),
        "reminder_effectiveness": pd.read_csv(PROCESSED_DIR / "reminder_effectiveness.csv"),
    }


def calculate_no_show_rate(daily_kpis: pd.DataFrame) -> dict[str, Any]:
    latest = daily_kpis.sort_values("date").iloc[-1]
    peak = daily_kpis.loc[daily_kpis["no_show_rate"].idxmax()]
    return {
        "overall_no_show_rate": round(float(daily_kpis["no_show_rate"].mean()), 4),
        "latest_no_show_rate": round(float(latest["no_show_rate"]), 4),
        "latest_date": str(latest["date"]),
        "peak_no_show_rate": round(float(peak["no_show_rate"]), 4),
        "peak_no_show_date": str(peak["date"]),
        "peak_no_show_appointments": int(peak["no_show_appointments"]),
    }


def analyze_no_show_by_weekday_hour(no_show_patterns: pd.DataFrame) -> dict[str, Any]:
    filtered = no_show_patterns[no_show_patterns["total_appointments"] >= 40].copy()
    top_combo = filtered.sort_values(
        ["no_show_rate", "total_appointments"], ascending=[False, False]
    ).iloc[0]
    top_weekday = (
        filtered.groupby("weekday", as_index=False)
        .agg(
            total_appointments=("total_appointments", "sum"),
            no_show_count=("no_show_count", "sum"),
        )
        .assign(no_show_rate=lambda df: df["no_show_count"] / df["total_appointments"])
        .sort_values(["no_show_rate", "total_appointments"], ascending=[False, False])
        .iloc[0]
    )
    top_specialty = (
        filtered.groupby("specialty", as_index=False)
        .agg(
            total_appointments=("total_appointments", "sum"),
            no_show_count=("no_show_count", "sum"),
        )
        .assign(no_show_rate=lambda df: df["no_show_count"] / df["total_appointments"])
        .sort_values(["no_show_rate", "total_appointments"], ascending=[False, False])
        .iloc[0]
    )
    return {
        "peak_weekday": str(top_weekday["weekday"]),
        "peak_weekday_no_show_rate": round(float(top_weekday["no_show_rate"]), 4),
        "peak_specialty": str(top_specialty["specialty"]),
        "peak_specialty_no_show_rate": round(float(top_specialty["no_show_rate"]), 4),
        "peak_hotspot_weekday": str(top_combo["weekday"]),
        "peak_hotspot_hour": int(top_combo["hour"]),
        "peak_hotspot_specialty": str(top_combo["specialty"]),
        "peak_hotspot_no_show_rate": round(float(top_combo["no_show_rate"]), 4),
        "peak_hotspot_appointments": int(top_combo["total_appointments"]),
    }


def provider_utilization_summary(provider_utilization: pd.DataFrame) -> dict[str, Any]:
    summary = (
        provider_utilization.groupby(["provider", "specialty"], as_index=False)
        .agg(
            avg_utilization_rate=("utilization_rate", "mean"),
            avg_wait_time_min=("avg_wait_time_min", "mean"),
            total_appointments=("total_appointments", "sum"),
            overloaded_days=("utilization_status", lambda s: int((s == "Overloaded").sum())),
        )
        .sort_values(["avg_utilization_rate", "total_appointments"], ascending=[False, False])
    )
    top_provider = summary.iloc[0]
    utilization_mix = provider_utilization["utilization_status"].value_counts(normalize=True)
    return {
        "top_overloaded_provider": str(top_provider["provider"]),
        "top_overloaded_specialty": str(top_provider["specialty"]),
        "top_provider_avg_utilization": round(float(top_provider["avg_utilization_rate"]), 4),
        "top_provider_avg_wait_time_min": round(float(top_provider["avg_wait_time_min"]), 2),
        "overloaded_share": round(float(utilization_mix.get("Overloaded", 0.0)), 4),
        "balanced_share": round(float(utilization_mix.get("Balanced", 0.0)), 4),
        "underused_share": round(float(utilization_mix.get("Underused", 0.0)), 4),
    }


def detect_wait_time_anomalies(daily_kpis: pd.DataFrame) -> dict[str, Any]:
    avg_wait = float(daily_kpis["avg_wait_time_min"].mean())
    std_wait = float(daily_kpis["avg_wait_time_min"].std(ddof=0))
    threshold = avg_wait + std_wait
    anomalies = daily_kpis[daily_kpis["avg_wait_time_min"] >= threshold].copy()
    top_day = daily_kpis.loc[daily_kpis["avg_wait_time_min"].idxmax()]
    return {
        "average_wait_time_min": round(avg_wait, 2),
        "wait_time_alert_threshold_min": round(threshold, 2),
        "anomalous_days_count": int(len(anomalies)),
        "peak_wait_time_date": str(top_day["date"]),
        "peak_wait_time_min": round(float(top_day["avg_wait_time_min"]), 2),
    }


def compare_reminder_effectiveness(reminder_effectiveness: pd.DataFrame) -> dict[str, Any]:
    summary = (
        reminder_effectiveness.groupby("reminder_status", as_index=False)
        .agg(
            total_appointments=("total_appointments", "sum"),
            attended_appointments=("attended_appointments", "sum"),
            no_show_appointments=("no_show_appointments", "sum"),
        )
        .assign(
            attendance_rate=lambda df: df["attended_appointments"] / df["total_appointments"],
            no_show_rate=lambda df: df["no_show_appointments"] / df["total_appointments"],
        )
    )
    reminder_sent = summary[summary["reminder_status"] == "Reminder Sent"].iloc[0]
    no_reminder = summary[summary["reminder_status"] == "No Reminder"].iloc[0]
    return {
        "reminder_sent_no_show_rate": round(float(reminder_sent["no_show_rate"]), 4),
        "no_reminder_no_show_rate": round(float(no_reminder["no_show_rate"]), 4),
        "reminder_sent_attendance_rate": round(float(reminder_sent["attendance_rate"]), 4),
        "no_reminder_attendance_rate": round(float(no_reminder["attendance_rate"]), 4),
        "reminder_effect_size": round(
            float(no_reminder["no_show_rate"] - reminder_sent["no_show_rate"]), 4
        ),
        "reminder_sent_appointments": int(reminder_sent["total_appointments"]),
        "no_reminder_appointments": int(no_reminder["total_appointments"]),
    }


def summarize_operational_facts() -> dict[str, Any]:
    datasets = load_processed_data()
    facts = {
        "no_show": calculate_no_show_rate(datasets["daily_kpis"]),
        "no_show_patterns": analyze_no_show_by_weekday_hour(datasets["no_show_patterns"]),
        "provider_utilization": provider_utilization_summary(datasets["provider_utilization"]),
        "wait_times": detect_wait_time_anomalies(datasets["daily_kpis"]),
        "reminder_effectiveness": compare_reminder_effectiveness(
            datasets["reminder_effectiveness"]
        ),
    }
    facts["metadata"] = {
        "source_files": sorted(path.name for path in PROCESSED_DIR.glob("*.csv")),
        "processed_dir": str(PROCESSED_DIR),
    }
    return facts


def build_no_show_analysis(
    question: str,
    datasets: dict[str, pd.DataFrame],
    facts: dict[str, Any],
) -> dict[str, Any]:
    patterns = datasets["no_show_patterns"]
    hotspot = patterns.sort_values(["no_show_rate", "total_appointments"], ascending=[False, False]).iloc[0]
    weekday = (
        patterns.groupby("weekday", as_index=False)
        .agg(total_appointments=("total_appointments", "sum"), no_show_count=("no_show_count", "sum"))
        .assign(no_show_rate=lambda df: df["no_show_count"] / df["total_appointments"])
        .sort_values(["no_show_rate", "total_appointments"], ascending=[False, False])
    )
    return {
        "route": "no_show",
        "answer": (
            f"No-shows are highest in {hotspot['specialty']} on {hotspot['weekday']} at "
            f"{int(hotspot['hour'])}:00, where the no-show rate reaches {float(hotspot['no_show_rate']):.1%}. "
            f"Overall no-show rate is {facts['no_show']['overall_no_show_rate']:.1%}."
        ),
        "evidence": [
            f"Top hotspot: {hotspot['weekday']} {int(hotspot['hour'])}:00, {hotspot['specialty']}",
            f"Hotspot appointments: {int(hotspot['total_appointments'])}",
            f"Peak weekday overall: {facts['no_show_patterns']['peak_weekday']} at {facts['no_show_patterns']['peak_weekday_no_show_rate']:.1%}",
        ],
        "recommendation": (
            "Target reminder timing, confirmation outreach, and scheduling review on the worst-performing "
            "weekday-hour blocks first."
        ),
        "support_table": weekday.loc[:, ["weekday", "total_appointments", "no_show_count", "no_show_rate"]]
        .sort_values(["no_show_rate", "total_appointments"], ascending=False)
        .reset_index(drop=True)
        .head(10),
        "chart_title": "No-Show Rate By Weekday",
        "chart_kind": "bar",
        "chart_data": weekday.loc[:, ["weekday", "no_show_rate"]].reset_index(drop=True),
    }


def build_provider_utilization_analysis(
    question: str,
    datasets: dict[str, pd.DataFrame],
    facts: dict[str, Any],
) -> dict[str, Any]:
    provider = datasets["provider_utilization"]
    summary = (
        provider.groupby(["provider", "specialty"], as_index=False)
        .agg(
            avg_utilization_rate=("utilization_rate", "mean"),
            avg_wait_time_min=("avg_wait_time_min", "mean"),
            total_appointments=("total_appointments", "sum"),
            overloaded_days=("utilization_status", lambda s: int((s == "Overloaded").sum())),
        )
        .sort_values(["avg_utilization_rate", "total_appointments"], ascending=[False, False])
    )
    top = summary.iloc[0]
    return {
        "route": "provider_utilization",
        "answer": (
            f"The most overloaded provider is {top['provider']} in {top['specialty']}, averaging "
            f"{float(top['avg_utilization_rate']):.2f} utilization and {float(top['avg_wait_time_min']):.1f} minutes of wait time. "
            f"Across all provider-day records, {facts['provider_utilization']['overloaded_share']:.1%} are overloaded."
        ),
        "evidence": [
            f"Top provider: {top['provider']} ({top['specialty']})",
            f"Overloaded share: {facts['provider_utilization']['overloaded_share']:.1%}",
            f"Underused share: {facts['provider_utilization']['underused_share']:.1%}",
        ],
        "recommendation": (
            "Redistribute bookings across underused providers and review provider-day utilization above 0.90."
        ),
        "support_table": summary.loc[
            :, ["provider", "specialty", "avg_utilization_rate", "avg_wait_time_min", "overloaded_days"]
        ]
        .sort_values(["avg_utilization_rate", "overloaded_days"], ascending=False)
        .reset_index(drop=True)
        .head(10),
        "chart_title": "Most Overloaded Providers",
        "chart_kind": "bar",
        "chart_data": summary.loc[:, ["provider", "avg_utilization_rate"]].head(10).reset_index(drop=True),
    }


def build_wait_time_analysis(
    question: str,
    datasets: dict[str, pd.DataFrame],
    facts: dict[str, Any],
) -> dict[str, Any]:
    daily = datasets["daily_kpis"].sort_values("avg_wait_time_min", ascending=False)
    top = daily.iloc[0]
    return {
        "route": "wait_times",
        "answer": (
            f"Wait times peak on {top['date']} at {float(top['avg_wait_time_min']):.1f} minutes. "
            f"The overall average is {facts['wait_times']['average_wait_time_min']:.1f} minutes, "
            f"and {facts['wait_times']['anomalous_days_count']} days exceed the alert threshold of "
            f"{facts['wait_times']['wait_time_alert_threshold_min']:.1f} minutes."
        ),
        "evidence": [
            f"Peak day: {top['date']}",
            f"Peak wait time: {float(top['avg_wait_time_min']):.1f} minutes",
            f"Alert threshold: {facts['wait_times']['wait_time_alert_threshold_min']:.1f} minutes",
        ],
        "recommendation": (
            "Set up a daily wait-time review on peak-delay days and align staffing with the highest-volume blocks."
        ),
        "support_table": daily.loc[
            :, ["date", "avg_wait_time_min", "total_appointments", "estimated_utilization_rate", "no_show_rate"]
        ]
        .sort_values(["avg_wait_time_min", "estimated_utilization_rate"], ascending=False)
        .reset_index(drop=True)
        .head(10),
        "chart_title": "Average Wait Time By Day",
        "chart_kind": "line",
        "chart_data": datasets["daily_kpis"].sort_values("date").loc[:, ["date", "avg_wait_time_min"]].reset_index(drop=True),
    }


def build_reminder_effectiveness_analysis(
    question: str,
    datasets: dict[str, pd.DataFrame],
    facts: dict[str, Any],
) -> dict[str, Any]:
    reminder = (
        datasets["reminder_effectiveness"]
        .groupby("reminder_status", as_index=False)
        .agg(
            total_appointments=("total_appointments", "sum"),
            attended_appointments=("attended_appointments", "sum"),
            no_show_appointments=("no_show_appointments", "sum"),
        )
    )
    reminder["attendance_rate"] = reminder["attended_appointments"] / reminder["total_appointments"]
    reminder["no_show_rate"] = reminder["no_show_appointments"] / reminder["total_appointments"]
    return {
        "route": "reminders",
        "answer": (
            f"In this dataset, reminder recipients have a no-show rate of "
            f"{facts['reminder_effectiveness']['reminder_sent_no_show_rate']:.1%}, compared with "
            f"{facts['reminder_effectiveness']['no_reminder_no_show_rate']:.1%} for patients without reminders."
        ),
        "evidence": [
            f"Reminder gap: {abs(facts['reminder_effectiveness']['reminder_effect_size']):.1%}",
            f"Reminder-sent appointments: {facts['reminder_effectiveness']['reminder_sent_appointments']}",
            f"No-reminder appointments: {facts['reminder_effectiveness']['no_reminder_appointments']}",
        ],
        "recommendation": (
            "Audit reminder targeting and timing before assuming reminder coverage is improving attendance."
        ),
        "support_table": reminder.loc[:, ["reminder_status", "total_appointments", "attendance_rate", "no_show_rate"]]
        .sort_values(["no_show_rate", "total_appointments"], ascending=False)
        .reset_index(drop=True)
        .head(10),
        "chart_title": "Reminder Vs No Reminder",
        "chart_kind": "bar",
        "chart_data": reminder.loc[:, ["reminder_status", "no_show_rate", "attendance_rate"]].reset_index(drop=True),
    }


def build_overview_analysis(
    question: str,
    datasets: dict[str, pd.DataFrame],
    facts: dict[str, Any],
) -> dict[str, Any]:
    daily = datasets["daily_kpis"].sort_values("date")
    latest = daily.iloc[-1]
    return {
        "route": "overview",
        "answer": (
            f"The clinic is averaging {facts['no_show']['overall_no_show_rate']:.1%} no-shows, "
            f"{facts['wait_times']['average_wait_time_min']:.1f} minutes of wait time, and "
            f"{float(daily['estimated_utilization_rate'].mean()):.1%} estimated utilization. "
            f"On the latest day, {int(latest['total_appointments'])} appointments were scheduled."
        ),
        "evidence": [
            f"Latest date: {latest['date']}",
            f"Latest appointments: {int(latest['total_appointments'])}",
            f"Latest no-show rate: {float(latest['no_show_rate']):.1%}",
        ],
        "recommendation": (
            "Use this overview to decide whether to drill into no-shows, wait times, provider load, or reminders."
        ),
        "support_table": daily.loc[
            :, ["date", "total_appointments", "no_show_rate", "avg_wait_time_min", "estimated_utilization_rate"]
        ]
        .sort_values(["date"], ascending=False)
        .reset_index(drop=True)
        .head(10),
        "chart_title": "Daily Operational Trend",
        "chart_kind": "line",
        "chart_data": daily.loc[:, ["date", "no_show_rate", "avg_wait_time_min"]].reset_index(drop=True),
    }


def get_operational_analysis_builders() -> dict[str, Any]:
    return {
        "no_show": build_no_show_analysis,
        "provider_utilization": build_provider_utilization_analysis,
        "wait_times": build_wait_time_analysis,
        "reminders": build_reminder_effectiveness_analysis,
        "overview": build_overview_analysis,
    }


@tool("analyze_no_show")
def analyze_no_show_tool(question: str) -> dict[str, Any]:
    """Analyze no-show patterns and hotspots for clinic operations."""
    return build_no_show_analysis(question, load_processed_data(), summarize_operational_facts())


@tool("analyze_provider_utilization")
def analyze_provider_utilization_tool(question: str) -> dict[str, Any]:
    """Analyze provider utilization, overload, and capacity balance."""
    return build_provider_utilization_analysis(question, load_processed_data(), summarize_operational_facts())


@tool("analyze_wait_times")
def analyze_wait_times_tool(question: str) -> dict[str, Any]:
    """Analyze wait-time pressure and anomalous operational days."""
    return build_wait_time_analysis(question, load_processed_data(), summarize_operational_facts())


@tool("analyze_reminder_effectiveness")
def analyze_reminder_effectiveness_tool(question: str) -> dict[str, Any]:
    """Analyze reminder performance and attendance differences."""
    return build_reminder_effectiveness_analysis(question, load_processed_data(), summarize_operational_facts())


@tool("analyze_overview")
def analyze_overview_tool(question: str) -> dict[str, Any]:
    """Provide an overall clinic operations summary."""
    return build_overview_analysis(question, load_processed_data(), summarize_operational_facts())
