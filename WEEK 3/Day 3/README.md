# Normal Objects LangChain Agent (Week 3 / Day 3)

This lab builds a creative, tool-using LangChain agent for the Normal Objects universe.

## What this project includes
- Custom themed tools:
  - `consult_demogorgon`
  - `check_hawkins_records`
  - `cast_interdimensional_spell`
  - `gather_party_wisdom`
- An agent with a creative system prompt and flexible tool chaining
- A complaint handler demo (runs at least 3 complaints)
- Tool usage tracking and chaining analysis
- Brief analysis report

## Project structure
- `src/normalobjects_langchain.py`: main Day 3 implementation
- `src/main.py`: minimal hello LangChain scaffold
- `docs/report/report.md`: brief analysis document
- `requirements.txt`: Python dependencies

## Setup
1. Create and activate a Python virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment:
   - Ensure `OPENAI_API_KEY` is available in your shell or `.env`.

## Run the Day 3 lab agent
From `WEEK 3/Day 3`:

```bash
python src/normalobjects_langchain.py
```

## What the script does at runtime
1. Loads environment variables (`OPENAI_API_KEY` required).
2. Builds and prints creative tool inventory.
3. Creates the LangChain agent with the custom system prompt.
4. Runs a sample anomaly message.
5. Runs complaint tests for the first 4 complaints from the predefined list.
6. Prints tool-usage statistics and chaining examples.

## Submission mapping
- Complete Python agent implementation: `src/normalobjects_langchain.py`
- Demonstration with complaints + creative responses: terminal output from script run
- Tool usage patterns: printed by `ToolUsageTracker`
- Brief analysis document:
  - `docs/report/report.md`
