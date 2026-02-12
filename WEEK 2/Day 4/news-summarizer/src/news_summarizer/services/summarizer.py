"""News summarizer with multi-provider support."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from news_summarizer.clients.gdelt_api import GDELTAPIClient
from news_summarizer.clients.news_api import NewsAPIClient
from news_summarizer.config import Config
from news_summarizer.providers.llm_providers import LLMProviders

logger = logging.getLogger(__name__)
VALID_PROVIDER_MODES = {"all", "openai", "cohere"}
VALID_NEWS_PROVIDERS = {"all", "newsapi", "gdelt"}


class NewsSummarizer:
    """Summarize news articles using multiple LLM providers."""

    def __init__(self, news_api: NewsAPIClient | None = None, gdelt_api: GDELTAPIClient | None = None):
        self.news_api = news_api or NewsAPIClient()
        self.gdelt_api = gdelt_api or GDELTAPIClient()
        self.llm_providers = LLMProviders()

    @staticmethod
    def _sort_key(article: Any) -> datetime:
        """Best-effort datetime parser for article sorting."""
        raw_value = getattr(article, "published_at", "") or ""
        value = str(raw_value).strip()
        if not value:
            return datetime.min
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
        try:
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ")
        except ValueError:
            return datetime.min

    @staticmethod
    def _deduplicate_articles(articles):
        """De-duplicate normalized articles by URL."""
        seen_urls = set()
        deduped = []
        for article in articles:
            url = (getattr(article, "url", "") or "").strip().lower()
            dedupe_key = url or f"{getattr(article, 'title', '').strip().lower()}|{getattr(article, 'source', '').strip().lower()}"
            if dedupe_key in seen_urls:
                continue
            seen_urls.add(dedupe_key)
            deduped.append(article)
        return deduped

    @staticmethod
    def _normalize_news_provider(news_provider: str | None) -> str:
        """Normalize news source mode to one of all/newsapi/gdelt."""
        normalized = (news_provider or "all").strip().lower()
        return normalized if normalized in VALID_NEWS_PROVIDERS else "all"

    def fetch_articles(
        self,
        category: str = "technology",
        max_articles: int = 5,
        news_provider: str = "all",
    ):
        """Fetch and merge articles from selected news source(s)."""
        if max_articles <= 0:
            return []

        normalized_news_provider = self._normalize_news_provider(news_provider)
        merged = []
        sources = []
        if normalized_news_provider in {"all", "newsapi"}:
            sources.append(
                ("NewsAPI", lambda: self.news_api.fetch_top_headlines(category=category, max_articles=max_articles))
            )
        if normalized_news_provider in {"all", "gdelt"}:
            sources.append(
                ("GDELT", lambda: self.gdelt_api.fetch_top_headlines(category=category, max_articles=max_articles))
            )
        for source_name, fetch_fn in sources:
            try:
                merged.extend(fetch_fn())
            except Exception as error:
                logger.exception("Failed to fetch from %s", source_name)
                print(f"✗ Failed to fetch from {source_name}: {error}")

        deduped = self._deduplicate_articles(merged)
        deduped.sort(key=self._sort_key, reverse=True)
        return deduped[:max_articles]

    @staticmethod
    def _extract_article_fields(article: Any) -> Dict[str, str]:
        """Normalize article input into a dict of string fields."""
        if isinstance(article, dict):
            get_value = article.get
        else:
            get_value = lambda key, default="": getattr(article, key, default)

        def to_text(value: Any) -> str:
            return value if isinstance(value, str) else ("" if value is None else str(value))

        return {
            "title": to_text(get_value("title", "")),
            "description": to_text(get_value("description", "")),
            "content": to_text(get_value("content", "")),
            "source": to_text(get_value("source", "")),
            "url": to_text(get_value("url", "")),
            "published_at": to_text(get_value("published_at", "")),
        }

    @staticmethod
    def _build_article_text(fields: Dict[str, str]) -> str:
        """Create compact article context text for prompting."""
        return f"""Title: {fields['title']}
Description: {fields['description']}
Content: {fields['content'][:500]}"""

    @staticmethod
    def _build_summary_prompt(article_text: str) -> str:
        """Build summary prompt."""
        return Config.SUMMARY_PROMPT_TEMPLATE.format(article_text=article_text)

    @staticmethod
    def _build_sentiment_prompt(summary: str) -> str:
        """Build sentiment analysis prompt."""
        return Config.SENTIMENT_PROMPT_TEMPLATE.format(summary=summary)

    @staticmethod
    def _normalize_provider_mode(provider_mode: str | None) -> str:
        """Normalize provider mode to one of all/openai/cohere."""
        normalized = (provider_mode or "all").strip().lower()
        return normalized if normalized in VALID_PROVIDER_MODES else "all"

    def _run_summary(self, summary_prompt: str, provider_mode: str = "all") -> str:
        """Run summary generation for selected provider mode."""
        mode = self._normalize_provider_mode(provider_mode)
        if mode == "openai":
            print("  → Summarizing with OpenAI...")
            summary = self.llm_providers.ask_openai(summary_prompt)
            print("  ✓ Summary generated")
            return summary
        if mode == "cohere":
            print("  → Summarizing with Cohere...")
            summary = self.llm_providers.ask_cohere(summary_prompt)
            print("  ✓ Summary generated")
            return summary

        try:
            print("  → Summarizing with OpenAI...")
            summary = self.llm_providers.ask_openai(summary_prompt)
            print("  ✓ Summary generated")
            return summary
        except Exception as error:
            print(f"  ✗ OpenAI summarization failed: {error}")
            print("  → Falling back to Cohere for summary...")
            return self.llm_providers.ask_cohere(summary_prompt)

    def _run_sentiment(self, summary: str, provider_mode: str = "all") -> str:
        """Run sentiment analysis for selected provider mode."""
        mode = self._normalize_provider_mode(provider_mode)
        sentiment_prompt = self._build_sentiment_prompt(summary)
        if mode == "openai":
            try:
                print("  → Analyzing sentiment with OpenAI...")
                sentiment = self.llm_providers.ask_openai(sentiment_prompt)
                print("  ✓ Sentiment analyzed")
                return sentiment
            except Exception as error:
                print(f"  ✗ OpenAI sentiment analysis failed: {error}")
                return "Unable to analyze sentiment"
        if mode == "cohere":
            try:
                print("  → Analyzing sentiment with Cohere...")
                sentiment = self.llm_providers.ask_cohere(sentiment_prompt)
                print("  ✓ Sentiment analyzed")
                return sentiment
            except Exception as error:
                print(f"  ✗ Cohere sentiment analysis failed: {error}")
                return "Unable to analyze sentiment"

        try:
            print("  → Analyzing sentiment with Cohere...")
            sentiment = self.llm_providers.ask_cohere(sentiment_prompt)
            print("  ✓ Sentiment analyzed")
            return sentiment
        except Exception as error:
            print(f"  ✗ Cohere sentiment analysis failed: {error}")
            try:
                print("  → Falling back to OpenAI for sentiment...")
                sentiment = self.llm_providers.ask_openai(sentiment_prompt)
                print("  ✓ Sentiment analyzed")
                return sentiment
            except Exception:
                return "Unable to analyze sentiment"

    def summarize_article(self, article, provider_mode: str = "all"):
        """
        Summarize a single article.

        Args:
            article: Article dictionary or object

        Returns:
            Dictionary with summary and sentiment
        """
        fields = self._extract_article_fields(article)
        print(f"\nProcessing: {fields['title'][:60]}...")

        article_text = self._build_article_text(fields)
        summary_prompt = self._build_summary_prompt(article_text)

        summary = self._run_summary(summary_prompt, provider_mode=provider_mode)
        sentiment = self._run_sentiment(summary, provider_mode=provider_mode)

        return {
            "title": fields["title"],
            "source": fields["source"],
            "url": fields["url"],
            "summary": summary,
            "sentiment": sentiment,
            "published_at": fields["published_at"],
        }

    def process_articles(self, articles, provider_mode: str = "all"):
        """
        Process multiple articles.

        Args:
            articles: List of article dictionaries

        Returns:
            List of processed articles
        """
        results = []

        for article in articles:
            try:
                result = self.summarize_article(article, provider_mode=provider_mode)
                results.append(result)
            except Exception as error:
                logger.exception("Failed to process article")
                print(f"✗ Failed to process article: {error}")

        return results

    @staticmethod
    def _print_report_item(index: int, result: Dict[str, str]) -> None:
        """Print one report entry."""
        print(f"\n{index}. {result['title']}")
        print(f"   Source: {result['source']} | Published: {result['published_at']}")
        print(f"   URL: {result['url']}")
        print("\n   SUMMARY:")
        print(f"   {result['summary']}")
        print("\n   SENTIMENT:")
        print(f"   {result['sentiment']}")
        print(f"\n   {'-' * 76}")

    def generate_report(self, results):
        """Generate a summary report."""
        print("\n" + "=" * 80)
        print("NEWS SUMMARY REPORT")
        print("=" * 80)

        for i, result in enumerate(results, 1):
            self._print_report_item(i, result)

        summary = self.llm_providers.cost_tracker.get_summary()
        print("\n" + "=" * 80)
        print("COST SUMMARY")
        print("=" * 80)
        print(f"Total requests: {summary['total_requests']}")
        print(f"Total cost: ${summary['total_cost']:.4f}")
        print(f"Total tokens: {summary['total_input_tokens'] + summary['total_output_tokens']:,}")
        print(f"  Input: {summary['total_input_tokens']:,}")
        print(f"  Output: {summary['total_output_tokens']:,}")
        print(f"Average cost per request: ${summary['average_cost']:.6f}")
        print("=" * 80)


class AsyncNewsSummarizer(NewsSummarizer):
    """Async version for processing multiple articles concurrently."""

    async def summarize_article_async(self, article):
        """Async version of summarize_article."""
        return await asyncio.to_thread(self.summarize_article, article)

    async def process_articles_async(self, articles, max_concurrent=3, provider_mode: str = "all"):
        """
        Process articles concurrently.

        Args:
            articles: List of articles
            max_concurrent: Maximum concurrent processes

        Returns:
            List of results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        normalized_mode = self._normalize_provider_mode(provider_mode)

        async def process_with_semaphore(article):
            async with semaphore:
                if normalized_mode == "all":
                    return await self.summarize_article_async(article)
                return await asyncio.to_thread(self.summarize_article, article, normalized_mode)

        tasks = [process_with_semaphore(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.exception("Failed to process article asynchronously", exc_info=result)
                print(f"✗ Failed to process article: {result}")
                continue
            valid_results.append(result)
        return valid_results


# Test async version
async def test_async():
    summarizer = AsyncNewsSummarizer()

    print("Fetching news articles...")
    articles = summarizer.fetch_articles(category="technology", max_articles=5)

    if articles:
        print(f"\nProcessing {len(articles)} articles concurrently...")
        results = await summarizer.process_articles_async(
            articles,
            max_concurrent=Config.ASYNC_MAX_CONCURRENT,
        )
        summarizer.generate_report(results)


# Test the module
if __name__ == "__main__":
    asyncio.run(test_async())
