# MCP + LangChain Agent (Week 3 / Day 5)

This project is a Python MCP client + LangChain agent demo that connects to:

- Google Calendar MCP server (`@cocal/google-calendar-mcp`)
- Google Drive MCP server (`@modelcontextprotocol/server-gdrive`)

It demonstrates:

- loading MCP tools through `MultiServerMCPClient`
- printing a per-server inventory of tools/resources
- running an agent with real calendar + drive tool usage
- simulating a practical 2-turn workflow (check tomorrow events, then create a constrained blocker)

## Project structure

- `mcp_langchain.py`: thin entrypoint wrapper
- `mcp_app/app.py`: main runtime orchestration
- `mcp_app/config.py`: environment loading + MCP server connection config
- `mcp_app/mcp_helpers.py`: tool/resource loading, inventory printing, helper utilities
- `mcp_app/calendar_logic.py`: non-agent helper checks (smoke test, today event listing)
- `mcp_app/agent_flows.py`: agent prompts, tests, and conversation simulation
- `.env`: local runtime configuration
- `.env.example`: template configuration

## Requirements

- Python 3.11+
- Node.js + npm (`npx` required)
- Google OAuth client JSON file (Desktop app type)
- Python deps in `requirements.txt`

Install Python deps:

```bash
python -m pip install -r requirements.txt
```

## Environment setup

Configure `WEEK 3/Day 5/.env`.

Minimum required values:

- `OPENAI_API_KEY`
- `OAUTH_CREDENTIALS_PATH` (path to Google OAuth client JSON)

Calendar MCP:

- `MCP_SERVER_COMMAND=npx`
- `MCP_SERVER_ARGS=@cocal/google-calendar-mcp`

Drive MCP:

- `ENABLE_GDRIVE_MCP=true`
- `GDRIVE_MCP_COMMAND=npx`
- `GDRIVE_MCP_ARGS="-y @modelcontextprotocol/server-gdrive@2025.1.14"`
- `GDRIVE_OAUTH_PATH` (optional if central `OAUTH_CREDENTIALS_PATH` is set)
- `GDRIVE_CREDENTIALS_PATH` (token output path)

## Run

From `WEEK 3/Day 5`:

```bash
python mcp_langchain.py
```

or directly:

```bash
python mcp_app/app.py
```

## What happens at runtime

1. Loads `.env` and validates key paths
2. Builds MCP connections for Calendar + Drive
3. Loads tools via `MultiServerMCPClient`
4. Prints server inventory:
   - tools for each server
   - resources (or resource errors if unsupported)
5. Runs agent simulation

## Current agent scenario

In `simulate_calendar_conversation`:

- **Turn 1**: retrieve tomorrow’s calendar events
- **Turn 2**: create a 1-hour blocker for tomorrow with constraints:
  - no overlap
  - within 08:00–20:00
  - use Google Drive file `ACFT02_AI Dictionary.pptx` (PDF attach/link fallback)

This is implemented as a prompt-driven (agentic) flow, not a hard-coded scheduling function.

## Known caveats / troubleshooting

### 1) `resources_error` on `google_calendar`

Expected in many setups. Calendar MCP commonly exposes tools but not MCP resources.

### 2) `invalid_request` during Drive tool calls

If Turn 2 fails with `invalid_request`, it is usually Drive server/runtime/tool compatibility, not basic Calendar auth. Verify:

- Drive OAuth/token validity
- correct Drive MCP package/version
- tool argument schema compliance

### 3) `Failed to parse JSONRPC message from server`

This indicates a server writing non-JSON logs to stdout (breaks MCP stdio framing). Use a server/version that is MCP-stdio clean.

### 4) `No module named langchain_mcp_adapters`

Install/update dependencies in the active environment.

## Notes on client lifecycle

This code uses `MultiServerMCPClient` directly (no async context manager), because installed adapter versions may not support context manager usage uniformly.

## Next improvements

- Add robust preflight checks per tool schema before agent run
- Add server capability registry (which server supports resources vs tools)
- Add structured logs and save run traces under `output/`
