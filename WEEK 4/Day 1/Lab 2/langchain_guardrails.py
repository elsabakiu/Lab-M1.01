"""Week 4 / Day 1 / Lab 2 - LangChain Guardrails starter.

This is a baseline agent that we will protect with guardrails in later steps.
It includes:
1) A small fake patient database (LLM-generated with fallback)
2) Four tools that operate on that database
3) A simple agent that can call those tools
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI


# ----------------------------
# Environment + model setup
# ----------------------------
def load_env() -> None:
    """Load local .env first, then workspace root .env as fallback."""
    lab_dir = Path(__file__).resolve().parent
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(lab_dir / ".env")
    load_dotenv(project_root / ".env")


def parse_json_safely(text: str) -> Any:
    """Parse LLM JSON that may come wrapped in markdown fences."""
    candidate = text.strip()
    if "```" in candidate:
        candidate = candidate.replace("```json", "").replace("```", "").strip()
    return json.loads(candidate)


# ----------------------------
# Fake patient DB generation
# ----------------------------
def fallback_fake_patients() -> list[dict[str, str]]:
    """Fallback dataset if LLM JSON generation fails."""
    return [
        {
            "patient_id": "P-1001",
            "name": "Ava Thompson",
            "age": "34",
            "condition": "Type 2 diabetes",
            "email": "ava.thompson@example.com",
            "phone": "555-0101",
            "last_visit": "2026-01-15",
            "notes": "Follow-up on glucose trends in 3 months.",
        },
        {
            "patient_id": "P-1002",
            "name": "Noah Patel",
            "age": "57",
            "condition": "Hypertension",
            "email": "noah.patel@example.com",
            "phone": "555-0102",
            "last_visit": "2026-02-02",
            "notes": "Medication adherence improved.",
        },
        {
            "patient_id": "P-1003",
            "name": "Mia Rodriguez",
            "age": "46",
            "condition": "Asthma",
            "email": "mia.rodriguez@example.com",
            "phone": "555-0103",
            "last_visit": "2025-12-20",
            "notes": "Review inhaler usage technique.",
        },
        {
            "patient_id": "P-1004",
            "name": "Liam Chen",
            "age": "29",
            "condition": "Migraine",
            "email": "liam.chen@example.com",
            "phone": "555-0104",
            "last_visit": "2026-01-08",
            "notes": "Track triggers and sleep schedule.",
        },
        {
            "patient_id": "P-1005",
            "name": "Emma Walker",
            "age": "63",
            "condition": "Hyperlipidemia",
            "email": "emma.walker@example.com",
            "phone": "555-0105",
            "last_visit": "2026-02-10",
            "notes": "Discuss diet and statin tolerance.",
        },
    ]


def generate_fake_patients_with_llm(llm: ChatOpenAI, count: int = 8) -> list[dict[str, str]]:
    """Generate fake patient records for security testing (prompt injection, etc.)."""
    prompt = f"""Generate {count} fake healthcare patient records as strict JSON.

Return ONLY a JSON array. No markdown fences.
Each object must include keys:
patient_id, name, age, condition, email, phone, last_visit, notes

Rules:
- Use completely fake data (not real people).
- Keep values realistic but synthetic.
- patient_id format should look like P-1001.
- last_visit format: YYYY-MM-DD.
"""
    response = llm.invoke(prompt)
    records = parse_json_safely(str(response.content))
    if not isinstance(records, list):
        raise ValueError("LLM did not return a JSON list.")
    cleaned: list[dict[str, str]] = []
    required = {
        "patient_id",
        "name",
        "age",
        "condition",
        "email", 
        "phone",
        "last_visit",
        "notes",
    }
    for item in records:
        if not isinstance(item, dict):
            continue
        if not required.issubset(item.keys()):
            continue
        cleaned.append({k: str(item[k]) for k in required})
    if not cleaned:
        raise ValueError("No valid patient records produced by LLM.")
    return cleaned


def build_patient_db(llm: ChatOpenAI) -> list[dict[str, str]]:
    """Build fake patient database and save it for testing."""
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "fake_patients.json"

    try:
        records = generate_fake_patients_with_llm(llm, count=8)
        source = "llm"
    except Exception:
        records = fallback_fake_patients()
        source = "fallback"

    output_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Fake patient DB created using {source}: {output_path}")
    return records


# Global in-memory storage used by tools.
PATIENT_DB: list[dict[str, str]] = []
SENT_EMAILS: list[dict[str, str]] = []


# ----------------------------
# Tools to protect later
# ----------------------------
@tool
def search_patient(query: str) -> str:
    """Search fake patient records by name, id, or condition."""
    q = query.lower().strip()
    matches = []
    for row in PATIENT_DB:
        haystack = " ".join(
            [
                row.get("patient_id", ""),
                row.get("name", ""),
                row.get("condition", ""),
                row.get("notes", ""),
            ]
        ).lower()
        if q in haystack:
            matches.append(
                {
                    "patient_id": row.get("patient_id"),
                    "name": row.get("name"),
                    "condition": row.get("condition"),
                    "last_visit": row.get("last_visit"),
                }
            )
    if not matches:
        return f"No patient records matched '{query}'."
    return json.dumps(matches, indent=2)


@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email notification (simulated)."""
    SENT_EMAILS.append({"recipient": recipient, "subject": subject, "body": body})
    return f"Email queued to {recipient} with subject '{subject}'."


@tool
def delete_record(patient_id: str) -> str:
    """Delete a patient record by patient_id (simulated destructive action)."""
    global PATIENT_DB
    before = len(PATIENT_DB)
    PATIENT_DB = [row for row in PATIENT_DB if row.get("patient_id") != patient_id]
    after = len(PATIENT_DB)
    if after < before:
        return f"Record {patient_id} deleted."
    return f"Record {patient_id} not found."


@tool
def search_medical_literature(topic: str) -> str:
    """Search medical literature (simulated static retrieval)."""
    simulated_db = {
        "diabetes": "Recent review: lifestyle + GLP-1 therapy improve outcomes.",
        "hypertension": "Meta-analysis: sodium reduction and exercise remain first-line.",
        "asthma": "GINA updates emphasize personalized inhaler strategies.",
        "migraine": "CGRP-targeted therapies show benefit for frequent attacks.",
    }
    key = topic.lower().strip()
    for k, v in simulated_db.items():
        if k in key:
            return v
    return f"No direct match for '{topic}'. Consider broader search terms."


def build_agent(llm: ChatOpenAI):
    """Create the baseline healthcare agent (without guardrails yet)."""
    system_prompt = (
        "You are a healthcare operations assistant. "
        "Use tools to help with patient-record queries and operational actions."
    )
    return create_agent(
        model=llm,
        tools=[search_patient, send_email, delete_record, search_medical_literature],
        system_prompt=system_prompt,
    )


def main() -> int:
    load_env()
    if not os.getenv("OPENAI_API_KEY"):
        print("Missing OPENAI_API_KEY. Add it to .env.")
        return 1

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    # Create fake database for guardrail testing.
    global PATIENT_DB
    PATIENT_DB = build_patient_db(llm)
    print(f"Loaded {len(PATIENT_DB)} fake patient records in memory.")

    # Build baseline agent.
    agent = build_agent(llm)
    print("Agent created with tools:")
    for tool_fn in [search_patient, send_email, delete_record, search_medical_literature]:
        print(f"- {tool_fn.name}")

    # Small smoke test prompt.
    test_prompt = "Find patients with diabetes and summarize what you found."
    result = agent.invoke({"messages": [{"role": "user", "content": test_prompt}]})
    final_message = result["messages"][-1]
    final_text = getattr(final_message, "content", str(final_message))
    print("\nSmoke test prompt:")
    print(test_prompt)
    print("\nAgent response:")
    print(final_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
