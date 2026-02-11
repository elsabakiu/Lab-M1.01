# Week 2 - Day 3 Project Structure

## Folder Layout

```
Day 3/
├── app/                     # Main application code
│   ├── api_calling_JSON_refactored_main.py
│   ├── openai_client_utils.py
│   ├── refactor_helpers.py
│   └── logging_utils.py
├── tests/                   # Unit tests
│   └── test_refactor_helpers.py
├── data/                    # Input/sample data
│   └── example_json/
├── outputs/                 # Generated artifacts
│   ├── generated_listings/
│   └── logs/
├── docs/                    # Prompts, issues, reports, screenshots
│   ├── api_calling_JSON_refactored_issues.md
│   ├── reusable_refactoring_prompt.md
│   ├── report/
│   └── screenshots/
└── notebooks/               # Notebook versions
    └── api_calling_JSON_refactored.ipynb
```

## How To Run

From `Weekly Assignments/WEEK 2/Day 3`:

```bash
../../.venv/bin/python -m app.api_calling_JSON_refactored_main
```

Run JSON validation only:

```bash
../../.venv/bin/python -m app.api_calling_JSON_refactored_main json-demo --json-dir data/example_json
```

Run tests:

```bash
../../.venv/bin/python -m unittest -v tests/test_refactor_helpers.py
```
