# MCP + LangChain Agent (Week 3 / Day 5)

This project is a multi-server MCP client and LangChain agent demo.

It connects to:
- Google Calendar MCP (`@cocal/google-calendar-mcp`)
- Google Drive MCP (`@modelcontextprotocol/server-gdrive@2025.1.14`)

and demonstrates:
- loading tools from multiple MCP servers via `MultiServerMCPClient`
- printing a structured server inventory (tools + resources per server)
- running an agentic calendar workflow that also attempts Drive lookup

## Project structure
- `mcp_langchain.py`: top-level entrypoint
- `mcp_app/app.py`: main orchestration (connect, inventory, run agent flow, teardown)
- `mcp_app/config.py`: `.env` loading + server connection builders
- `mcp_app/mcp_helpers.py`: tool loading, inventory printing, tool filtering, client teardown
- `mcp_app/agent_flows.py`: agent tests and 2-turn simulated conversation
- `mcp_app/calendar_logic.py`: optional non-agent calendar checks
- `.env`: local runtime configuration
- `.env.example`: template values

## Requirements
- Python 3.11+
- Node.js + npm (`npx`)
- Google OAuth client JSON (Desktop app credentials)
- Python dependencies from `requirements.txt`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Environment configuration
Set values in `WEEK 3/Day 5/.env`.

Core:
- `OPENAI_API_KEY`
- `OAUTH_CREDENTIALS_PATH=/absolute/path/to/google-client-secret.json`

Calendar MCP:
- `MCP_SERVER_COMMAND=npx`
- `MCP_SERVER_ARGS=@cocal/google-calendar-mcp`
- `GOOGLE_CALENDAR_ACCOUNT=normal` (recommended if your account alias is `normal`)

Drive MCP:
- `ENABLE_GDRIVE_MCP=true`
- `GDRIVE_MCP_COMMAND=npx`
- `GDRIVE_MCP_ARGS="-y @modelcontextprotocol/server-gdrive@2025.1.14"`
- `GDRIVE_OAUTH_PATH` (optional when `OAUTH_CREDENTIALS_PATH` is set)
- `GDRIVE_CREDENTIALS_PATH` (optional; defaults to `~/.config/.gdrive-server-credentials.json`)

Notes:
- `OAUTH_CREDENTIALS_PATH` is treated as the central credentials file and mapped to server-specific env vars where needed.
- `config.py` suppresses Node warning noise with `NODE_NO_WARNINGS=1` for cleaner logs.

## Run
From `WEEK 3/Day 5`:

```bash
python mcp_langchain.py
```

or:

```bash
python mcp_app/app.py
```

## Runtime behavior
`mcp_app/app.py` performs:
1. Load environment and print key config checks.
2. Build MCP server connection configs (calendar + optional drive).
3. Initialize `MultiServerMCPClient`.
4. Load tools once and filter out unsafe account-management tool for agent usage.
5. Print inventory per server:
   - `tools_count` and tool names
   - `resources_count` and resource URIs (or `resources_error`)
6. Verify LangChain tool interfaces (`invoke`, `ainvoke`).
7. Run simulated 2-turn agent conversation.
8. Execute explicit best-effort MCP teardown (`close_mcp_client`).

## Agent flow in this project
Current simulation (`simulate_calendar_conversation`) runs:
- Turn 1: “Retrieve my calendar events for tomorrow.”
- Turn 2: “Create a 1-hour ‘Review AI concepts’ event tomorrow in earliest free slot (08:00-20:00), no overlap, and use Drive file `ACFT02_AI Dictionary.pptx` with PDF attach/link fallback.”

If Turn 2 fails, a retry prompt is sent with stricter schema-safe instructions.

## Known limitations
1. `google_calendar` may report resource-listing errors.
Calendar server typically exposes tools, not MCP resources. This is expected.

2. Drive tool calls may fail with `invalid_request`.
This is usually due to server/tool schema/runtime mismatch, not calendar auth.

3. Some MCP servers break stdio framing.
If a server writes plain text logs to stdout, MCP JSON-RPC parsing fails.

4. Adapter API differences by version.
`close_mcp_client` uses best-effort teardown (`aclose`, `close`, or fallback message).

## Troubleshooting checklist
- Confirm Python env has `langchain-mcp-adapters`, `langchain-openai`, `mcp`, `python-dotenv`.
- Confirm `npx` works in shell (`npx --version`).
- Confirm OAuth path exists and points to a valid desktop OAuth JSON.
- Re-auth Drive/Calendar server if token files are missing or stale.
- Ensure `GOOGLE_CALENDAR_ACCOUNT` matches a real account alias returned by your calendar MCP.
