"""News summarizer with multi-provider support."""
import asyncio
import aiohttp  # For async HTTP requests
from news_summarizer.clients.news_api import NewsAPIClient
from news_summarizer.config import Config
from news_summarizer.providers.llm_providers import LLMProviders

class NewsSummarizer:
    """Summarize news articles using multiple LLM providers."""
    
    def __init__(self):
        self.news_api = NewsAPIClient()
        self.llm_providers = LLMProviders()
    
    def summarize_article(self, article):
        """
        Summarize a single article.
        
        Args:
            article: Article dictionary
        
        Returns:
            Dictionary with summary and sentiment
        """
        title = article.get("title", "") if isinstance(article, dict) else getattr(article, "title", "")
        description = (
            article.get("description", "") if isinstance(article, dict) else getattr(article, "description", "")
        )
        content = article.get("content", "") if isinstance(article, dict) else getattr(article, "content", "")
        source = article.get("source", "") if isinstance(article, dict) else getattr(article, "source", "")
        url = article.get("url", "") if isinstance(article, dict) else getattr(article, "url", "")
        published_at = (
            article.get("published_at", "") if isinstance(article, dict) else getattr(article, "published_at", "")
        )

        print(f"\nProcessing: {title[:60]}...")
        
        # Prepare text for summarization
        article_text = f"""Title: {title}
Description: {description}
Content: {content[:500]}"""  # Limit content length
        
        # Step 1: Summarize with OpenAI (fast and cheap)
        try:
            print("  → Summarizing with OpenAI...")
            summary_prompt = f"""Summarize this news article in 2-3 sentences:

{article_text}"""
            
            summary = self.llm_providers.ask_openai(summary_prompt)
            print(f"  ✓ Summary generated")
        
        except Exception as e:
            print(f"  ✗ OpenAI summarization failed: {e}")
            # Fallback to Cohere for summary
            print("  → Falling back to Cohere for summary...")
            summary = self.llm_providers.ask_cohere(summary_prompt)
        
        # Step 2: Analyze sentiment with Cohere 

        try:
            print("  → Analyzing sentiment with Cohere...")
            sentiment_prompt = f"""Analyze the sentiment of this text: "{summary}"

Provide:
- Overall sentiment (positive/negative/neutral)
- Confidence (0-100%)
- Key emotional tone

Be concise (2-3 sentences)."""
            
            sentiment = self.llm_providers.ask_cohere(sentiment_prompt)
            print(f"  ✓ Sentiment analyzed")
        
        except Exception as e:
            print(f"  ✗ Cohere sentiment analysis failed: {e}")
            # If sentiment fails, use a fallback
            sentiment = "Unable to analyze sentiment"
        
        return {
            "title": title,
            "source": source,
            "url": url,
            "summary": summary,
            "sentiment": sentiment,
            "published_at": published_at
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
            except Exception as e:
                print(f"✗ Failed to process article: {e}")
                # Continue with next article
        
        return results
    
    def generate_report(self, results):
        """Generate a summary report."""
        print("\n" + "="*80)
        print("NEWS SUMMARY REPORT")
        print("="*80)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']}")
            print(f"   Source: {result['source']} | Published: {result['published_at']}")
            print(f"   URL: {result['url']}")
            print(f"\n   SUMMARY:")
            print(f"   {result['summary']}")
            print(f"\n   SENTIMENT:")
            print(f"   {result['sentiment']}")
            print(f"\n   {'-'*76}")
        
        # Cost summary
        summary = self.llm_providers.cost_tracker.get_summary()
        print("\n" + "="*80)
        print("COST SUMMARY")
        print("="*80)
        print(f"Total requests: {summary['total_requests']}")
        print(f"Total cost: ${summary['total_cost']:.4f}")
        print(f"Total tokens: {summary['total_input_tokens'] + summary['total_output_tokens']:,}")
        print(f"  Input: {summary['total_input_tokens']:,}")
        print(f"  Output: {summary['total_output_tokens']:,}")
        print(f"Average cost per request: ${summary['average_cost']:.6f}")
        print("="*80)


class AsyncNewsSummarizer(NewsSummarizer):
    """Async version for processing multiple articles concurrently."""
    
    async def summarize_article_async(self, article):
        """Async version of summarize_article."""
        # Note: The LLM API calls themselves are not async in this simple version
        # For true async, you'd need to use aiohttp with the API endpoints directly
        # This version just allows concurrent processing of multiple articles
        
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
        
        # Filter out exceptions
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        return valid_results

# Test async version
async def test_async():
    summarizer = AsyncNewsSummarizer()
    
    # Fetch more articles
    print("Fetching news articles...")
    articles = summarizer.news_api.fetch_top_headlines(category="technology", max_articles=5)
    
    if articles:
        print(f"\nProcessing {len(articles)} articles concurrently...")
        results = await summarizer.process_articles_async(articles, max_concurrent=3)
        summarizer.generate_report(results)

# Test the module
if __name__ == "__main__":
    
    """
    summarizer = NewsSummarizer()
    
    # Fetch news
    print("Fetching news articles...")
    articles = summarizer.news_api.fetch_top_headlines(category="technology", max_articles=2)
    
    if not articles:
        print("No articles fetched. Check your News API key.")
    else:
        # Process articles
        print(f"\nProcessing {len(articles)} articles...")
        results = summarizer.process_articles(articles)
        
        # Generate report
        summarizer.generate_report(results)
    """
    
    # Uncomment to test async version
    asyncio.run(test_async())
    pass

