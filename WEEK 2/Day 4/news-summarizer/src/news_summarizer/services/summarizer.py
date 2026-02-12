"""News summarizer with multi-provider support."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from news_summarizer.clients.news_api import NewsAPIClient
from news_summarizer.config import Config
from news_summarizer.providers.llm_providers import LLMProviders

logger = logging.getLogger(__name__)


class NewsSummarizer:
    """Summarize news articles using multiple LLM providers."""

    def __init__(self):
        self.news_api = NewsAPIClient()
        self.llm_providers = LLMProviders()

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

    def _run_summary(self, summary_prompt: str) -> str:
        """Run summary generation with OpenAI primary and Cohere fallback."""
        try:
            print("  → Summarizing with OpenAI...")
            summary = self.llm_providers.ask_openai(summary_prompt)
            print("  ✓ Summary generated")
            return summary
        except Exception as error:
            print(f"  ✗ OpenAI summarization failed: {error}")
            print("  → Falling back to Cohere for summary...")
            return self.llm_providers.ask_cohere(summary_prompt)

    def _run_sentiment(self, summary: str) -> str:
        """Run sentiment analysis with Cohere and fallback text on failure."""
        sentiment_prompt = self._build_sentiment_prompt(summary)
        try:
            print("  → Analyzing sentiment with Cohere...")
            sentiment = self.llm_providers.ask_cohere(sentiment_prompt)
            print("  ✓ Sentiment analyzed")
            return sentiment
        except Exception as error:
            print(f"  ✗ Cohere sentiment analysis failed: {error}")
            return "Unable to analyze sentiment"

    def summarize_article(self, article):
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

        summary = self._run_summary(summary_prompt)
        sentiment = self._run_sentiment(summary)

        return {
            "title": fields["title"],
            "source": fields["source"],
            "url": fields["url"],
            "summary": summary,
            "sentiment": sentiment,
            "published_at": fields["published_at"],
        }

    def process_articles(self, articles):
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
                result = self.summarize_article(article)
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

    async def process_articles_async(self, articles, max_concurrent=3):
        """
        Process articles concurrently.

        Args:
            articles: List of articles
            max_concurrent: Maximum concurrent processes

        Returns:
            List of results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(article):
            async with semaphore:
                return await self.summarize_article_async(article)

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
    articles = summarizer.news_api.fetch_top_headlines(category="technology", max_articles=5)

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
