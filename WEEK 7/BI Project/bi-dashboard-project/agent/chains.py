from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from .prompts import get_system_prompt
except ImportError:
    from prompts import get_system_prompt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "8"))


def route_operational_question(question: str) -> str:
    lowered = question.lower()
    if any(token in lowered for token in ["reminder", "sms", "text message"]):
        return "reminders"
    if any(token in lowered for token in ["no-show", "noshow", "missed", "attendance"]):
        return "no_show"
    if any(token in lowered for token in ["provider", "utilization", "capacity", "overload", "staff"]):
        return "provider_utilization"
    if any(token in lowered for token in ["wait", "delay", "queue"]):
        return "wait_times"
    return "overview"


def _openai_enhancement_enabled() -> bool:
    return os.getenv("ENABLE_OPENAI_ENHANCEMENT", "").strip().lower() in {"1", "true", "yes", "on"}


def _try_llm_answer(question: str, facts: dict[str, Any], tool_result: dict[str, Any]) -> str | None:
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
        prompt = {
            "question": question,
            "facts": facts,
            "draft_answer": tool_result["answer"],
            "evidence": tool_result["evidence"],
            "recommendation": tool_result["recommendation"],
        }
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {
                    "role": "user",
                    "content": (
                        "Answer the user's operational question using only the provided facts. "
                        "Keep it concise, grounded, and non-clinical.\n\n"
                        f"{json.dumps(prompt, indent=2)}"
                    ),
                },
            ],
        )
        return response.choices[0].message.content
    except Exception:
        return None


def format_agent_output(question: str, facts: dict[str, Any], tool_result: dict[str, Any]) -> dict[str, Any]:
    response = dict(tool_result)
    enhanced = _try_llm_answer(question, facts, response)
    if enhanced:
        response["answer"] = enhanced

    response["question"] = question
    response["facts"] = facts
    response["agent_architecture"] = "langgraph + langchain-style tools"
    return response
