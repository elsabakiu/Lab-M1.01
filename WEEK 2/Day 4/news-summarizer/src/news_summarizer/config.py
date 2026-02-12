"""Centralized configuration for the news summarizer project."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int, minimum: int | None = None) -> int:
    """Read an integer env var with fallback and optional lower bound."""
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        return max(minimum, value)
    return value


def _get_float(name: str, default: float, minimum: float | None = None) -> float:
    """Read a float env var with fallback and optional lower bound."""
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        return max(minimum, value)
    return value


class Config:
    """Application configuration loaded from environment variables."""

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")

    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    MAX_RETRIES = _get_int("MAX_RETRIES", 3, minimum=0)
    REQUEST_TIMEOUT = _get_int("REQUEST_TIMEOUT", 30, minimum=1)

    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    COHERE_MODEL = os.getenv("COHERE_MODEL", "command-a-03-2025")

    DAILY_BUDGET = _get_float("DAILY_BUDGET", 5.00, minimum=0.0)

    OPENAI_RPM = _get_int("OPENAI_RPM", 500, minimum=1)
    COHERE_RPM = _get_int("COHERE_RPM", 50, minimum=1)
    NEWS_API_RPM = _get_int("NEWS_API_RPM", 100, minimum=1)
    GDELT_RPM = _get_int("GDELT_RPM", 120, minimum=1)

    DEFAULT_CATEGORY = os.getenv("DEFAULT_CATEGORY", "technology")
    GDELT_DEFAULT_QUERY = os.getenv("GDELT_DEFAULT_QUERY", "AI")
    MIN_ARTICLES = _get_int("MIN_ARTICLES", 1, minimum=1)
    MAX_ARTICLES = _get_int("MAX_ARTICLES", 10, minimum=1)
    DEFAULT_ARTICLES = _get_int("DEFAULT_ARTICLES", 3, minimum=1)
    ASYNC_MAX_CONCURRENT = _get_int("ASYNC_MAX_CONCURRENT", 3, minimum=1)

    SUMMARY_PROMPT_TEMPLATE = (
        "Summarize this news article in 2-3 sentences:\n\n"
        "{article_text}"
    )
    SENTIMENT_PROMPT_TEMPLATE = (
        "Analyze the sentiment of this text: \"{summary}\"\n\n"
        "Provide:\n"
        "- Overall sentiment (positive/negative/neutral)\n"
        "- Confidence (0-100%)\n"
        "- Key emotional tone\n\n"
        "Be concise (2-3 sentences)."
    )

    @classmethod
    def validate(cls) -> None:
        """Validate required runtime configuration."""
        required = [
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
            ("COHERE_API_KEY", cls.COHERE_API_KEY),
            ("NEWS_API_KEY", cls.NEWS_API_KEY),
        ]
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
