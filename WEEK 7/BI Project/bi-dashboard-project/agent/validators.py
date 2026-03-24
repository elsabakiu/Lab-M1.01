from __future__ import annotations

import re
from typing import Iterable

try:
    from .schemas import Insight
except ImportError:
    from schemas import Insight


BANNED_CLINICAL_TERMS = {
    "diagnose",
    "diagnosis",
    "treat",
    "treatment",
    "medication",
    "prescription",
    "therapy plan",
    "clinical advice",
}

ACTION_HINTS = {
    "increase",
    "reduce",
    "review",
    "flag",
    "prioritize",
    "shift",
    "redistribute",
    "track",
    "monitor",
    "create",
}

ALLOWED_METRICS = {
    "no_show_rate",
    "reminder_effectiveness",
    "provider_utilization",
    "avg_wait_time_min",
}


def _contains_banned_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in BANNED_CLINICAL_TERMS)


def _is_actionable(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ACTION_HINTS)


def _has_numeric_evidence(text: str) -> bool:
    return bool(re.search(r"\d", text))


def validate_insight(insight: Insight) -> list[str]:
    errors: list[str] = []
    combined_text = " ".join(
        [
            insight.title,
            insight.finding,
            insight.evidence,
            insight.likely_cause,
            insight.recommended_action,
        ]
    )
    if insight.affected_metric not in ALLOWED_METRICS:
        errors.append(f"Unsupported affected_metric: {insight.affected_metric}")
    if not _has_numeric_evidence(insight.evidence):
        errors.append("Evidence must include a numeric detail grounded in the metrics.")
    if not _is_actionable(insight.recommended_action):
        errors.append("Recommended action is not specific enough.")
    if _contains_banned_terms(combined_text):
        errors.append("Clinical advice detected in insight output.")
    return errors


def validate_insights(insights: Iterable[Insight]) -> list[str]:
    all_errors: list[str] = []
    for index, insight in enumerate(insights, start=1):
        errors = validate_insight(insight)
        for error in errors:
            all_errors.append(f"Insight {index}: {error}")
    return all_errors
