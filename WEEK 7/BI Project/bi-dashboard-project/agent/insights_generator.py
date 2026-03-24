from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from .prompts import build_user_prompt, get_system_prompt
    from .schemas import Insight
    from .tools import summarize_operational_facts
except ImportError:
    from prompts import build_user_prompt, get_system_prompt
    from schemas import Insight
    from tools import summarize_operational_facts


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "8"))


def _openai_enhancement_enabled() -> bool:
    return os.getenv("ENABLE_OPENAI_ENHANCEMENT", "").strip().lower() in {"1", "true", "yes", "on"}


def _build_deterministic_insights(facts: dict[str, Any]) -> list[Insight]:
    no_show = facts["no_show"]
    patterns = facts["no_show_patterns"]
    provider = facts["provider_utilization"]
    wait_times = facts["wait_times"]
    reminder = facts["reminder_effectiveness"]

    reminder_gap = reminder["reminder_effect_size"]
    if reminder_gap > 0:
        reminder_title = "Expand reminder coverage where it changes attendance"
        reminder_finding = "Appointments with reminders perform better than appointments without reminders."
        reminder_cause = (
            "Reminder messages appear to reduce missed appointments by closing the gap between "
            "scheduling and attendance."
        )
        reminder_action = (
            "Increase reminder coverage for patients in high no-show segments and track the uplift "
            "by weekday, specialty, and lead-time bucket."
        )
    else:
        reminder_title = "Audit reminder targeting and timing"
        reminder_finding = (
            "Appointments that received reminders are still showing higher no-show rates than "
            "appointments without reminders."
        )
        reminder_cause = (
            "The clinic may already be targeting reminders to harder-to-attend patients, or the current "
            "timing and message design may not be strong enough to change attendance behavior."
        )
        reminder_action = (
            "Review who receives reminders, create an earlier or multi-step reminder sequence, and "
            "track high-risk attendance cohorts separately before using reminder coverage as a success metric."
        )

    insights = [
        Insight(
            title="Address the top no-show hotspot",
            finding=(
                f"The highest no-show hotspot is {patterns['peak_hotspot_weekday']} at "
                f"{patterns['peak_hotspot_hour']}:00 in {patterns['peak_hotspot_specialty']}."
            ),
            evidence=(
                f"No-show rate is {patterns['peak_hotspot_no_show_rate']:.1%} across "
                f"{patterns['peak_hotspot_appointments']} appointments in that segment."
            ),
            likely_cause=(
                f"{patterns['peak_hotspot_specialty']} is the highest-risk specialty and "
                f"{patterns['peak_weekday']} is the highest-risk weekday overall, suggesting "
                "scheduling friction in that slot."
            ),
            recommended_action=(
                "Prioritize reminder outreach and schedule confirmation for that weekday-hour block, "
                "then review whether those slots need overbooking or alternate staffing."
            ),
            priority="high",
            confidence="high",
            affected_metric="no_show_rate",
        ),
        Insight(
            title=reminder_title,
            finding=reminder_finding,
            evidence=(
                f"No-show rate is {reminder['reminder_sent_no_show_rate']:.1%} with reminders versus "
                f"{reminder['no_reminder_no_show_rate']:.1%} without reminders, a "
                f"{abs(reminder['reminder_effect_size']):.1%} absolute gap."
            ),
            likely_cause=reminder_cause,
            recommended_action=reminder_action,
            priority="high",
            confidence="high",
            affected_metric="reminder_effectiveness",
        ),
        Insight(
            title="Rebalance provider capacity",
            finding=(
                f"{provider['overloaded_share']:.1%} of provider-day records are overloaded, with "
                f"{provider['top_overloaded_provider']} in {provider['top_overloaded_specialty']} "
                "showing the highest average utilization."
            ),
            evidence=(
                f"{provider['top_overloaded_provider']} averages "
                f"{provider['top_provider_avg_utilization']:.2f} utilization and "
                f"{provider['top_provider_avg_wait_time_min']:.1f} minutes of wait time."
            ),
            likely_cause=(
                "Demand is clustering into a subset of providers while other slots remain underused."
            ),
            recommended_action=(
                "Shift appointment supply toward overloaded specialties, redistribute bookings across "
                "available providers, and flag provider-day utilization above 0.9 for intervention."
            ),
            priority="high",
            confidence="medium",
            affected_metric="provider_utilization",
        ),
        Insight(
            title="Investigate high-wait days",
            finding=(
                f"Average wait time peaks at {wait_times['peak_wait_time_min']:.1f} minutes on "
                f"{wait_times['peak_wait_time_date']}."
            ),
            evidence=(
                f"The overall average wait time is {wait_times['average_wait_time_min']:.1f} minutes, "
                f"and {wait_times['anomalous_days_count']} days exceed the "
                f"{wait_times['wait_time_alert_threshold_min']:.1f}-minute alert threshold."
            ),
            likely_cause=(
                "Wait times are likely rising on days where provider utilization, lead time variation, "
                "and afternoon demand combine."
            ),
            recommended_action=(
                "Create a daily wait-time alert, review staffing on peak-delay days, and separate "
                "longer-visit specialties from fast-turnover appointment blocks."
            ),
            priority="medium",
            confidence="medium",
            affected_metric="avg_wait_time_min",
        ),
        Insight(
            title="Track overall no-show performance weekly",
            finding=(
                f"Overall no-show rate averages {no_show['overall_no_show_rate']:.1%}, with the worst "
                f"day reaching {no_show['peak_no_show_rate']:.1%}."
            ),
            evidence=(
                f"The latest observed day is {no_show['latest_date']} at "
                f"{no_show['latest_no_show_rate']:.1%}, while the peak date "
                f"{no_show['peak_no_show_date']} recorded {no_show['peak_no_show_appointments']} "
                "missed appointments."
            ),
            likely_cause=(
                "No-show performance is consistent enough to monitor as an operational KPI, but high-risk "
                "segments still need targeted intervention."
            ),
            recommended_action=(
                "Review the no-show KPI weekly with clinic operations, set a threshold target, and pair "
                "it with reminder coverage and hotspot monitoring."
            ),
            priority="medium",
            confidence="high",
            affected_metric="no_show_rate",
        ),
    ]
    return insights


def _try_llm_enhancement(facts: dict[str, Any]) -> list[Insight] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not _openai_enhancement_enabled():
        return None

    try:
        from openai import OpenAI
    except Exception:
        return None

    try:
        client = OpenAI(
            api_key=api_key,
            timeout=OPENAI_TIMEOUT_SECONDS,
            max_retries=0,
        )
        prompt = build_user_prompt(facts)
        fallback = [insight.model_dump() for insight in _build_deterministic_insights(facts)]

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\nReturn JSON with an `insights` array. "
                        f"If unsure, stay close to these grounded examples:\n{json.dumps(fallback)}"
                    ),
                },
            ],
        )

        content = response.choices[0].message.content or ""
        payload = json.loads(content)
        raw_insights = payload.get("insights", [])
        return [Insight.model_validate(item) for item in raw_insights]
    except Exception:
        return None


def generate_insights() -> list[Insight]:
    facts = summarize_operational_facts()
    insights = _try_llm_enhancement(facts)
    if insights:
        return insights
    return _build_deterministic_insights(facts)


def serialize_insights(insights: list[Insight]) -> list[dict[str, Any]]:
    created_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for index, insight in enumerate(insights, start=1):
        row = insight.model_dump()
        row["timestamp"] = created_at
        row["insight_rank"] = index
        rows.append(row)
    return rows
