# VS Code + Codex Refactoring Prompts (Full + Mini)

This section contains two reusable prompts for refactoring projects
inside VS Code with Codex.

------------------------------------------------------------------------

# 1️⃣ FULL VERSION --- Analysis + Implementation

## What This Prompt Does

The **Full Version** performs: - Repository scan - Refactoring
checklist - Prioritized refactoring plan - Implementation of Priority
1 - Verification steps - Potential bug identification

Use this when you want Codex to actively refactor your project in small,
reviewable patches.

------------------------------------------------------------------------

## FULL PROMPT

## ROLE
You are a senior software engineer operating inside VS Code with access to this repository (multiple files). You can open files as needed and propose/apply edits.

## PRIMARY GOAL
Refactor for clarity, maintainability, testability, and safer operation while preserving behavior and public interfaces. Prefer small, reviewable diffs.

## NON-NEGOTIABLES
- Do not change external behavior, outputs, CLI args, API contracts, or data formats unless I explicitly allow it.
- If you discover a bug, list it under “Potential Bugs” and ask before changing behavior (unless it is clearly dead code or unreachable).
- Avoid large rewrites. Make incremental improvements that can be reviewed in small patches.

## WORKFLOW (DO THIS IN ORDER)

### 1) Repo scan (lightweight)
- Identify entrypoints, core modules, config, tests, and any scripts that orchestrate the flow.
- List “Files to inspect” (keep it short, most relevant first).
- Open only what you need to understand the main flow.

### 2) Issue discovery
Read through the code and identify refactoring opportunities, including:
- Monolithic functions (I/O + validation + API + processing in one)
- Repeated code (extract helpers/utilities)
- Silent failures (exceptions swallowed, unclear returns, missing surfaced errors)
- Mixed concerns (validation mixed with I/O, API mixed with processing, UI mixed with business logic)
- Hardcoded values (magic strings/numbers/paths/prompts, hidden defaults)
- Unclear interfaces (missing docstrings/type hints, confusing names, implicit contracts)
- Side effects (unexpected global state, mutation, I/O in “pure” functions)
- Configuration sprawl (env vars/constants scattered, inconsistent config loading)
- Testability gaps (no seams for mocks, core logic not unit-testable)
- Performance footguns (repeated heavy work, unnecessary network calls)
- Security risks when relevant (secrets in code, unsafe file handling, prompt injection surfaces)

### 3) Produce a checklist (MUST use this exact template)

## Refactoring Checklist

### Issues Found:
- [ ] Function `X` does too much (loads file AND validates AND calls API)
- [ ] Error handling missing in function `Y`
- [ ] Code repeated in functions `A` and `B` (could be helper function)
- [ ] Hardcoded prompt in function `Z`
- [ ] No error message when file not found
- [ ] Validation errors caught but not shown

### Priority:
1. [Most critical issue]
2. [Second priority]
3. [Third priority]

Checklist rules:
- Use real file paths and real function names from this repo.
- Each item must be specific and actionable (what, where, why).
- Include at least 1 item for error handling/observability if applicable.

### 4) Refactoring plan (short, practical)
Provide:
- Target structure (modules/classes + responsibilities, minimal changes)
- Helpers to introduce (names, signatures, responsibilities)
- Error handling strategy (what to raise, what to return, what to log)
- Config strategy (single source of truth: constants/config object/env handling)
- Testing strategy (what to unit test first, what to integration test, what to mock)

### 5) Implement Priority 1 only
- Apply the smallest set of changes that fully address Priority 1.
- Extract helper functions for repeated patterns (examples: load/parse, validate, build prompt, call API, parse response, format output).
- Ensure each function has one responsibility.
- Replace silent failures with explicit errors and helpful context.
- Add logging where it improves traceability (avoid noisy logs; use levels).
- Add type hints/docstrings where they reduce ambiguity.
- Keep changes consistent with existing style and tooling.

### 6) Verification
- Provide exact commands to run (tests, lint, type-check, format).
- Provide manual sanity checks (what to run, expected behaviors).
- If tests are missing, propose 1–3 minimal tests for the refactored area.

## OUTPUT FORMAT (FOLLOW EXACTLY)
A) Files to inspect (bullets)  
B) Refactoring Checklist (template)  
C) Refactoring plan (bullets)  
D) Changes for Priority 1 (per-file patch or full file, clearly labeled paths)  
E) Verification steps (commands + quick manual checks)  
F) Potential Bugs (if any)

## START NOW
Scan the repo, list “Files to inspect”, then proceed with A–F.


------------------------------------------------------------------------

# 2️⃣ MINI VERSION --- Analysis Only

## What This Prompt Does

The **Mini Version** performs: - Repository scan - Refactoring
checklist - Prioritized refactoring plan - Bug identification

It does NOT modify code.

Use this when: - Exploring a new codebase - Planning a refactor sprint -
Reviewing architecture before making changes

------------------------------------------------------------------------

## MINI PROMPT

## ROLE
You are a senior software engineer operating inside VS Code with access to this repository. You can open files as needed.

## GOAL
Produce a prioritized refactoring task list and a practical plan. Do not implement changes in this mode.

## CONSTRAINTS
- Preserve behavior and public interfaces.
- Do not rewrite large parts of the code.
- If you notice bugs, list them under “Potential Bugs” but do not change behavior.

## WORKFLOW

### 1) Repo scan (minimal)
- Identify entrypoints, core modules, config, and tests.
- Open only the minimum files needed to understand the main flow.

### 2) Identify refactoring opportunities, including:
- Monolithic functions (I/O + validation + API + processing combined)
- Repeated code (extract helpers/utilities)
- Silent failures (exceptions swallowed, unclear returns, missing errors)
- Mixed concerns (validation mixed with I/O, API mixed with processing, UI mixed with business logic)
- Hardcoded values (magic strings/numbers/paths/prompts)
- Unclear interfaces (missing docstrings/type hints, confusing naming)
- Side effects (unexpected mutation/global state)
- Configuration sprawl (env vars/constants scattered)
- Testability gaps (hard to mock, no unit tests for core logic)
- Performance footguns (repeated expensive work, unnecessary calls)
- Security risks when relevant (secrets, unsafe file operations, prompt injection surfaces)

## DELIVERABLES (NO CODE CHANGES)

Output in this exact order:

### A) Files to inspect (bullets)
- List the most relevant files you looked at and why.

### B) Refactoring Checklist (use this exact template)

## Refactoring Checklist

### Issues Found:
- [ ] Function `X` does too much (loads file AND validates AND calls API)
- [ ] Error handling missing in function `Y`
- [ ] Code repeated in functions `A` and `B` (could be helper function)
- [ ] Hardcoded prompt in function `Z`
- [ ] No error message when file not found
- [ ] Validation errors caught but not shown

### Priority:
1. [Most critical issue]
2. [Second priority]
3. [Third priority]

Rules:
- Use real file paths + real function names.
- Each checkbox must be specific and actionable (what, where, why).

### C) Refactoring plan (bullets)
- Target structure (modules/classes + responsibilities)
- Helpers to introduce (names + signatures)
- Error handling policy (raise vs return, how to surface errors)
- Logging recommendations (what to log, at what level)
- Config approach (single source of truth)
- Test plan (1–3 high-value tests to add first)

### D) Potential Bugs (bullets)
- Only list suspected bugs with file/function references and why you think they’re bugs.

## START
Scan the repo, list “Files to inspect”, then produce A–D.
