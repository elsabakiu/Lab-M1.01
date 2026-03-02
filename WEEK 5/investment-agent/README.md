# Autonomous Investment Research Agent (Iteration 1)

Local end-to-end autonomous investment workflow with:

- Fixed universe config (30 symbols)
- 3 API tools (market data, fundamentals, news)
- LangGraph orchestration with conditional retries
- ReAct-style evidence loop
- Quality + Momentum strategy engines
- JSON + Markdown report output per ticker
- Batch ranking summary (top picks + watchlist)

## Project structure

```
investment-agent/
  config/
    universe.yaml
  runs/
  src/investment_agent/
    config.py
    state.py
    schemas.py
    runner.py
    tools/
    strategies/
    workflow/
    reporting/
  tests/
  requirements.txt
```

## Setup

```bash
cd "WEEK 5/investment-agent"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Configure these in `WEEK 5/.env`:

- `MARKET_DATA_API_BASE_URL`
- `MARKET_DATA_API_KEY`
- `FUNDAMENTALS_API_BASE_URL`
- `FUNDAMENTALS_API_KEY`
- `NEWS_API_BASE_URL`
- `NEWS_API_KEY`

Optional:

- `HTTP_TIMEOUT_SECONDS` (default `15`)
- `HTTP_MAX_RETRIES` (default `3`)
- `HTTP_BACKOFF_SECONDS` (default `1.0`)

## Run single ticker

```bash
PYTHONPATH=src python -m investment_agent.runner --ticker AAPL
```

## Run batch

```bash
PYTHONPATH=src python -m investment_agent.runner --batch
```

Optional cap:

```bash
PYTHONPATH=src python -m investment_agent.runner --batch --max-symbols 10
```

## Output files

Each run writes to `runs/<timestamp>/`.

Single ticker run:

- `runs/<timestamp>/<TICKER>/state.json`
- `runs/<timestamp>/<TICKER>/report.json`
- `runs/<timestamp>/<TICKER>/report.md`
- `runs/<timestamp>/<TICKER>/react_trace.md`

Batch run also writes:

- `runs/<timestamp>/ranked_summary.json`
- `runs/<timestamp>/ranked_summary.md`

## Tests

```bash
PYTHONPATH=src pytest -q
```
