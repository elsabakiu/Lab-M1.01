from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    discord_bot_token: str
    discord_guild_id: int
    discord_channel_id: int
    n8n_webhook_url: str
    ignore_bots: bool
    log_level: str


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")

    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    guild_id_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
    channel_id_raw = os.getenv("DISCORD_CHANNEL_ID", "").strip()
    webhook_url = os.getenv("N8N_WEBHOOK_URL", "").strip()
    ignore_bots = _parse_bool(os.getenv("IGNORE_BOTS"), default=True)
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"

    missing = []
    if not token:
        missing.append("DISCORD_BOT_TOKEN")
    if not guild_id_raw:
        missing.append("DISCORD_GUILD_ID")
    if not channel_id_raw:
        missing.append("DISCORD_CHANNEL_ID")
    if not webhook_url:
        missing.append("N8N_WEBHOOK_URL")
    if missing:
        missing_keys = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {missing_keys}")

    try:
        guild_id = int(guild_id_raw)
    except ValueError as exc:
        raise ValueError("DISCORD_GUILD_ID must be a valid integer.") from exc

    try:
        channel_id = int(channel_id_raw)
    except ValueError as exc:
        raise ValueError("DISCORD_CHANNEL_ID must be a valid integer.") from exc

    return Settings(
        discord_bot_token=token,
        discord_guild_id=guild_id,
        discord_channel_id=channel_id,
        n8n_webhook_url=webhook_url,
        ignore_bots=ignore_bots,
        log_level=log_level,
    )
