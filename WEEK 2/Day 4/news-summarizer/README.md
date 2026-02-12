# News Summarizer

A CLI app that fetches headlines from NewsAPI and GDELT, summarizes each article with OpenAI, analyzes sentiment with Cohere, and prints a report with per-run token/cost usage.

## What The Project Does

- Fetches latest headlines by category/query from multiple sources (NewsAPI + GDELT).
- Summarizes each article in 2-3 sentences.
- Runs sentiment analysis on each generated summary.
- Supports sync and async processing modes.
- Tracks token usage and estimated cost for every LLM request.
- Applies provider rate limiting, retry logic, and basic fallback behavior.

## Project Structure

- `src/news_summarizer/main.py`: interactive CLI entrypoint.
- `src/news_summarizer/clients/news_api.py`: NewsAPI client + normalization.
- `src/news_summarizer/clients/gdelt_api.py`: GDELT client + normalization.
- `src/news_summarizer/services/summarizer.py`: sync/async orchestration and report generation.
- `src/news_summarizer/providers/llm_providers.py`: OpenAI/Cohere calls, retries, budget checks, and cost tracking.
- `tests/`: unit tests.

## Setup

## 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure environment variables

Create or update `.env` in the project root.

Required:

- `OPENAI_API_KEY`
- `COHERE_API_KEY`
- `NEWS_API_KEY`

Common optional settings (defaults shown in code):

- `OPENAI_MODEL=gpt-4o-mini`
- `COHERE_MODEL=command-a-03-2025`
- `DAILY_BUDGET=5.00`
- `MAX_RETRIES=3`
- `REQUEST_TIMEOUT=30`
- `OPENAI_RPM=500`
- `COHERE_RPM=50`
- `NEWS_API_RPM=100`
- `GDELT_RPM=120`
- `GDELT_DEFAULT_QUERY=AI`

## How To Run

From the project root:

```bash
PYTHONPATH=src python -m news_summarizer.main
```

You will be prompted for:

- News category
- Number of articles (1-10)
- Whether to use async processing

## Run Tests

```bash
python -m pytest
```

## Example Output

```text
================================================================================
NEWS SUMMARIZER - Multi-Provider Edition
================================================================================

Enter news category (technology/business/health/general): technology
How many articles to process? (1-10): 2
Use async processing? (y/n): n

Fetching 2 articles from category: technology

Processing 2 articles...

Processing: AI startup launches a new coding assistant...
  -> Summarizing with OpenAI...
  ✓ Summary generated
  -> Analyzing sentiment with Cohere...
  ✓ Sentiment analyzed

Processing: Semiconductor demand rises in Q1...
  -> Summarizing with OpenAI...
  ✓ Summary generated
  -> Analyzing sentiment with Cohere...
  ✓ Sentiment analyzed

================================================================================
NEWS SUMMARY REPORT
================================================================================

1. AI startup launches a new coding assistant
   Source: Example News | Published: 2026-02-12T10:22:00Z
   URL: https://example.com/article-1

   SUMMARY:
   The article explains...

   SENTIMENT:
   Overall sentiment is positive with moderate confidence...

--------------------------------------------------------------------------------

2. Semiconductor demand rises in Q1
   Source: Example Daily | Published: 2026-02-12T08:05:00Z
   URL: https://example.com/article-2

   SUMMARY:
   The report states...

   SENTIMENT:
   Overall sentiment is neutral to positive...

--------------------------------------------------------------------------------

================================================================================
COST SUMMARY
================================================================================
Total requests: 4.0
Total cost: $0.0018
Total tokens: 2,945.0
  Input: 2,410.0
  Output: 535.0
Average cost per request: $0.000450
================================================================================
```

## Cost Analysis

Cost estimation is implemented in `src/news_summarizer/providers/llm_providers.py`.

### Pricing model

The app stores model pricing as USD per 1M tokens:

- `gpt-4o-mini`: input `$0.15`, output `$0.60`
- `gpt-4o`: input `$2.50`, output `$10.00`
- `command-a-03-2025`: input `$2.50`, output `$10.00`
- `command-r`: input `$0.50`, output `$1.50`
- `command-r-plus`: input `$3.00`, output `$15.00`

If a model is not listed, fallback pricing is used:

- input `$3.00` / 1M tokens
- output `$15.00` / 1M tokens

### Per-request formula

```text
input_cost  = (input_tokens  / 1,000,000) * input_price
output_cost = (output_tokens / 1,000,000) * output_price
total_cost  = input_cost + output_cost
```

### Budget behavior

- Every LLM call is tracked in `CostTracker`.
- If total spend reaches or exceeds `DAILY_BUDGET`, a `BudgetExceededError` is raised.
- A warning is logged when usage reaches 90% of budget.

## Notes

- The async mode parallelizes article processing, but each LLM call is still made through the same provider clients.
- The report is console-based; no persistent database is required.
