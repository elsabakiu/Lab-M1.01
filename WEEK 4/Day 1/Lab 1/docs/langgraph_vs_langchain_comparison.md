# Comparison: Week 4 Day 1 (LangGraph) vs Week 3 Day 3 (LangChain)

## Objective
This document compares two implementations in the NormalObjects project:
- Week 3 / Day 3: creative, agentic workflow using LangChain tools
- Week 4 / Day 1: structured, rule-driven workflow using LangGraph state machine

## High-level difference
- LangChain version is optimized for flexibility and creative reasoning.
- LangGraph version is optimized for strict process control, traceability, and consistency.

## Implementation comparison

### 1) Workflow control
- Week 3 / Day 3 (`src/normalobjects_langchain.py`):
  - Uses `create_agent(...)` and lets the model decide tool order dynamically.
  - Tool chaining is emergent at runtime.
- Week 4 / Day 1 (`normalobjects_langgraph.py`):
  - Uses `StateGraph(WorkflowState)` with explicit node sequence.
  - Enforces fixed lifecycle: `intake -> validate -> investigate -> resolve -> close`.
  - Conditional routing only decides whether to continue or stop (clarification/reject paths).

### 2) State management
- LangChain:
  - Lightweight state (message history + tool outputs).
  - Tool usage is tracked in a separate `ToolUsageTracker` class for analysis.
- LangGraph:
  - Rich typed state (`WorkflowState`) with explicit fields for:
    - intake parsing (`who/what/when/where`, category, missing details)
    - validation (`validation_passed`, errors, manual review)
    - investigation evidence
    - resolution metadata (protocol references, effectiveness)
    - closure metadata (timestamp, outcome, follow-up requirements)
  - State is updated at every step and persisted through node transitions.

### 3) Rule enforcement
- LangChain:
  - Behavior guided mainly by prompt/tool descriptions.
  - Not guaranteed to follow a strict order.
- LangGraph:
  - Rules are hard-coded into nodes and routing functions:
    - investigation blocked unless validation passed
    - resolution blocked without evidence
    - closure blocked if resolution not applied
    - low effectiveness triggers 30-day follow-up scheduling

### 4) Traceability and auditability
- LangChain:
  - Good visibility into tool calls and usage statistics.
  - Less deterministic for compliance-style audit.
- LangGraph:
  - Explicit `audit_log` and `workflow_path` capture each transition.
  - Added outputs:
    - `output/test_complaints_output.txt`
    - `output/workflow_paths_output.txt`
  - Graph visualization available via mermaid PNG export/display.

### 5) Output consistency
- LangChain:
  - More variable outputs; better for exploratory reasoning.
- LangGraph:
  - More consistent outputs for similar inputs due to fixed process and gates.

## Practical strengths and tradeoffs

### LangChain approach (Week 3/Day 3)
Strengths:
- Fast to prototype
- Creative responses and flexible tool order
- Works well for open-ended brainstorming and diagnosis

Tradeoffs:
- Harder to guarantee step-by-step compliance
- Less deterministic execution path

### LangGraph approach (Week 4/Day 1)
Strengths:
- Deterministic process and explicit state transitions
- Better for compliance, auditing, and repeatability
- Easier to reason about why/where processing stopped

Tradeoffs:
- More verbose implementation
- Less flexible for unstructured exploratory tasks

## When to use each
- Use **LangChain agentic workflow** when:
  - task is open-ended
  - creativity/adaptation is primary
  - strict process guarantees are not required

- Use **LangGraph structured workflow** when:
  - process order must be enforced
  - auditability is required
  - outcomes need to be consistent and policy-aligned

## Conclusion
Both approaches are valuable and complementary:
- Week 3 shows how to maximize creative problem-solving with tool-driven agents.
- Week 4 shows how to operationalize the same domain with controlled, traceable workflow execution.

For production complaint-handling under protocol constraints, the Week 4 LangGraph design is the stronger default.
