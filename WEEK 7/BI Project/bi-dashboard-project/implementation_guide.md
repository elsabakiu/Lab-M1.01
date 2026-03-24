# Healthcare SME AI Analytics Solution: Implementation Guide

This guide turns the project plan into a practical sequence we can follow to build the full solution end to end.

## 1. Target Outcome

We are building a healthcare operations analytics solution for a mid-sized outpatient clinic or ambulatory care provider.

The finished project should include:

- cleaned and processed clinic operations data
- a Plotly/Streamlit dashboard experience for stakeholder review
- a healthcare operations AI agent that generates structured insights
- LangSmith tracing and evaluation for the agent
- an n8n workflow that turns insights into a daily summary action
- cost and timeline documentation for an SME implementation

## 2. Architecture We Are Building

The system flow is:

1. Raw public and synthetic healthcare data enters the data preparation layer.
2. Python preprocessing creates clean appointment data and KPI summary tables.
3. Streamlit and Plotly read those processed CSVs and display operational metrics.
4. The AI agent reads the same KPI tables and generates structured insights.
5. LangSmith tracks prompts, tool calls, outputs, and evaluation results.
6. n8n runs the agent on a schedule and sends a summary to stakeholders.

## 3. Build Order

Use this build order so each later phase has the inputs it needs:

1. Finalize scenario and scope
2. Gather and document data sources
3. Prepare and clean the data in Python
4. Generate KPI tables
5. Build the Streamlit/Plotly dashboard
6. Build the AI agent
7. Add LangSmith tracing and evaluation
8. Build the n8n workflow
9. Document costs, timeline, and setup

## 4. Step-By-Step Instructions

### Phase 1: Define Scope

#### Step 1. Lock the business scenario

Document the project as:

- Sector: Healthcare
- Company type: Mid-sized outpatient clinic or ambulatory care provider
- Business focus: appointment operations and clinic efficiency

Add this summary to `README.md` and the research notes so every artifact stays aligned.

#### Step 2. Lock the KPI focus

Use these five core topics throughout the project:

- appointment operations
- no-shows
- provider utilization
- wait times
- reminder effectiveness

These topics should appear consistently in the data model, dashboard visuals, agent outputs, LangSmith evaluation cases, and n8n summary.

### Phase 2: Data And Research Foundation

#### Step 3. Select the datasets

Gather:

- 1 main public dataset related to appointments, attendance, ambulatory visits, patient flow, or clinic operations
- 1 supporting dataset if needed
- synthetic rows or synthetic columns if key operational fields are missing

Prioritize fields that let us model:

- appointment date and time
- attendance or no-show behavior
- provider or clinic resource allocation
- visit duration or wait time
- reminder outreach

Place original files in `data/raw/`.

#### Step 4. Review the raw data structure

Before cleaning, inspect the dataset and record:

- file names
- row counts
- column names
- missing fields
- which fields need to be synthesized

Add these notes to `research/sector_research.md` or a preprocessing note in the README.

#### Step 5. Complete the research documents

Fill out the research files with project-specific content:

- `research/sector_research.md`
- `research/opportunities_risks.md`
- `research/use_cases.md`

Use this content:

`sector_research.md`

- outpatient clinic context
- common scheduling and attendance challenges
- healthcare operations KPIs
- AI adoption opportunities in non-clinical operations

`opportunities_risks.md`

- opportunities: scheduling optimization, staffing efficiency, reminder targeting, daily operations alerts
- risks: poor data quality, biased patterns, privacy concerns, low explainability, overreliance on AI

`use_cases.md`

- no-show pattern analysis
- provider utilization optimization
- daily operations insight generation

Checkpoint:

- we should have a clear business story, target users, and measurable operational KPIs before writing preprocessing logic

### Phase 3: Data Preparation In Python

#### Step 6. Set up the Python environment

Add the packages we expect to need to `requirements.txt`, such as:

- `pandas`
- `numpy`
- `python-dotenv`
- `openai` or another LLM SDK later
- `langsmith` later

Then create and activate a local environment and install the dependencies.

#### Step 7. Create a preprocessing script

Add a script file such as:

- `data_prep.py`

Its job will be to read the raw data and output clean files for both the dashboard and the agent.

#### Step 8. Standardize the input schema

When loading the raw dataset into pandas, map the columns into a consistent schema like:

- `appointment_id`
- `date`
- `weekday`
- `hour`
- `provider`
- `specialty`
- `attended`
- `no_show`
- `wait_time_min`
- `visit_duration_min`
- `reminder_sent`

If the source data lacks a field, create a documented synthetic version only where needed.

#### Step 9. Clean and transform the data

In the preprocessing script:

- remove duplicates
- handle null values
- normalize date and time formats
- create weekday and hour columns
- derive a reliable `no_show` flag
- convert duration fields to numeric values
- create reminder-related fields

Export the cleaned appointment-level dataset to:

- `data/processed/appointments_clean.csv`

#### Step 10. Build the KPI summary tables

Use the cleaned dataset to create these outputs:

- `data/processed/daily_kpis.csv`
- `data/processed/no_show_patterns.csv`
- `data/processed/provider_utilization.csv`
- `data/processed/reminder_effectiveness.csv`

Suggested logic:

`daily_kpis.csv`

- date
- total appointments
- attended appointments
- no-show rate
- average wait time
- average visit duration
- reminder coverage

`no_show_patterns.csv`

- weekday
- hour
- specialty
- no-show count
- no-show rate

`provider_utilization.csv`

- provider
- specialty
- daily appointment volume
- average visit duration
- estimated utilization rate

`reminder_effectiveness.csv`

- reminder sent vs not sent
- attendance rate
- no-show rate
- counts

Checkpoint:

- all four KPI files should load cleanly as CSVs and have column names suited for dashboard visuals

### Phase 4: Streamlit And Plotly Dashboard

#### Step 11. Draft the dashboard wireframe

Plan the main dashboard views before building visuals:

Page 1: Executive Overview

- total appointments
- no-show rate
- average wait time
- provider utilization
- reminder coverage
- weekly trend

Page 2: No-show Analysis

- no-show by weekday
- no-show by hour
- no-show by specialty
- reminder sent vs not sent

Page 3: Provider Utilization

- utilization by provider
- average visit duration
- demand vs capacity
- overloaded vs underused providers

Page 4: AI Insights Summary

- latest 3 to 5 agent insights
- severity or priority
- recommendation
- confidence
- timestamp

Record the page plan in `dashboard/dashboard_documentation.md`.

#### Step 12. Build the dashboard model

In Streamlit and Plotly:

1. Load the processed CSVs.
2. Review data types and display formats.
3. Create summary views that answer the key clinic operations questions.
4. Build visuals that are easy for a stakeholder to interpret in a live walkthrough.

Use:

- KPI cards
- line charts
- bar charts
- heatmaps or matrix visuals
- tables for agent insights

Save the working dashboard experience in:

- `streamlit_app.py`
- `dashboard/plotly_charts.py`

#### Step 13. Reserve the AI Insights input

Prepare the dashboard to later read:

- `data/processed/agent_insights_latest.csv`

Even if the file does not exist yet, document the expected columns now so the dashboard and agent stay aligned.

Checkpoint:

- the dashboard should already tell a useful operational story before the AI layer is added

### Phase 5: Build The Healthcare AI Agent

#### Step 14. Define the agent boundary

The agent is an operations analyst, not a clinician.

The agent may:

- analyze clinic operational KPIs
- identify patterns or anomalies
- suggest operational actions

The agent may not:

- diagnose conditions
- recommend treatment
- produce medical advice

Add this boundary to `agent/prompts.py` and the README.

#### Step 15. Expand the agent module structure

Add these files under `agent/`:

- `tools.py`
- `schemas.py`
- `prompts.py`
- `validators.py`
- `insights_generator.py`
- `run_agent.py`

Each file should have one clear responsibility.

#### Step 16. Implement deterministic analytics tools

In `agent/tools.py`, add functions such as:

- `calculate_no_show_rate()`
- `analyze_no_show_by_weekday_hour()`
- `provider_utilization_summary()`
- `detect_wait_time_anomalies()`
- `compare_reminder_effectiveness()`

These tools should only compute facts from the KPI tables and cleaned data.

#### Step 17. Define the structured output schema

In `agent/schemas.py`, define the required insight format with fields like:

- `title`
- `finding`
- `evidence`
- `likely_cause`
- `recommended_action`
- `priority`
- `confidence`
- `affected_metric`

This schema becomes the contract for both validation and dashboard ingestion.

#### Step 18. Create the prompt layer

In `agent/prompts.py`, write a system prompt that tells the model to:

- use only provided metrics
- focus on operations and staffing efficiency
- avoid clinical advice
- return structured output only
- make recommendations specific and actionable

#### Step 19. Generate the insights

In `agent/insights_generator.py`:

1. load KPI tables
2. call deterministic analytics tools
3. build a structured summary of facts
4. send that summary to the LLM
5. request the top 3 to 5 operational insights

#### Step 20. Validate the output

In `agent/validators.py`, check:

- all required fields exist
- evidence matches the input metrics
- recommendations are actionable
- no prohibited clinical content appears

Reject or flag outputs that do not pass validation.

#### Step 21. Save the latest insight file

In `agent/run_agent.py`, run the full pipeline and export the final results to:

- `data/processed/agent_insights_latest.csv`

Suggested columns:

- timestamp
- title
- finding
- evidence
- likely_cause
- recommended_action
- priority
- confidence
- affected_metric

Checkpoint:

- we should be able to run one script that creates a fresh insight CSV for the dashboard

### Phase 6: LangSmith Setup

#### Step 22. Add the LangSmith files

Create or expand:

- `langsmith/dataset_creation.py`
- `langsmith/evaluators.py`
- `langsmith/monitoring_setup.py`

#### Step 23. Set environment variables

Add the needed keys to `.env`, such as:

- `LANGSMITH_API_KEY`
- `OPENAI_API_KEY` or your selected LLM provider key

Do not commit real keys.

#### Step 24. Create an evaluation dataset

Build 10 to 20 scenarios representing realistic clinic operations cases, such as:

- unusually high Monday no-show rate
- low reminder coverage
- a provider with overloaded utilization
- a sharp increase in wait times

Each evaluation record should include:

- structured input metrics
- expected insight focus
- expected recommendation category

#### Step 25. Trace agent runs

Capture in LangSmith:

- prompt text
- KPI input payload
- tool calls
- model output
- validation status
- run metadata

#### Step 26. Implement evaluators

In `langsmith/evaluators.py`, add evaluators for:

- schema validity
- groundedness
- actionability
- safety boundary compliance

#### Step 27. Save monitoring evidence

For final presentation, collect:

- one trace example
- one evaluator result example
- one failure or guardrail example

Store screenshots, exports, or notes in `langsmith/monitoring_results/`.

Checkpoint:

- we should be able to prove that the AI layer is observable, constrained, and auditable

### Phase 7: n8n Workflow

#### Step 28. Design the automation use case

Use one simple workflow:

- Daily Clinic Operations Summary

Business goal:

- send a daily operational summary to a clinic manager or operations lead

#### Step 29. Build the workflow logic

In n8n, create this flow:

1. Schedule trigger at 08:00 daily
2. Run the Python agent script or call a webhook
3. Read the latest structured insights
4. format an email-friendly summary
5. send the summary
6. optionally log high-priority issues to Google Sheets, Notion, or a database

#### Step 30. Export and document the workflow

Save the workflow export to:

- `n8n/Appointment Reminders and Follow-ups (Airtable + Gmail + Telegram).json`

Document the workflow in:

- `n8n/workflow_documentation.md`

Include:

- purpose
- trigger
- steps
- sample output
- business value

Checkpoint:

- the workflow should clearly show how insights become action

### Phase 8: Cost And Timeline Estimation

#### Step 31. Build the cost estimate

In `cost_estimation/cost_analysis.md`, estimate:

- data preparation effort
- dashboard build effort
- AI agent development effort
- n8n workflow setup effort
- LangSmith monitoring effort
- API usage costs
- infrastructure assumptions

Keep the estimate realistic for an SME clinic MVP.

#### Step 32. Build the timeline estimate

In `cost_estimation/timeline_estimate.md`, use a phased schedule like:

- weeks 1 to 2: discovery and data
- weeks 3 to 4: dashboard MVP
- weeks 5 to 6: agent MVP
- week 7: n8n workflow
- week 8: monitoring, testing, and packaging

### Phase 9: Final Packaging

#### Step 33. Finalize the README

Update `README.md` so it explains:

- the project scenario
- architecture overview
- folder structure
- setup steps
- how to run preprocessing
- how to run the agent
- what the dashboard shows
- what the n8n workflow does
- how LangSmith is used

#### Step 34. Do a final walkthrough

Before submission, verify:

1. raw and processed data files are present
2. research docs are complete
3. the Streamlit dashboard opens and uses the processed CSVs
4. the agent runs and exports `agent_insights_latest.csv`
5. LangSmith traces and evaluator results exist
6. the n8n workflow export and documentation are saved
7. cost and timeline estimates are complete
8. the README explains how the whole project fits together

## 5. Recommended Execution Sequence For Us

To keep momentum, we should build in this order:

1. Fill the research docs and confirm the exact dataset
2. Implement the Python preprocessing pipeline
3. Generate the four KPI CSV outputs
4. Build the Streamlit/Plotly dashboard views
5. Build and test the agent locally
6. Add LangSmith tracing and evaluators
7. Create the n8n workflow
8. Finish cost, timeline, and README packaging

## 6. Definition Of Done

The project is complete when:

- the Streamlit dashboard shows clinic operations KPIs and trends
- the agent produces safe, structured operational insights
- LangSmith can trace and evaluate those outputs
- n8n can deliver a daily summary workflow
- the repository includes clear documentation and implementation estimates
