from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[2]
_WEEK5_ROOT = _THIS_FILE.parents[3]

# Load nearest/default .env first, then explicit Week 5 paths if present.
load_dotenv()
load_dotenv(_WEEK5_ROOT / ".env")
load_dotenv(_PROJECT_ROOT / ".env")


class HttpSettings(BaseModel):
    timeout_seconds: int = Field(default=15, ge=1, le=120)
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_seconds: float = Field(default=1.0, ge=0.0, le=30.0)


class ApiSettings(BaseModel):
    base_url: str = ""
    api_key: str = ""


class AppConfig(BaseModel):
    http: HttpSettings
    market_data: ApiSettings
    fundamentals: ApiSettings
    news: ApiSettings


def load_config() -> AppConfig:
    def env(name: str, default: str = "") -> str:
        return os.getenv(name, default).strip()

    return AppConfig(
        http=HttpSettings(
            timeout_seconds=int(env("HTTP_TIMEOUT_SECONDS", "15")),
            max_retries=int(env("HTTP_MAX_RETRIES", "3")),
            backoff_seconds=float(env("HTTP_BACKOFF_SECONDS", "1.0")),
        ),
        market_data=ApiSettings(
            base_url=env("MARKET_DATA_API_BASE_URL"),
            api_key=env("MARKET_DATA_API_KEY"),
        ),
        fundamentals=ApiSettings(
            base_url=env("FUNDAMENTALS_API_BASE_URL"),
            api_key=env("FUNDAMENTALS_API_KEY"),
        ),
        news=ApiSettings(
            base_url=env("NEWS_API_BASE_URL"),
            api_key=env("NEWS_API_KEY"),
        ),
    )


def load_universe(config_path: str | Path = "config/universe.yaml") -> list[str]:
    path = Path(config_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    universe = data.get("universe", []) if isinstance(data, dict) else []
    if not isinstance(universe, list):
        return []
    return [str(symbol).strip().upper() for symbol in universe if str(symbol).strip()]
