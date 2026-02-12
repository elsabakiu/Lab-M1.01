"""News API client for fetching and normalizing article data."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import requests

from news_summarizer.config import Config

logger = logging.getLogger(__name__)


class NewsAPIError(RuntimeError):
    """Raised when the NewsAPI request or response is invalid."""


@dataclass
class NewsArticle:
    """Normalized article shape used by the summarizer pipeline."""

    title: str
    description: str
    content: str
    url: str
    source: str
    published_at: str


class NewsAPIClient:
    """Small client wrapper around NewsAPI with basic rate limiting."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://newsapi.org/v2",
        request_timeout_seconds: Optional[int] = None,
        requests_per_minute: Optional[int] = None,
        session: Optional[requests.Session] = None,
        sleep_fn=time.sleep,
    ) -> None:
        self.api_key = api_key or Config.NEWS_API_KEY
        if not self.api_key:
            raise ValueError("NEWS_API_KEY is missing. Set it in your environment or .env file.")

        self.base_url = base_url.rstrip("/")
        self.request_timeout_seconds = request_timeout_seconds or Config.REQUEST_TIMEOUT
        self.requests_per_minute = requests_per_minute or Config.NEWS_API_RPM
        self.session = session or requests.Session()
        self.sleep_fn = sleep_fn
        self._last_call_time = 0.0

    def _wait_if_needed(self) -> None:
        """Apply a minimal fixed rate limit between outbound requests."""
        min_interval = 60.0 / float(self.requests_per_minute)
        elapsed = time.time() - self._last_call_time
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.info("Rate limiting News API request for %.2f seconds", wait_time)
            self.sleep_fn(wait_time)
        self._last_call_time = time.time()

    @staticmethod
    def _normalize_article(raw_article: Dict[str, Any]) -> NewsArticle:
        """Convert NewsAPI article payload to the project's normalized schema."""
        return NewsArticle(
            title=(raw_article.get("title") or "").strip(),
            description=(raw_article.get("description") or "").strip(),
            content=(raw_article.get("content") or "").strip(),
            url=(raw_article.get("url") or "").strip(),
            source=(raw_article.get("source") or {}).get("name", "Unknown"),
            published_at=(raw_article.get("publishedAt") or "").strip(),
        )

    def fetch_top_headlines(
        self,
        category: str = "technology",
        country: str = "us",
        max_articles: int = 5,
    ) -> List[NewsArticle]:
        """
        Fetch top headlines and return normalized NewsArticle objects.
        """
        if max_articles <= 0:
            return []

        self._wait_if_needed()
        endpoint = f"{self.base_url}/top-headlines"
        params = {
            "apiKey": self.api_key,
            "category": category,
            "country": country,
            "pageSize": max_articles,
        }

        try:
            response = self.session.get(endpoint, params=params, timeout=self.request_timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as error:
            raise NewsAPIError(f"HTTP error while calling NewsAPI: {error}") from error

        data = response.json()
        if data.get("status") != "ok":
            raise NewsAPIError(f"News API error: {data.get('message', 'Unknown error')}")

        raw_articles = data.get("articles", [])
        return [self._normalize_article(article) for article in raw_articles]

    def fetch_top_headlines_as_dicts(
        self,
        category: str = "technology",
        country: str = "us",
        max_articles: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Convenience wrapper for code paths that still expect dictionaries.
        """
        return [asdict(article) for article in self.fetch_top_headlines(category, country, max_articles)]


# Test the module
if __name__ == "__main__":
    api = NewsAPIClient()
    articles = api.fetch_top_headlines_as_dicts(category="technology", max_articles=3)
    
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article['title']}")
        print(f"   Source: {article['source']}")
        print(f"   URL: {article['url']}")