# BI Dashboard Project

Healthcare operations analytics project for a mid-sized outpatient clinic. The repository combines public appointment data, KPI preprocessing, an AI insights layer, workflow automation, and a Streamlit dashboard for stakeholder demos.

For the full build sequence and business framing, use `implementation_guide.md`.

## Structure

- `data/raw/`: original source datasets
- `data/processed/`: cleaned and transformed datasets
- `research/`: sector analysis, risks, and use case definition
- `dashboard/`: Plotly dashboard assets and documentation
- `n8n/`: workflow export and workflow notes
- `agent/`: optional Python agent components
- `langsmith/`: evaluation and monitoring setup
- `cost_estimation/`: delivery cost and timeline documents

## Scenario

- Sector: Healthcare
- Company size: Medium SME
- Business focus: outpatient appointment operations, no-shows, reminder effectiveness, and provider utilization

## Submission Narrative

This project intentionally uses Plotly and Streamlit as the dashboard delivery layer.

That choice was made because Plotly/Streamlit makes the dashboard:

- easier to demo in a live meeting without requiring a desktop BI tool
- easier to version in Git alongside the Python preprocessing and AI logic
- easier to combine with AI Q&A, risk scoring, and workflow triggers in a single interface
- better suited to an interactive stakeholder walkthrough where narrative and action matter as much as charts

The intended submission experience is the Streamlit application backed by Plotly visualizations.

## Transparency Framing

To avoid a black-box presentation, the dashboard separates content into:

- `Observed data`: funnel, no-show, utilization, lead time, and reminder views derived from processed clinic data
- `AI-generated insight`: chatbot answers, AI insight cards, and risk prioritization
- `Modeled estimate`: ROI scenarios, use-case comparisons, and business impact projections

This framing helps Chloe understand what is measured, what is AI-produced, and what is a planning estimate.

## LangSmith Visibility

The live app now surfaces LangSmith directly in the AI impact tab through a `Latest Trace Status` panel.

That panel explains:

- what gets logged
- whether tracing is enabled
- which LangSmith project and dataset are active
- which recent evaluation experiment was recorded

Reference monitoring artifacts:

- [latest_monitoring_run.md](/Users/elsa/Documents/Dropbox/Work%20Projects/AI%20Consulting%20Training/Weekly%20Assignments/WEEK%207/BI%20Project/bi-dashboard-project/langsmith/monitoring_results/latest_monitoring_run.md)
- [latest_monitoring_run.json](/Users/elsa/Documents/Dropbox/Work%20Projects/AI%20Consulting%20Training/Weekly%20Assignments/WEEK%207/BI%20Project/bi-dashboard-project/langsmith/monitoring_results/latest_monitoring_run.json)

## Reproducible Setup

Run these commands from the project root:

1. Create and activate a virtual environment:

`python3 -m venv .venv`

`source .venv/bin/activate`

2. Install dependencies:

`pip install -r requirements.txt`

3. Rebuild the processed KPI files from the raw dataset:

`python data/data_prep.py`

4. Generate the latest AI insights export:

`python agent/run_agent.py`

5. Start the dashboard:

`streamlit run streamlit_app.py`

Optional:

- train or refresh the no-show risk model with `python agent/train_model.py`
- generate the daily risk board with `python agent/run_daily_risk.py`
- enable OpenAI wording enhancement by setting `ENABLE_OPENAI_ENHANCEMENT=true` in `.env`

## Suggested Workflow

1. Place source files in `data/raw/`.
2. Run `python data/data_prep.py` to generate the processed dashboard CSVs.
3. Document research findings in `research/`.
4. Build or refine the dashboard experience in Streamlit/Plotly.
5. Export automation flows into the documented n8n JSON artifact under `n8n/`.
6. Add any optional agent logic under `agent/`.
7. Track evaluation and monitoring assets under `langsmith/`.
8. Estimate effort and costs in `cost_estimation/`.

## Dashboard Inputs

Run:

`python data/data_prep.py`

This creates the CSV files the Streamlit dashboard, Plotly views, and agent use from `data/processed/`:

- `appointments_clean.csv`
- `daily_kpis.csv`
- `no_show_patterns.csv`
- `provider_utilization.csv`
- `reminder_effectiveness.csv`

## AI Agent

Run:

`python agent/run_agent.py`

This creates:

- `data/processed/agent_insights_latest.csv`

The agent uses deterministic analytics over the processed KPI files by default. It can optionally enhance the wording with OpenAI when both `OPENAI_API_KEY` and `ENABLE_OPENAI_ENHANCEMENT=true` are present in `.env`.

## Streamlit Dashboard

Run:

`streamlit run streamlit_app.py`

The app is the intended final dashboard submission. It gives users a chat-style question-and-answer interface on top of the same processed files used by the dashboard and the agent export.

Features:

- conversational history with follow-up questions
- preset buttons for common operational questions
- Plotly visualizations designed for stakeholder readability
- a ClinicIQ workspace layout for reviewing KPIs, AI insights, and workflow triggers
