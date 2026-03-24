from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent


def _clean_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip().strip('"').strip("'")


def configure_langsmith() -> dict[str, str]:
    load_dotenv(PROJECT_ROOT / ".env")

    config = {
        "tracing": _clean_env("LANGSMITH_TRACING", "true") or "true",
        "endpoint": _clean_env("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        "api_key": _clean_env("LANGSMITH_API_KEY"),
        "project": _clean_env("LANGSMITH_PROJECT", "BI Dashboard Project") or "BI Dashboard Project",
    }

    os.environ["LANGSMITH_TRACING"] = config["tracing"]
    os.environ["LANGSMITH_ENDPOINT"] = config["endpoint"]
    if config["api_key"]:
        os.environ["LANGSMITH_API_KEY"] = config["api_key"]
    os.environ["LANGSMITH_PROJECT"] = config["project"]

    if "LANGCHAIN_TRACING_V2" not in os.environ:
        os.environ["LANGCHAIN_TRACING_V2"] = "true" if config["tracing"].lower() in {"1", "true", "yes", "on"} else "false"

    return config
