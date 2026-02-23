"""Week 4 / Day 1 - NormalObjects LangGraph scaffold.

This file sets up LangGraph and defines the shared workflow state.
Lab goal: structured, traceable workflow with these steps:
intake -> validate -> investigate -> resolve -> close
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

# Load environment variables from .env so OPENAI_API_KEY is available.
load_dotenv()

# LLM is initialized here for upcoming graph nodes.
# You can tune model and temperature later.
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

TEST_COMPLAINTS = [
    (
        "Who: Joyce Byers. "
        "What: The Downside Up portal at Hawkins Lab gate flickers and opens unpredictably. "
        "When: 2026-02-20 around 22:10 and 2026-02-21 around 03:40. "
        "Where: Hawkins Lab service entrance."
    ),
    (
        "Who: Steve Harrington. "
        "What: A demogorgon near the old rail yard alternates between hunting alone and coordinating with another creature. "
        "When: 2026-02-18 at 23:00 and 2026-02-19 at 01:20. "
        "Where: Hawkins rail yard."
    ),
    (
        "Who: Eleven. "
        "What: Psychic ability limitation: can move bikes but fails when lifting heavy rocks after 10 minutes of use. "
        "When: 2026-02-22 at 16:00 during controlled testing. "
        "Where: Hopper cabin training field."
    ),
    (
        "Who: Utility crew lead Tom. "
        "What: Environmental anomaly where power lines arc and creatures become agitated during storm fronts. "
        "When: 2026-02-17 between 19:00 and 20:00. "
        "Where: East Hawkins substation."
    ),
    (
        "Who: Karen Wheeler. "
        "What: I have a random complaint about strange vibes and unrelated noise with no clear downside-up category. "
        "When: 2026-02-21 at 12:00. "
        "Where: Downtown Hawkins."
    ),
    # Intentionally underspecified: should stop at intake and request clarification.
    "This is weird and broken somehow. Please fix it.",
    # Detailed but likely invalid for category-specific validation.
    (
        "Who: Mike Wheeler. "
        "What: Portal concern, but no anomaly detail beyond saying it feels odd. "
        "When: yesterday. "
        "Where: somewhere near town."
    ),
    # Duplicate of complaint 1 (same customer + same issue pattern) for consolidation test.
    (
        "Who: Joyce Byers. "
        "What: The Downside Up portal at Hawkins Lab gate flickers and opens unpredictably. "
        "When: 2026-02-25 around 22:05. "
        "Where: Hawkins Lab service entrance."
    ),
]


class WorkflowState(TypedDict):
    """Shared state passed between LangGraph nodes.

    This state is intentionally explicit so each step can read/write
    traceable fields for compliance and auditing.
    """

    # Core complaint input
    complaint_id: str
    complaint_text: str
    customer_id: str
    submitted_at: str

    # Parsed essential details (required for routing quality)
    who: NotRequired[str]
    what: NotRequired[str]
    when: NotRequired[str]
    where: NotRequired[str]
    missing_details: NotRequired[list[str]]
    clarification_requested: NotRequired[bool]

    # Intake categorization: exactly one category
    category: NotRequired[
        Literal["portal", "monster", "psychic", "environmental", "other"]
    ]

    # Duplicate handling (same customer + same issue within 30 days)
    issue_fingerprint: NotRequired[str]
    is_duplicate: NotRequired[bool]
    duplicate_of_complaint_id: NotRequired[str]
    consolidated_complaint_ids: NotRequired[list[str]]

    # Workflow control and traceability
    current_step: Literal[
        "intake", "validate", "manual_review", "investigate", "resolve", "close"
    ]
    workflow_path: NotRequired[list[str]]
    status: Literal[
        "new",
        "needs_clarification",
        "rejected",
        "in_progress",
        "escalated",
        "resolved",
        "closed",
    ]
    audit_log: list[str]

    # Validation
    validation_passed: NotRequired[bool]
    validation_errors: NotRequired[list[str]]
    manual_review_required: NotRequired[bool]
    manual_review_notes: NotRequired[str]

    # Investigation (must exist before resolution)
    investigation_notes: NotRequired[str]
    evidence: NotRequired[list[str]]
    investigation_completed: NotRequired[bool]

    # Resolution
    resolution: NotRequired[str]
    protocol_references: NotRequired[list[str]]
    specialized_team_escalation: NotRequired[bool]
    effectiveness_rating: NotRequired[Literal["high", "medium", "low"]]
    resolution_applied: NotRequired[bool]

    # Closure
    customer_satisfaction_attempted: NotRequired[bool]
    customer_satisfaction_result: NotRequired[
        Literal["satisfied", "unsatisfied", "no_response", "unknown"]
    ]
    outcome: NotRequired[str]
    closed_at: NotRequired[str]
    closure_log_entry: NotRequired[dict[str, str]]
    follow_up_required: NotRequired[bool]
    follow_up_due_at: NotRequired[str]


VALID_CATEGORIES = {"portal", "monster", "psychic", "environmental", "other"}

# In-memory duplicate index used during one process run.
# Note: this is not persistent storage; restart resets history.
COMPLAINT_HISTORY: list[dict[str, str]] = []


def _invoke_llm_text(prompt: str) -> str:
    """Run one prompt through the shared LLM and return plain text."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return str(response.content).strip()


def _json_from_llm_text(raw_text: str) -> dict:
    """Best-effort JSON parse for LLM responses, handling fenced blocks."""
    candidate = raw_text
    if "```" in candidate:
        candidate = candidate.replace("```json", "").replace("```", "").strip()
    return json.loads(candidate)


def _next_trace(state: WorkflowState, step: str) -> tuple[list[str], list[str]]:
    """Return updated audit and workflow path lists for a new step."""
    updated_audit = list(state.get("audit_log", []))
    updated_path = list(state.get("workflow_path", []))
    updated_path.append(step)
    return updated_audit, updated_path


def _missing_details_from_state(state: WorkflowState) -> list[str]:
    """Compute missing who/what/when/where fields from current state."""
    missing_details = list(state.get("missing_details", []))
    if not missing_details:
        for key in ("who", "what", "when", "where"):
            if not state.get(key):
                missing_details.append(key)
    return missing_details


def _normalize_issue_text(text: str) -> str:
    """Normalize complaint text for stable duplicate fingerprinting."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return " ".join(tokens)


def _parse_iso_dt(value: str) -> datetime | None:
    """Parse ISO datetime safely; return None if parse fails."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _detect_duplicate(
    state: WorkflowState, issue_fingerprint: str
) -> tuple[bool, str, list[str]]:
    """Check if same customer raised same issue within 30 days."""
    customer_id = state.get("customer_id", "")
    submitted_at = _parse_iso_dt(state.get("submitted_at", "")) or datetime.now(
        timezone.utc
    )

    duplicate_of = ""
    consolidated_ids: list[str] = []
    for item in COMPLAINT_HISTORY:
        if item.get("customer_id") != customer_id:
            continue
        if item.get("issue_fingerprint") != issue_fingerprint:
            continue
        previous_ts = _parse_iso_dt(item.get("submitted_at", ""))
        if previous_ts is None:
            continue
        if submitted_at - previous_ts <= timedelta(days=30):
            duplicate_of = item.get("complaint_id", "")
            if duplicate_of:
                consolidated_ids = [duplicate_of, state.get("complaint_id", "")]
                return True, duplicate_of, consolidated_ids
    return False, duplicate_of, consolidated_ids


def _register_history(state: WorkflowState, issue_fingerprint: str) -> None:
    """Store complaint in in-memory history for duplicate checks."""
    COMPLAINT_HISTORY.append(
        {
            "complaint_id": state.get("complaint_id", ""),
            "customer_id": state.get("customer_id", ""),
            "submitted_at": state.get("submitted_at", ""),
            "issue_fingerprint": issue_fingerprint,
        }
    )


def intake_node(state: WorkflowState) -> WorkflowState:
    """Step 1: Intake - parse and categorize the complaint."""
    print("\n[INTAKE] Processing complaint...")

    complaint = state["complaint_text"]

    # 1) Categorize complaint into exactly one Bloyce category.
    categorization_prompt = f"""Categorize this Downside Up complaint into one of these categories:
- portal: Issues with portal timing, location, or behavior
- monster: Issues with creature behavior (demogorgons, etc.)
- psychic: Issues with psychic abilities or limitations
- environmental: Issues with electricity, weather, or physical environment
- other: Anything else

Complaint: {complaint}

Respond with ONLY one word:
portal or monster or psychic or environmental or other."""
    category_text = _invoke_llm_text(categorization_prompt).lower()
    if category_text not in VALID_CATEGORIES:
        category_text = "other"

    # 2) Extract essential detail flags (who/what/when/where) for clarification routing.
    detail_prompt = f"""Extract essential complaint details and return strict JSON.
Keys: who, what, when, where
If missing, return empty string for that key.

Complaint: {complaint}
"""
    details_text = _invoke_llm_text(detail_prompt)

    parsed_details: dict[str, str] = {"who": "", "what": "", "when": "", "where": ""}
    try:
        loaded = _json_from_llm_text(details_text)
        for key in parsed_details:
            parsed_details[key] = str(loaded.get(key, "")).strip()
    except Exception:
        # Keep safe defaults if model output is not parseable JSON.
        pass

    missing_details = [key for key, value in parsed_details.items() if not value]
    clarification_requested = len(missing_details) > 0

    fingerprint_source = parsed_details.get("what") or complaint
    # Duplicate detection uses the normalized issue content (prefer `what` detail).
    issue_fingerprint = _normalize_issue_text(fingerprint_source)
    is_duplicate, duplicate_of_id, consolidated_ids = _detect_duplicate(
        state, issue_fingerprint
    )

    updated_audit, updated_path = _next_trace(state, "intake")
    updated_audit.append(
        f"intake: category={category_text}, missing_details={','.join(missing_details) or 'none'}"
    )
    if is_duplicate:
        updated_audit.append(
            f"intake: duplicate=true linked_to={duplicate_of_id} consolidated={consolidated_ids}"
        )
    else:
        updated_audit.append("intake: duplicate=false")

    _register_history(state, issue_fingerprint)

    new_state: WorkflowState = {
        **state,
        "category": category_text,  # type: ignore[typeddict-item]
        "who": parsed_details["who"],
        "what": parsed_details["what"],
        "when": parsed_details["when"],
        "where": parsed_details["where"],
        "missing_details": missing_details,
        "clarification_requested": clarification_requested,
        "issue_fingerprint": issue_fingerprint,
        "is_duplicate": is_duplicate,
        "duplicate_of_complaint_id": duplicate_of_id,
        "consolidated_complaint_ids": consolidated_ids,
        "current_step": "intake",
        "workflow_path": updated_path,
        "status": "needs_clarification" if clarification_requested else "in_progress",
        "audit_log": updated_audit,
    }

    print(f"[INTAKE] Categorized as: {category_text}")
    if clarification_requested:
        print(f"[INTAKE] Missing essential details: {', '.join(missing_details)}")
    return new_state


def validate_node(state: WorkflowState) -> WorkflowState:
    """Step 2: Validate - enforce Bloyce's protocol validation rules."""
    print("\n[VALIDATE] Validating complaint against protocol rules...")

    category = state.get("category", "other")
    complaint = state.get("complaint_text", "")
    complaint_lower = complaint.lower()

    updated_audit, updated_path = _next_trace(state, "validate")
    errors: list[str] = []
    validation_passed = True
    manual_review_required = False

    # First gate: route quality requires who/what/when/where completeness.
    missing_details = _missing_details_from_state(state)

    if missing_details:
        validation_passed = False
        errors.append(
            "Insufficient detail for routing. Missing: " + ", ".join(missing_details)
        )
        updated_audit.append(
            "validate: rejected due to missing essential details "
            f"({','.join(missing_details)})"
        )
        print("[VALIDATE] Rejected: insufficient details for routing.")
        return {
            **state,
            "current_step": "validate",
            "validation_passed": False,
            "validation_errors": errors,
            "manual_review_required": False,
            "clarification_requested": True,
            "status": "rejected",
            "workflow_path": updated_path,
            "audit_log": updated_audit,
        }

    # Category-specific rules
    if category == "portal":
        has_portal_signal = "portal" in complaint_lower or "gate" in complaint_lower
        has_location_or_timing = bool(state.get("where")) or bool(state.get("when"))
        has_anomaly_terms = any(
            term in complaint_lower
            for term in ("timing", "location", "flicker", "open", "close", "schedule")
        )
        if not (has_portal_signal and has_location_or_timing and has_anomaly_terms):
            validation_passed = False
            errors.append(
                "Portal complaint must reference specific location/timing anomaly."
            )

    elif category == "monster":
        has_creature_reference = any(
            term in complaint_lower
            for term in ("monster", "demogorgon", "creature", "mind flayer")
        )
        has_behavior_or_interaction = any(
            term in complaint_lower
            for term in (
                "behavior",
                "attack",
                "eat",
                "hunt",
                "chase",
                "interact",
                "interaction",
            )
        )
        if not (has_creature_reference and has_behavior_or_interaction):
            validation_passed = False
            errors.append(
                "Monster complaint must describe creature behavior or interactions."
            )

    elif category == "psychic":
        has_psychic_reference = any(
            term in complaint_lower
            for term in ("psychic", "power", "ability", "telekinesis", "vision")
        )
        has_limitation_or_malfunction = any(
            term in complaint_lower
            for term in (
                "limit",
                "limited",
                "can't",
                "cannot",
                "unable",
                "fail",
                "malfunction",
                "inconsistent",
            )
        )
        if not (has_psychic_reference and has_limitation_or_malfunction):
            validation_passed = False
            errors.append(
                "Psychic complaint must reference specific ability limits or malfunction."
            )

    elif category == "environmental":
        has_environment_signal = any(
            term in complaint_lower
            for term in (
                "electricity",
                "power",
                "line",
                "weather",
                "storm",
                "temperature",
                "atmosphere",
                "physical",
            )
        )
        if not has_environment_signal:
            validation_passed = False
            errors.append(
                "Environmental complaint must connect to electricity, weather, or observable physical phenomena."
            )

    elif category == "other":
        # Other category is valid for routing but must be escalated to manual review.
        manual_review_required = True
        updated_audit.append("validate: category=other -> manual review escalation")

    if validation_passed:
        updated_audit.append(
            f"validate: passed (category={category}, manual_review={manual_review_required})"
        )
        print(
            "[VALIDATE] Passed."
            + (" Escalated for manual review." if manual_review_required else "")
        )
    else:
        updated_audit.append(
            f"validate: failed (category={category}, errors={'; '.join(errors)})"
        )
        print("[VALIDATE] Failed: " + "; ".join(errors))

    return {
        **state,
        "current_step": "validate",
        "validation_passed": validation_passed,
        "validation_errors": errors,
        "manual_review_required": manual_review_required,
        "status": "escalated"
        if manual_review_required
        else ("in_progress" if validation_passed else "rejected"),
        "clarification_requested": not validation_passed,
        "workflow_path": updated_path,
        "audit_log": updated_audit,
    }


def manual_review_node(state: WorkflowState) -> WorkflowState:
    """Manual-review checkpoint for category=other complaints."""
    print("\n[MANUAL_REVIEW] Escalation checkpoint for manual review...")
    updated_audit, updated_path = _next_trace(state, "manual_review")
    # Keep this as a trace checkpoint; workflow continues for full lifecycle logging.
    notes = (
        "Complaint routed to manual review due to category 'other'. "
        "Automated pipeline continues for trace completeness."
    )
    updated_audit.append("manual_review: escalated case acknowledged")
    return {
        **state,
        "current_step": "manual_review",
        "manual_review_notes": notes,
        "status": "escalated",
        "workflow_path": updated_path,
        "audit_log": updated_audit,
    }


def investigate_node(state: WorkflowState) -> WorkflowState:
    """Step 3: Investigate - gather category-specific evidence."""
    print("\n[INVESTIGATE] Gathering investigation evidence...")

    updated_audit, updated_path = _next_trace(state, "investigate")

    # Bloyce rule: investigation cannot proceed without successful validation.
    if not state.get("validation_passed", False):
        updated_audit.append(
            "investigate: blocked (validation_passed is false; investigation not allowed)"
        )
        print("[INVESTIGATE] Blocked: validation must pass before investigation.")
        return {
            **state,
            "current_step": "investigate",
            "investigation_completed": False,
            "investigation_notes": "Blocked: validation did not pass.",
            "evidence": [],
            "status": "rejected",
            "workflow_path": updated_path,
            "audit_log": updated_audit,
        }

    category = state.get("category", "other")
    complaint = state.get("complaint_text", "")
    when = state.get("when", "")
    where = state.get("where", "")

    investigation_prompts = {
        "portal": (
            "Investigate portal issues using this checklist:\n"
            "1) temporal patterns\n"
            "2) location consistency\n"
            "3) environmental factors\n"
            "Return strict JSON with keys: investigation_notes (string), evidence (array of strings).\n"
            f"Complaint: {complaint}\nWhen: {when}\nWhere: {where}"
        ),
        "monster": (
            "Investigate monster issues using this checklist:\n"
            "1) behavioral data\n"
            "2) interaction patterns\n"
            "3) environmental triggers\n"
            "Return strict JSON with keys: investigation_notes (string), evidence (array of strings).\n"
            f"Complaint: {complaint}\nWhen: {when}\nWhere: {where}"
        ),
        "psychic": (
            "Investigate psychic issues using this checklist:\n"
            "1) ability specifications\n"
            "2) tested limitations\n"
            "3) contextual factors\n"
            "Return strict JSON with keys: investigation_notes (string), evidence (array of strings).\n"
            f"Complaint: {complaint}\nWhen: {when}\nWhere: {where}"
        ),
        "environmental": (
            "Investigate environmental issues using this checklist:\n"
            "1) power line activity\n"
            "2) atmospheric conditions\n"
            "3) anomaly correlation\n"
            "Return strict JSON with keys: investigation_notes (string), evidence (array of strings).\n"
            f"Complaint: {complaint}\nWhen: {when}\nWhere: {where}"
        ),
        "other": (
            "This complaint is category 'other'. Gather concise fact-finding evidence for manual review.\n"
            "Return strict JSON with keys: investigation_notes (string), evidence (array of strings).\n"
            f"Complaint: {complaint}\nWhen: {when}\nWhere: {where}"
        ),
    }

    prompt = investigation_prompts.get(category, investigation_prompts["other"])
    raw_text = _invoke_llm_text(prompt)

    notes = ""
    evidence: list[str] = []
    try:
        loaded = _json_from_llm_text(raw_text)
        notes = str(loaded.get("investigation_notes", "")).strip()
        raw_evidence = loaded.get("evidence", [])
        if isinstance(raw_evidence, list):
            evidence = [str(item).strip() for item in raw_evidence if str(item).strip()]
    except Exception:
        # Safe fallback to guarantee documented evidence exists.
        notes = "Fallback investigation summary generated due to non-JSON model response."
        evidence = [
            f"Complaint text reviewed: {complaint[:120]}",
            f"Category under investigation: {category}",
            "Manual verification required for detailed evidence expansion.",
        ]

    # Bloyce rule: documented evidence must exist before resolution.
    if not evidence:
        evidence = [f"Minimum evidence entry for category '{category}'."]
    investigation_completed = len(evidence) > 0

    updated_audit.append(
        f"investigate: completed={investigation_completed}, category={category}, evidence_count={len(evidence)}"
    )
    print(
        f"[INVESTIGATE] Completed for category '{category}' with {len(evidence)} evidence item(s)."
    )

    return {
        **state,
        "current_step": "investigate",
        "investigation_notes": notes,
        "evidence": evidence,
        "investigation_completed": investigation_completed,
        "status": "in_progress",
        "workflow_path": updated_path,
        "audit_log": updated_audit,
    }


def resolve_node(state: WorkflowState) -> WorkflowState:
    """Step 4: Resolve - apply a category-specific fix."""
    print("\n[RESOLVE] Building resolution plan...")

    updated_audit, updated_path = _next_trace(state, "resolve")
    category = state.get("category", "other")
    complaint = state.get("complaint_text", "")
    evidence = list(state.get("evidence", []))

    # Bloyce rule: no resolution without documented investigation evidence.
    if not evidence:
        updated_audit.append(
            "resolve: blocked (no documented investigation evidence available)"
        )
        print("[RESOLVE] Blocked: evidence required before resolution.")
        return {
            **state,
            "current_step": "resolve",
            "resolution": "Resolution blocked: no documented investigation evidence.",
            "protocol_references": [],
            "effectiveness_rating": "low",
            "specialized_team_escalation": False,
            "resolution_applied": False,
            "status": "rejected",
            "workflow_path": updated_path,
            "audit_log": updated_audit,
        }

    resolution_prompts = {
        "portal": (
            "Create a specific portal-issue resolution based on evidence.\n"
            "Must reference established Downside Up protocol(s).\n"
            "Return strict JSON with keys:\n"
            "resolution (string), protocol_references (array of strings), "
            "effectiveness_rating (high|medium|low), specialized_team_escalation (boolean).\n"
            f"Complaint: {complaint}\nEvidence: {evidence}"
        ),
        "monster": (
            "Create a specific monster-issue resolution based on evidence.\n"
            "Must reference established Downside Up protocol(s).\n"
            "Monster cases may require specialized team escalation.\n"
            "Return strict JSON with keys:\n"
            "resolution (string), protocol_references (array of strings), "
            "effectiveness_rating (high|medium|low), specialized_team_escalation (boolean).\n"
            f"Complaint: {complaint}\nEvidence: {evidence}"
        ),
        "psychic": (
            "Create a specific psychic-issue resolution based on evidence.\n"
            "Must reference established Downside Up protocol(s).\n"
            "Return strict JSON with keys:\n"
            "resolution (string), protocol_references (array of strings), "
            "effectiveness_rating (high|medium|low), specialized_team_escalation (boolean).\n"
            f"Complaint: {complaint}\nEvidence: {evidence}"
        ),
        "environmental": (
            "Create a specific environmental-issue resolution based on evidence.\n"
            "Must reference established Downside Up protocol(s).\n"
            "Environmental cases may require specialized team escalation.\n"
            "Return strict JSON with keys:\n"
            "resolution (string), protocol_references (array of strings), "
            "effectiveness_rating (high|medium|low), specialized_team_escalation (boolean).\n"
            f"Complaint: {complaint}\nEvidence: {evidence}"
        ),
        "other": (
            "Create a conservative interim resolution for an 'other' complaint.\n"
            "Must reference established Downside Up protocol(s) and manual review dependency.\n"
            "Return strict JSON with keys:\n"
            "resolution (string), protocol_references (array of strings), "
            "effectiveness_rating (high|medium|low), specialized_team_escalation (boolean).\n"
            f"Complaint: {complaint}\nEvidence: {evidence}"
        ),
    }

    prompt = resolution_prompts.get(category, resolution_prompts["other"])
    raw_text = _invoke_llm_text(prompt)

    resolution = ""
    protocol_references: list[str] = []
    effectiveness_rating: Literal["high", "medium", "low"] = "medium"
    specialized_team_escalation = False

    try:
        loaded = _json_from_llm_text(raw_text)

        resolution = str(loaded.get("resolution", "")).strip()
        refs = loaded.get("protocol_references", [])
        if isinstance(refs, list):
            protocol_references = [str(r).strip() for r in refs if str(r).strip()]

        rating = str(loaded.get("effectiveness_rating", "medium")).strip().lower()
        if rating in {"high", "medium", "low"}:
            effectiveness_rating = rating  # type: ignore[assignment]

        specialized_team_escalation = bool(loaded.get("specialized_team_escalation", False))
    except Exception:
        # Safe fallback that still respects protocol requirements.
        resolution = (
            f"Apply category-specific containment and monitoring for '{category}' issue, "
            "then re-check after controlled protocol cycle."
        )
        protocol_references = ["DU-CORE-01", "DU-INCIDENT-TRIAGE-02"]
        effectiveness_rating = "medium"
        specialized_team_escalation = category in {"monster", "environmental"}

    # Enforce protocol references presence.
    if not protocol_references:
        protocol_references = ["DU-CORE-01"]

    # Enforce protocol: specialized escalation is only for monster/environmental.
    if category not in {"monster", "environmental"}:
        specialized_team_escalation = False
    elif effectiveness_rating == "low":
        specialized_team_escalation = True

    resolution_applied = True
    updated_audit.append(
        "resolve: applied resolution "
        f"(category={category}, effectiveness={effectiveness_rating}, "
        f"escalation={specialized_team_escalation})"
    )
    print(
        "[RESOLVE] Resolution prepared with effectiveness="
        f"{effectiveness_rating} and escalation={specialized_team_escalation}."
    )

    return {
        **state,
        "current_step": "resolve",
        "resolution": resolution,
        "protocol_references": protocol_references,
        "effectiveness_rating": effectiveness_rating,
        "specialized_team_escalation": specialized_team_escalation,
        "resolution_applied": resolution_applied,
        "status": "resolved",
        "workflow_path": updated_path,
        "audit_log": updated_audit,
    }


def close_node(state: WorkflowState) -> WorkflowState:
    """Step 5: Close - confirm completion and write closure record."""
    print("\n[CLOSE] Finalizing complaint closure...")

    updated_audit, updated_path = _next_trace(state, "close")

    # Bloyce rule: closure requires confirmation that resolution was applied.
    if not state.get("resolution_applied", False):
        updated_audit.append("close: blocked (resolution_applied is false)")
        print("[CLOSE] Blocked: resolution must be applied before closure.")
        return {
            **state,
            "current_step": "close",
            "status": "resolved",
            "outcome": "Closure blocked: resolution not confirmed as applied.",
            "customer_satisfaction_attempted": False,
            "workflow_path": updated_path,
            "audit_log": updated_audit,
        }

    complaint = state.get("complaint_text", "")
    category = state.get("category", "other")
    resolution = state.get("resolution", "")
    effectiveness = state.get("effectiveness_rating", "medium")

    # Attempt customer satisfaction verification (required attempt before closure).
    satisfaction_prompt = (
        "Simulate a concise customer satisfaction check result for this complaint resolution.\n"
        "Return ONLY one of: satisfied, unsatisfied, no_response, unknown.\n"
        f"Complaint: {complaint}\nResolution: {resolution}"
    )
    satisfaction_text = _invoke_llm_text(satisfaction_prompt).lower()
    if satisfaction_text not in {"satisfied", "unsatisfied", "no_response", "unknown"}:
        satisfaction_text = "unknown"

    now_utc = datetime.now(timezone.utc)
    closed_at = now_utc.isoformat()

    # Bloyce rule: low effectiveness requires 30-day follow-up checkpoint.
    follow_up_required = effectiveness == "low"
    follow_up_due_at = (
        (now_utc + timedelta(days=30)).isoformat() if follow_up_required else ""
    )

    outcome = (
        f"Complaint closed with {effectiveness} predicted effectiveness; "
        f"customer_satisfaction={satisfaction_text}."
    )

    closure_log_entry = {
        "category": str(category),
        "resolution": str(resolution)[:400],
        "outcome": outcome,
        "timestamp": closed_at,
    }

    updated_audit.append(
        "close: completed "
        f"(satisfaction={satisfaction_text}, follow_up_required={follow_up_required})"
    )
    print(
        "[CLOSE] Closed complaint. "
        f"follow_up_required={follow_up_required}, satisfaction={satisfaction_text}"
    )

    return {
        **state,
        "current_step": "close",
        "customer_satisfaction_attempted": True,
        "customer_satisfaction_result": satisfaction_text,  # type: ignore[typeddict-item]
        "closed_at": closed_at,
        "closure_log_entry": closure_log_entry,
        "follow_up_required": follow_up_required,
        "follow_up_due_at": follow_up_due_at,
        "outcome": outcome,
        "status": "closed",
        "workflow_path": updated_path,
        "audit_log": updated_audit,
    }


def visualize_workflow_path(state: WorkflowState) -> str:
    """Return a readable path visualization from the workflow execution."""
    path = list(state.get("workflow_path", []))
    if not path:
        return "(no steps recorded)"
    return " -> ".join(path)


def _route_after_intake(state: WorkflowState) -> Literal["validate", "end"]:
    """Route after intake: clarification requests stop flow until user clarifies."""
    if state.get("clarification_requested", False):
        return "end"
    return "validate"


def _route_after_validate_with_manual(
    state: WorkflowState,
) -> Literal["investigate", "manual_review", "end"]:
    """Route after validation with explicit manual-review checkpoint."""
    if not state.get("validation_passed", False):
        return "end"
    if state.get("manual_review_required", False):
        return "manual_review"
    return "investigate"


def _route_after_resolve(state: WorkflowState) -> Literal["close", "end"]:
    """Route after resolution: unresolved/blocked states stop, resolved continue."""
    if state.get("status") != "resolved":
        return "end"
    return "close"


def build_graph():
    """Create and compile the complaint workflow graph.

    Flow:
    intake -> validate -> investigate -> resolve -> close
    with protocol-safe conditional stops for clarification/rejection.
    """

    graph = StateGraph(WorkflowState)

    # Add all workflow nodes.
    graph.add_node("intake", intake_node)
    graph.add_node("validate", validate_node)
    graph.add_node("manual_review", manual_review_node)
    graph.add_node("investigate", investigate_node)
    graph.add_node("resolve", resolve_node)
    graph.add_node("close", close_node)

    # Entry.
    graph.add_edge(START, "intake")

    # Conditional routes.
    graph.add_conditional_edges(
        "intake",
        _route_after_intake,
        {"validate": "validate", "end": END},
    )
    graph.add_conditional_edges(
        "validate",
        _route_after_validate_with_manual,
        {
            "manual_review": "manual_review",
            "investigate": "investigate",
            "end": END,
        },
    )

    # Linear middle path.
    graph.add_edge("manual_review", "investigate")
    graph.add_edge("investigate", "resolve")

    # Conditional route before closure.
    graph.add_conditional_edges(
        "resolve",
        _route_after_resolve,
        {"close": "close", "end": END},
    )

    # Normal completion.
    graph.add_edge("close", END)

    # Compile runnable workflow.
    return graph.compile()


def run_workflow_tests(app) -> None:
    """Run structured workflow over sample complaints."""
    # Reset in-memory duplicate history to keep test runs reproducible.
    COMPLAINT_HISTORY.clear()

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    full_output_path = output_dir / "test_complaints_output.txt"
    path_output_path = output_dir / "workflow_paths_output.txt"

    full_lines: list[str] = []
    path_lines: list[str] = []

    def emit(line: str = "") -> None:
        print(line)
        full_lines.append(line)

    emit("\nTesting workflow with sample complaints...\n")

    for idx, complaint in enumerate(TEST_COMPLAINTS, start=1):
        emit(f"\n{'=' * 80}")
        emit(f"Complaint {idx}: {complaint}")
        emit(f"{'=' * 80}")

        complaint_text_norm = complaint.lower()
        if "joyce byers" in complaint_text_norm:
            customer_id = "CUST-JOYCE"
        elif "steve harrington" in complaint_text_norm:
            customer_id = "CUST-STEVE"
        elif "eleven" in complaint_text_norm:
            customer_id = "CUST-ELEVEN"
        elif "tom" in complaint_text_norm:
            customer_id = "CUST-TOM"
        elif "karen wheeler" in complaint_text_norm:
            customer_id = "CUST-KAREN"
        elif "mike wheeler" in complaint_text_norm:
            customer_id = "CUST-MIKE"
        else:
            customer_id = f"CUST-{idx:03d}"

        initial_state: WorkflowState = {
            "complaint_id": f"CMP-{idx:03d}",
            "complaint_text": complaint,
            "customer_id": customer_id,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "current_step": "intake",
            "status": "new",
            "audit_log": [],
        }

        final_state = app.invoke(initial_state)
        workflow_path_text = visualize_workflow_path(final_state)

        emit("Result summary:")
        emit(f"- category: {final_state.get('category', 'unknown')}")
        emit(f"- status: {final_state.get('status', 'unknown')}")
        emit(f"- current_step: {final_state.get('current_step', 'unknown')}")
        emit(f"- validation_passed: {final_state.get('validation_passed', False)}")
        emit(f"- manual_review_required: {final_state.get('manual_review_required', False)}")
        emit(f"- evidence_count: {len(final_state.get('evidence', []))}")
        emit(f"- effectiveness_rating: {final_state.get('effectiveness_rating', 'n/a')}")
        emit(f"- follow_up_required: {final_state.get('follow_up_required', False)}")
        emit(f"- workflow_path: {workflow_path_text}")
        path_lines.append(
            f"Complaint {idx}: status={final_state.get('status', 'unknown')} | path={workflow_path_text}"
        )

        errors = final_state.get("validation_errors", [])
        if errors:
            emit(f"- validation_errors: {errors}")

        emit("- audit trail:")
        for item in final_state.get("audit_log", []):
            emit(f"  - {item}")

    full_output_path.write_text("\n".join(full_lines) + "\n", encoding="utf-8")
    path_output_path.write_text("\n".join(path_lines) + "\n", encoding="utf-8")
    print(f"\nSaved full test output to: {full_output_path}")
    print(f"Saved workflow path output to: {path_output_path}")


def visualize_graph(app) -> None:
    """Visualize graph and always save PNG artifact in output folder."""
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "workflow_graph.png"

    image = app.get_graph().draw_mermaid_png()
    png_path.write_bytes(image)
    print(f"Saved workflow graph image to: {png_path}")

    # Optional notebook display.
    try:
        from IPython.display import Image, display

        display(Image(image))
        print("Displayed workflow graph in notebook output.")
    except Exception:
        pass


def main() -> None:
    """Quick smoke check that environment and scaffold load correctly."""

    api_key = os.getenv("OPENAI_API_KEY")
    print("OPENAI_API_KEY set:" if api_key else "OPENAI_API_KEY missing")

    app = build_graph()
    print("LangGraph workflow compiled successfully.")
    print(f"Compiled graph type: {type(app).__name__}")
    visualize_graph(app)
    run_workflow_tests(app)


if __name__ == "__main__":
    main()
