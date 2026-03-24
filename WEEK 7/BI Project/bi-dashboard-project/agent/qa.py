from __future__ import annotations

from typing import Any

try:
    from .agent import answer_operational_question
except ImportError:
    from agent import answer_operational_question


def answer_question(question: str) -> dict[str, Any]:
    return answer_operational_question(question)
