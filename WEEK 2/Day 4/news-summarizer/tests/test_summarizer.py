"""Unit tests for summarizer pipeline."""
import asyncio
import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from news_summarizer.clients.news_api import NewsAPIClient
from news_summarizer.config import Config
from news_summarizer.main import _parse_num_articles
from news_summarizer.providers.llm_providers import LLMProviders, CostTracker, count_tokens
from news_summarizer.services.summarizer import AsyncNewsSummarizer, NewsSummarizer

class TestCostTracker:
    """Test cost tracking functionality."""
    
    def test_track_request(self):
        """Test tracking a single request."""
        tracker = CostTracker()
        cost = tracker.track_request("openai", "gpt-4o-mini", 100, 500)
        
        assert cost > 0
        assert tracker.total_cost == cost
        assert len(tracker.requests) == 1
    
    def test_get_summary(self):
        """Test summary generation."""
        tracker = CostTracker()
        tracker.track_request("openai", "gpt-4o-mini", 100, 200)
        tracker.track_request("cohere", "command-r", 150, 300)
        
        summary = tracker.get_summary()
        
        assert summary["total_requests"] == 2
        assert summary["total_cost"] > 0
        assert summary["total_input_tokens"] == 250
        assert summary["total_output_tokens"] == 500
    
    def test_budget_check(self):
        """Test budget checking."""
        tracker = CostTracker()
        
        # Should not raise for small amount
        tracker.track_request("openai", "gpt-4o-mini", 100, 100)
        tracker.check_budget(10.00)  # Should pass
        
        # Should raise for exceeding budget
        tracker.total_cost = 15.00
        with pytest.raises(Exception, match="budget.*exceeded"):
            tracker.check_budget(10.00)

class TestTokenCounting:
    """Test token counting."""
    
    def test_count_tokens(self):
        """Test token counting function."""
        text = "Hello, how are you?"
        count = count_tokens(text)
        
        assert count > 0
        assert count < len(text)  # Should be less than character count

class TestNewsAPI:
    """Test News API integration."""
    
    @patch("news_summarizer.clients.news_api.requests.Session.get")
    def test_fetch_top_headlines(self, mock_get):
        """Test fetching headlines."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "Test Article",
                    "description": "Test description",
                    "content": "Test content",
                    "url": "https://example.com",
                    "source": {"name": "Test Source"},
                    "publishedAt": "2026-01-19"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        api = NewsAPIClient(api_key="test-api-key")
        articles = api.fetch_top_headlines(max_articles=1)
        
        assert len(articles) == 1
        assert articles[0].title == "Test Article"
        assert articles[0].source == "Test Source"

class TestLLMProviders:
    """Test LLM provider integration."""
    
    def test_ask_openai(self):
        """Test OpenAI integration."""
        # Mock OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_client.chat.completions.create.return_value = mock_response
        
        providers = LLMProviders(openai_client=mock_client, cohere_client=Mock())
        
        response = providers.ask_openai("Test prompt")
        
        assert response == "Test response"
        assert mock_client.chat.completions.create.called

class TestNewsSummarizer:
    """Test news summarizer."""
    
    def test_initialization(self):
        """Test summarizer initialization."""
        summarizer = NewsSummarizer()
        
        assert summarizer.news_api is not None
        assert summarizer.llm_providers is not None
    
    @patch.object(LLMProviders, 'ask_openai')
    @patch.object(LLMProviders, 'ask_cohere')
    def test_summarize_article(self, mock_cohere, mock_openai):
        """Test article summarization."""
        mock_openai.return_value = "Test summary"
        mock_cohere.return_value = "Positive sentiment"
        
        summarizer = NewsSummarizer()
        article = {
            "title": "Test Article",
            "description": "Test description",
            "content": "Test content",
            "url": "https://example.com",
            "source": "Test Source",
            "published_at": "2026-01-19"
        }
        
        result = summarizer.summarize_article(article)
        
        assert result["title"] == "Test Article"
        assert result["summary"] == "Test summary"
        assert result["sentiment"] == "Positive sentiment"
        assert mock_openai.called
        assert mock_cohere.called

    @patch.object(LLMProviders, "ask_openai")
    @patch.object(LLMProviders, "ask_cohere")
    def test_summarize_article_with_object_input(self, mock_cohere, mock_openai):
        """Test article summarization with object-style input."""
        mock_openai.return_value = "Test summary"
        mock_cohere.return_value = "Neutral sentiment"

        summarizer = NewsSummarizer()
        article = SimpleNamespace(
            title="Object Article",
            description="Object description",
            content="Object content",
            url="https://example.com/object",
            source="Object Source",
            published_at="2026-01-19",
        )

        result = summarizer.summarize_article(article)

        assert result["title"] == "Object Article"
        assert result["summary"] == "Test summary"
        assert result["sentiment"] == "Neutral sentiment"


class TestMainHelpers:
    """Test CLI helper behavior."""

    def test_parse_num_articles_invalid_defaults(self):
        """Invalid numeric input should use configured default."""
        assert _parse_num_articles("abc") == Config.DEFAULT_ARTICLES


class TestAsyncNewsSummarizer:
    """Test async processing behavior."""

    def test_process_articles_async_mixed_results(self):
        """Async processing should return valid results and skip exceptions."""
        summarizer = AsyncNewsSummarizer.__new__(AsyncNewsSummarizer)

        async def fake_summarize(article):
            if article == "bad":
                raise RuntimeError("boom")
            return {"title": "ok"}

        summarizer.summarize_article_async = fake_summarize

        with patch("builtins.print") as mock_print:
            results = asyncio.run(
                AsyncNewsSummarizer.process_articles_async(
                    summarizer, ["good", "bad"], max_concurrent=2
                )
            )

        assert results == [{"title": "ok"}]
        assert any("Failed to process article" in str(call) for call in mock_print.call_args_list)

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
