# Week 4 / Day 1 - Bloyce's Protocol (LangGraph)

This lab implements a **structured complaint workflow** for the Downside Up Complaint Bureau using **LangGraph**.

Unlike the Week 3/Day 3 creative LangChain agent, this workflow is rule-based and traceable.

## Objective
Build a state-machine workflow that enforces:

`intake -> validate -> investigate -> resolve -> close`

with conditional stops for clarification/rejection and explicit audit logging.

## Files
- `normalobjects_langgraph.py`: full workflow implementation
- `requirements.txt`: required Python packages
- `docs/langgraph_vs_langchain_comparison.md`: comparison with Week 3/Day 3
- `output/workflow_graph.png`: graph visualization artifact
- `output/test_complaints_output.txt`: full test run log
- `output/workflow_paths_output.txt`: compact path summary per complaint

## Setup
From `WEEK 4/Day 1`:

```bash
python -m pip install -r requirements.txt
```

Ensure your `.env` has:

- `OPENAI_API_KEY`

## Run
```bash
python normalobjects_langgraph.py
```

## What the workflow does

### 1) Intake
- Categorizes complaint into exactly one:
  - `portal`, `monster`, `psychic`, `environmental`, `other`
- Extracts required detail fields (`who`, `what`, `when`, `where`)
- Flags missing detail for clarification
- Checks duplicate complaints (same customer + same issue within 30 days) and links/consolidates metadata

### 2) Validate
- Applies category-specific validation rules
- Rejects insufficiently detailed complaints
- Auto-escalates `other` category to manual-review checkpoint

### 3) Manual Review (checkpoint)
- Runs for `other` category complaints
- Records escalation trace and continues flow for full lifecycle logging

### 4) Investigate
- Requires successful validation
- Produces category-specific investigation notes and evidence
- Guarantees documented evidence exists before resolution step

### 5) Resolve
- Requires investigation evidence
- Produces category-specific resolution
- Enforces protocol references and effectiveness rating (`high|medium|low`)
- Constrains specialized escalation to `monster` and `environmental` categories

### 6) Close
- Requires confirmed applied resolution
- Attempts customer satisfaction verification
- Logs closure record with required fields
- Schedules 30-day follow-up when effectiveness is `low`

## Traceability and outputs
The system tracks:
- `workflow_path`: executed node sequence
- `audit_log`: step-by-step protocol decisions

Artifacts written on each run:
- `output/workflow_graph.png`
- `output/test_complaints_output.txt`
- `output/workflow_paths_output.txt`

## Visualization
The script always saves the graph PNG to:

- `output/workflow_graph.png`

If running in a notebook/IPython environment, it also displays inline.

## Notes
- Duplicate detection currently uses an **in-memory history** for the current process run.
- For production, replace this with persistent storage (database or event store).
