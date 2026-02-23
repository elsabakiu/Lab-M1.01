# Report - Normal Objects LangChain Agent

## Scope
This document summarizes how the AI agent behaves when handling anomaly complaints in the Normal Objects universe using custom LangChain tools.

## When the agent used tools creatively
- The agent selected different tool combinations based on complaint type rather than following one fixed sequence.
- It mixed factual-style tools (`check_hawkins_records`, `gather_party_wisdom`) with imaginative tools (`consult_demogorgon`, `cast_interdimensional_spell`) to produce both explanation and action suggestions.
- For ambiguous complaints, the agent often used multiple perspectives (records + party + demogorgon) before proposing a final plan.

## Tool usage and chaining patterns
- Tool invocation is dynamic and prompt-driven.
- Chaining behavior typically follows this pattern:
  1. gather context (`check_hawkins_records` / `gather_party_wisdom`)
  2. add alternative perspective (`consult_demogorgon`)
  3. propose intervention (`cast_interdimensional_spell`)
- The exact order varies by complaint, which confirms flexible chaining.

## Comparison with a structured approach
- Agentic approach (current):
  - Pros: adaptive tool choice, better for open-ended complaints, more creative outputs.
  - Cons: less deterministic; output/tool path can vary between runs.
- Structured approach (fixed workflow):
  - Pros: predictable, easier to test/debug, stable behavior.
  - Cons: can over-call tools or miss nuance when complaints differ.

## Recommendations
- Use the **agentic approach** for exploratory, ambiguous, or narrative problem-solving tasks where creativity and flexible reasoning matter.
- Use a **structured pipeline** for compliance-style, repeatable, or production-critical tasks requiring deterministic behavior and strict validation.
- Hybrid recommendation:
  - Keep agentic planning for tool selection.
  - Add guardrails for output format and tool-call limits in higher-stakes workflows.
