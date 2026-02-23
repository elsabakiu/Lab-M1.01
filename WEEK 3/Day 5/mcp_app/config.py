from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ConnectionConfig = dict[str, Any]


def build_server_env() -> dict[str, str]:
    """Build env vars passed to the MCP server subprocess."""
    env = os.environ.copy()
    # This keeps npm/node deprecation noise out of terminal output.
    env.setdefault("NODE_NO_WARNINGS", "1")
    return env


def mask_key(key: str) -> str:
    """Hide most of an API key when printing logs."""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


def load_environment() -> tuple[str | None, str | None]:
    """Load .env and print key configuration checks for the user."""
    day5_dir = Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=day5_dir / ".env", override=True)
    load_dotenv()

    openai_key = os.getenv("OPENAI_API_KEY")
    central_oauth_path = os.getenv("OAUTH_CREDENTIALS_PATH")

    # If a central credential path is defined, map it to service-specific vars.
    if central_oauth_path:
        os.environ["GOOGLE_OAUTH_CREDENTIALS"] = central_oauth_path

    oauth_path = os.getenv("GOOGLE_OAUTH_CREDENTIALS")

    if openai_key:
        print(f"OPENAI_API_KEY detected: {mask_key(openai_key)}")
    else:
        print("OPENAI_API_KEY is not set.")

    if oauth_path:
        resolved = Path(oauth_path).expanduser()
        exists_text = "exists" if resolved.exists() else "missing file"
        print(f"GOOGLE_OAUTH_CREDENTIALS: {resolved} ({exists_text})")
    else:
        print("GOOGLE_OAUTH_CREDENTIALS is not set.")

    return openai_key, oauth_path


def build_calendar_connection() -> ConnectionConfig:
    """Build a stdio MCP connection config for Google Calendar."""
    command = os.getenv("MCP_SERVER_COMMAND", "npx").strip()
    args_raw = os.getenv("MCP_SERVER_ARGS", "@cocal/google-calendar-mcp").strip()
    args = shlex.split(args_raw)
    if not args:
        raise ValueError("MCP_SERVER_ARGS cannot be empty.")

    return {
        "transport": "stdio",
        "command": command,
        "args": args,
        "env": build_server_env(),
    }


def is_enabled(value: str | None, default: bool = False) -> bool:
    """Parse bool-like env values."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_drive_connection() -> ConnectionConfig:
    """Build a stdio MCP connection config for Google Drive."""
    command = os.getenv("GDRIVE_MCP_COMMAND", "npx").strip()
    args_raw = os.getenv(
        "GDRIVE_MCP_ARGS", "-y @modelcontextprotocol/server-gdrive@2025.1.14"
    ).strip()
    args = shlex.split(args_raw)
    if not args:
        raise ValueError("GDRIVE_MCP_ARGS cannot be empty.")

    drive_env = build_server_env()

    central_oauth = os.getenv("OAUTH_CREDENTIALS_PATH")
    if central_oauth:
        drive_env.setdefault("GDRIVE_OAUTH_PATH", central_oauth)

    drive_env.setdefault(
        "GDRIVE_CREDENTIALS_PATH",
        str(Path.home() / ".config" / ".gdrive-server-credentials.json"),
    )

    return {
        "transport": "stdio",
        "command": command,
        "args": args,
        "env": drive_env,
    }


def build_connections() -> dict[str, ConnectionConfig]:
    """Build MCP connections for calendar and optional Google Drive."""
    connections: dict[str, ConnectionConfig] = {
        "google_calendar": build_calendar_connection()
    }

    drive_enabled_default = bool(
        os.getenv("GDRIVE_OAUTH_PATH")
        or os.getenv("GDRIVE_CREDENTIALS_PATH")
        or os.getenv("OAUTH_CREDENTIALS_PATH")
    )
    drive_enabled = is_enabled(
        os.getenv("ENABLE_GDRIVE_MCP"), default=drive_enabled_default
    )
    if drive_enabled:
        connections["google_drive"] = build_drive_connection()

    return connections
