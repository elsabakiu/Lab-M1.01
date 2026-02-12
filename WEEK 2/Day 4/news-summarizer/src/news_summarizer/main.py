"""Gradio entrypoint for running the summarizer pipeline."""

from __future__ import annotations

import asyncio
from typing import Any

from news_summarizer.config import Config
from news_summarizer.services.summarizer import AsyncNewsSummarizer, NewsSummarizer

NEWS_CATEGORIES = [
    "business",
    "entertainment",
    "general",
    "health",
    "science",
    "sports",
    "technology",
]
NEWS_PROVIDER_CHOICES = ["all", "newsapi", "gdelt"]


def _parse_num_articles(raw_value: Any) -> int:
    """Parse and clamp user-provided article count."""
    try:
        parsed = int(float(raw_value))
        return max(Config.MIN_ARTICLES, min(Config.MAX_ARTICLES, parsed))
    except (TypeError, ValueError):
        return Config.DEFAULT_ARTICLES


def _normalize_news_provider(raw_value: Any) -> str:
    """Normalize UI news provider selection to allowed values."""
    normalized = (raw_value or "all").strip().lower()
    return normalized if normalized in NEWS_PROVIDER_CHOICES else "all"


def _run_pipeline(
    category: str,
    num_articles: int,
    use_async: bool,
    news_provider: str,
):
    """Run summarization pipeline and return summarizer/results tuple."""
    normalized_category = (category or Config.DEFAULT_CATEGORY).strip() or Config.DEFAULT_CATEGORY
    if normalized_category not in NEWS_CATEGORIES:
        normalized_category = Config.DEFAULT_CATEGORY
    normalized_num_articles = _parse_num_articles(num_articles)
    normalized_news_provider = _normalize_news_provider(news_provider)
    summarizer = AsyncNewsSummarizer() if use_async else NewsSummarizer()

    articles = summarizer.fetch_articles(
        category=normalized_category,
        max_articles=normalized_num_articles,
        news_provider=normalized_news_provider,
    )
    if not articles:
        return (
            normalized_category,
            normalized_num_articles,
            normalized_news_provider,
            [],
            summarizer,
        )

    if use_async:
        results = asyncio.run(
            summarizer.process_articles_async(
                articles,
                max_concurrent=Config.ASYNC_MAX_CONCURRENT,
                provider_mode="all",
            )
        )
    else:
        results = summarizer.process_articles(articles, provider_mode="all")
    return (
        normalized_category,
        normalized_num_articles,
        normalized_news_provider,
        results,
        summarizer,
    )


def _format_report(category: str, num_articles: int, news_provider: str, results, summarizer) -> str:
    """Format results and cost summary as markdown for Gradio."""
    if not results:
        return (
            f"## News Summarizer Report\n"
            f"- Category: `{category}`\n"
            f"- Requested articles: `{num_articles}`\n\n"
            f"- News provider: `{news_provider}`\n\n"
            "No articles found for the selected category."
        )

    lines = [
        "## News Summarizer Report",
        f"- Category: `{category}`",
        f"- Requested articles: `{num_articles}`",
        f"- News provider: `{news_provider}`",
        "",
    ]
    for idx, result in enumerate(results, 1):
        lines.extend(
            [
                f"### {idx}. {result['title']}",
                f"- Source: {result['source']}",
                f"- Published: {result['published_at']}",
                f"- URL: {result['url']}",
                "",
                "**Summary**",
                result["summary"],
                "",
                "**Sentiment**",
                result["sentiment"],
                "",
            ]
        )

    cost_summary = summarizer.llm_providers.cost_tracker.get_summary()
    lines.extend(
        [
            "## Cost Summary",
            f"- Total requests: {int(cost_summary['total_requests'])}",
            f"- Total cost: ${cost_summary['total_cost']:.4f}",
            (
                "- Total tokens: "
                f"{int(cost_summary['total_input_tokens'] + cost_summary['total_output_tokens']):,}"
            ),
            f"- Input tokens: {int(cost_summary['total_input_tokens']):,}",
            f"- Output tokens: {int(cost_summary['total_output_tokens']):,}",
            f"- Average cost/request: ${cost_summary['average_cost']:.6f}",
        ]
    )
    return "\n".join(lines)


def _format_result_rows(results) -> list[list[str]]:
    """Format article outputs for tabular display in Gradio."""
    rows: list[list[str]] = []
    for result in results:
        rows.append(
            [
                result.get("title", ""),
                result.get("source", ""),
                result.get("published_at", ""),
                result.get("summary", ""),
                result.get("sentiment", ""),
                result.get("url", ""),
            ]
        )
    return rows


def run_app(
    category: str,
    num_articles: int,
    use_async: bool,
    news_provider: str,
) -> tuple[str, list[list[str]]]:
    """Gradio callback for running the summarizer."""
    try:
        (
            resolved_category,
            resolved_num,
            resolved_news_provider,
            results,
            summarizer,
        ) = _run_pipeline(
            category,
            num_articles,
            use_async,
            news_provider,
        )
        report = _format_report(
            resolved_category,
            resolved_num,
            resolved_news_provider,
            results,
            summarizer,
        )
        rows = _format_result_rows(results)
        return report, rows
    except Exception as error:
        return f"## Error\n\n{error}", []


def build_demo():
    """Create the Gradio UI."""
    import gradio as gr

    with gr.Blocks(title="News Summarizer") as demo:
        gr.Markdown("# News Summarizer")
        gr.Markdown("Fetch headlines, summarize with LLMs, and get sentiment + cost analysis.")

        with gr.Row():
            category = gr.Dropdown(
                label="Category",
                choices=NEWS_CATEGORIES,
                value=Config.DEFAULT_CATEGORY,
            )
            num_articles = gr.Slider(
                minimum=Config.MIN_ARTICLES,
                maximum=Config.MAX_ARTICLES,
                step=1,
                value=Config.DEFAULT_ARTICLES,
                label="Number of articles",
            )
            news_provider = gr.Dropdown(
                label="News provider",
                choices=NEWS_PROVIDER_CHOICES,
                value="all",
            )

        use_async = gr.Checkbox(value=False, label="Use async processing")

        run_button = gr.Button("Run Summarizer", variant="primary")
        
        report_output = gr.Markdown(label="Report")
        
        results_output = gr.Dataframe(
            headers=["Title", "Source", "Published", "Summary", "Sentiment", "URL"],
            datatype=["str", "str", "str", "str", "str", "str"],
            col_count=(6, "fixed"),
            row_count=(0, "dynamic"),
            interactive=False,
            wrap=True,
            label="Summarized Results",
        )

        run_button.click(
            fn=run_app,
            inputs=[category, num_articles, use_async, news_provider],
            outputs=[report_output, results_output],
        )
    return demo


def main() -> None:
    """Launch the Gradio app."""
    demo = build_demo()
    demo.launch()


if __name__ == "__main__":
    main()
