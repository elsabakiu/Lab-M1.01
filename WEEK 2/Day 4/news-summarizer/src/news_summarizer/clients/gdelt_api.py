"""GDELT API client for fetching and normalizing article data."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import requests

from news_summarizer.clients.news_api import NewsArticle
from news_summarizer.config import Config

logger = logging.getLogger(__name__)


class GDELTAPIError(RuntimeError):
    """Raised when the GDELT request or response is invalid."""


class GDELTAPIClient:
    """Small client wrapper around GDELT with basic rate limiting."""

    def __init__(
        self,
        base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc",
        request_timeout_seconds: Optional[int] = None,
        requests_per_minute: Optional[int] = None,
        session: Optional[requests.Session] = None,
        sleep_fn=time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.request_timeout_seconds = request_timeout_seconds or Config.REQUEST_TIMEOUT
        self.requests_per_minute = requests_per_minute or Config.GDELT_RPM
        self.session = session or requests.Session()
        self.sleep_fn = sleep_fn
        self._last_call_time = 0.0

    def _wait_if_needed(self) -> None:
        """Apply a minimal fixed rate limit between outbound requests."""
        min_interval = 60.0 / float(self.requests_per_minute)
        elapsed = time.time() - self._last_call_time
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.info("Rate limiting GDELT request for %.2f seconds", wait_time)
            self.sleep_fn(wait_time)
        self._last_call_time = time.time()

    @staticmethod
    def _normalize_published_at(raw_value: str) -> str:
        """Convert GDELT seendate into ISO-like display format when possible."""
        candidate = (raw_value or "").strip()
        match = re.fullmatch(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z", candidate)
        if not match:
            return candidate
        year, month, day, hour, minute, second = match.groups()
        return f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"

    @classmethod
    def _normalize_article(cls, raw_article: Dict[str, Any]) -> NewsArticle:
        """Convert GDELT payload to the project's normalized schema."""
        domain = (raw_article.get("domain") or "").strip()
        source = f"GDELT ({domain})" if domain else "GDELT"
        return NewsArticle(
            title=(raw_article.get("title") or "").strip(),
            description=(raw_article.get("snippet") or "").strip(),
            content=(raw_article.get("snippet") or "").strip(),
            url=(raw_article.get("url") or "").strip(),
            source=source,
            published_at=cls._normalize_published_at(raw_article.get("seendate") or ""),
        )

    def fetch_top_headlines(
        self,
        category: str = "technology",
        max_articles: int = 5,
    ) -> List[NewsArticle]:
        """
        Fetch GDELT article list and return normalized NewsArticle objects.
        """
        if max_articles <= 0:
            return []

        self._wait_if_needed()
        query = (category or "").strip() or Config.GDELT_DEFAULT_QUERY
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": max_articles,
        }

        try:
            response = self.session.get(self.base_url, params=params, timeout=self.request_timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as error:
            raise GDELTAPIError(f"HTTP error while calling GDELT: {error}") from error

        data = response.json()
        if not isinstance(data, dict):
            raise GDELTAPIError("Invalid GDELT response payload")

        raw_articles = data.get("articles", [])
        if not isinstance(raw_articles, list):
            raise GDELTAPIError("Invalid GDELT response format: 'articles' is not a list")
        return [self._normalize_article(article) for article in raw_articles]

    def fetch_top_headlines_as_dicts(
        self,
        category: str = "technology",
        max_articles: int = 5,
    ) -> List[Dict[str, Any]]:
        """Convenience wrapper for code paths that still expect dictionaries."""
        return [asdict(article) for article in self.fetch_top_headlines(category, max_articles)]
