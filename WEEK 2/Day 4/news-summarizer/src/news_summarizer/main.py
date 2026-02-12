"""Command-line entrypoint for running the summarizer pipeline."""

from __future__ import annotations

import asyncio
import sys

from news_summarizer.config import Config
from news_summarizer.services.summarizer import AsyncNewsSummarizer, NewsSummarizer


def _print_banner() -> None:
    print("=" * 80)
    print("NEWS SUMMARIZER - Multi-Provider Edition")
    print("=" * 80)


def _parse_num_articles(raw_value: str) -> int:
    """Parse and clamp user-provided article count."""
    try:
        parsed = int(raw_value)
        return max(Config.MIN_ARTICLES, min(Config.MAX_ARTICLES, parsed))
    except ValueError:
        print(f"Invalid number; defaulting to {Config.DEFAULT_ARTICLES}.")
        return Config.DEFAULT_ARTICLES


def _collect_user_input() -> tuple[str, int, bool]:
    """Read and normalize CLI input values."""
    category = (
        input("\nEnter news category (technology/business/health/general): ").strip()
        or Config.DEFAULT_CATEGORY
    )
    num_articles = _parse_num_articles(
        input(f"How many articles to process? ({Config.MIN_ARTICLES}-{Config.MAX_ARTICLES}): ").strip()
    )
    use_async = input("Use async processing? (y/n): ").strip().lower() == "y"
    return category, num_articles, use_async


def _run_sync(category: str, num_articles: int) -> None:
    """Run synchronous processing flow."""
    summarizer = NewsSummarizer()
    articles = summarizer.news_api.fetch_top_headlines(category=category, max_articles=num_articles)

    if articles:
        print(f"\nProcessing {len(articles)} articles...")
        results = summarizer.process_articles(articles)
        summarizer.generate_report(results)
    else:
        print("No articles found for the selected category.")


def _run_async(category: str, num_articles: int) -> None:
    """Run asynchronous processing flow."""
    summarizer = AsyncNewsSummarizer()
    articles = summarizer.news_api.fetch_top_headlines(category=category, max_articles=num_articles)

    if articles:
        print(f"\nProcessing {len(articles)} articles concurrently...")
        results = asyncio.run(
            summarizer.process_articles_async(articles, max_concurrent=Config.ASYNC_MAX_CONCURRENT)
        )
        summarizer.generate_report(results)
    else:
        print("No articles found for the selected category.")


def main() -> None:
    """Run the news summarizer."""
    _print_banner()

    category, num_articles, use_async = _collect_user_input()
    print(f"\nFetching {num_articles} articles from category: {category}")

    try:
        if use_async:
            _run_async(category, num_articles)
        else:
            _run_sync(category, num_articles)

        print("\n✓ Processing complete!")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)

    except Exception as error:
        print(f"\n✗ Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
