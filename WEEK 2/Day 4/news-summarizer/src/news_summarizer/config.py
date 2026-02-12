"""Centralized configuration for the news summarizer project."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")

    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    COHERE_MODEL = os.getenv("COHERE_MODEL", "command-a-03-2025")

    DAILY_BUDGET = float(os.getenv("DAILY_BUDGET", "5.00"))

    OPENAI_RPM = int(os.getenv("OPENAI_RPM", "500"))
    COHERE_RPM = int(os.getenv("COHERE_RPM", "50"))
    NEWS_API_RPM = int(os.getenv("NEWS_API_RPM", "100"))

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
