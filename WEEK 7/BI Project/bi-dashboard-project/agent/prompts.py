from __future__ import annotations

import json
from typing import Any


def get_system_prompt() -> str:
    return (
        "You are an AI operations analyst for a mid-sized outpatient clinic. "
        "Use only the metrics provided to you. Focus strictly on appointment operations, "
        "no-shows, provider utilization, wait times, and reminder effectiveness. "
        "Do not provide diagnosis, treatment guidance, or any clinical advice. "
        "Return concise, structured operational insights only."
    )


def build_user_prompt(facts: dict[str, Any]) -> str:
    return (
        "Review the structured clinic metrics below and produce the top 3 to 5 operational insights. "
        "Each insight must include title, finding, evidence, likely_cause, recommended_action, "
        "priority, confidence, and affected_metric.\n\n"
        f"Structured metrics:\n{json.dumps(facts, indent=2)}"
    )
