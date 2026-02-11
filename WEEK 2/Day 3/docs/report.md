# Refactoring Brief Report (Path 1: My Own Code from Lab 6)

## 1) What I Refactored
I refactored the original notebook-style workflow into a structured Python project with clear module boundaries and reusable components.

Main changes:
- Moved from one large script/notebook flow to package-based modules.
- Separated business logic, API integration, validation, logging, and helpers.
- Reorganized project folders for readability and maintainability.

Current structure:
- `app/`: application modules
- `tests/`: unit tests
- `data/`: sample JSON input files
- `outputs/`: generated listings and logs
- `docs/`: prompts, issue checklist, report assets
- `notebooks/`: original notebook artifact

## 2) Helper Functions Created
Core helper functions (in `app/refactor_helpers.py`):
- `load_json_file`
- `safe_json_loads`, `parse_json_strict`, `extract_first_json_object`
- `validate_product_payload`, `validate_listing_payload`
- `build_listing_prompt`
- `parse_listing_response`, `parse_listing_json`
- `format_validation_error`
- `normalize_string_list`
- `build_result_record`
- Error utilities: `build_error_message`, `get_traceback_location`, `report_error`

OpenAI utility helpers (in `app/openai_client_utils.py`):
- `build_env_candidates`, `resolve_env_path`
- `load_environment_variables`
- `read_openai_api_key`
- `build_openai_wrapper`

## 3) How I Modularized the Code
I split responsibilities into focused modules:
- `app/api_calling_JSON_refactored_main.py`: orchestration and CLI commands.
- `app/refactor_helpers.py`: shared validation, parsing, formatting, and reusable helper logic.
- `app/openai_client_utils.py`: reusable OpenAI wrapper with retries and standardized API error handling.
- `app/logging_utils.py`: centralized logging configuration (file + console handlers).

I also introduced:
- `OpenAIWrapper` class with exponential backoff retry behavior.
- Standardized error payloads (`OpenAIWrapperError.details`) for API failures.
- Config classes (`BatchConfig`, `BatchPaths`) for cleaner parameter flow.

## 4) Error Handling Before/After (Examples)
### A) Missing file error (JSON input)
Before:
- Errors could appear in multiple places (duplicate noisy output).
- Context and suggestions were inconsistent.

After:
- Single clear message from file-loading layer + structured return object.
- Example output:
```text
ERROR in load_json_file(): FileNotFoundError
  Location: path=example_json/missing.json; source=.../pathlib.py:1110
  Message: [Errno 2] No such file or directory: 'example_json/missing.json'
  Suggestion: Check that the file path is correct and the file exists.
```
Returned:
```json
{"error":"file_not_found","message":"[Errno 2] No such file or directory: 'example_json/missing.json'"}
```

### B) Invalid JSON syntax
Before:
- Parser failures were less structured.

After:
- Includes line/column + fix suggestion.
```text
ERROR in load_json_file(): JSONDecodeError
  Location: path=..., line=1, column=11
  Message: Expecting property name enclosed in double quotes
  Suggestion: Fix JSON syntax at the shown line/column.
```

### C) API failure / rate limit
After:
- Wrapper retries automatically and then raises standardized error details:
```json
{
  "error": {
    "type": "RuntimeError",
    "message": "simulated rate limit",
    "model": "gpt-4.1-mini",
    "attempt": 2,
    "max_retries": 2,
    "context": {}
  }
}
```

## 5) Challenges Faced
- Converting notebook-style sequential code into reusable modules without breaking behavior.
- Avoiding duplicate error reporting while still preserving useful debug context.
- Updating imports and default paths after folder restructuring.
- Understanding the code after different steps of the refactoring processs

## 6) What I Learned
- Strong separation of concerns makes refactoring and testing much easier.
- A thin orchestration layer + reusable helpers reduces repetition and bugs.
- Standardized error shapes improve debugging and user-facing clarity.
- Logging is essential for auditability in data + API pipelines.
- Folder structure matters: clean organization improves onboarding, maintenance, and collaboration.
- BUT, at the end I can read the code with more difficulty and understand it less then before :) 
