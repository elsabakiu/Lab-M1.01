"""LLM provider integration with fallback and basic cost tracking."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import cohere
import tiktoken
from openai import OpenAI

from news_summarizer.config import Config

logger = logging.getLogger(__name__)

# Pricing in USD per 1M tokens.
# Update this table as provider pricing changes.
PRICING_PER_MILLION: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "command-a-03-2025": {"input": 2.50, "output": 10.00},
    "command-r": {"input": 0.50, "output": 1.50},
    "command-r-plus": {"input": 3.00, "output": 15.00},
}


class BudgetExceededError(RuntimeError):
    """Raised when tracked usage passes the configured budget."""


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens with tiktoken; fall back to rough 4 chars/token estimate."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text) // 4)


@dataclass
class RequestCost:
    """Structured record for one LLM request cost event."""

    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class CostTracker:
    """Track cumulative token/cost usage across providers."""

    def __init__(self) -> None:
        self.total_cost = 0.0
        self.requests: List[RequestCost] = []

    def track_request(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Add one request to the ledger and return cost in USD."""
        pricing = PRICING_PER_MILLION.get(model, {"input": 3.0, "output": 15.0})
        input_cost = (input_tokens / 1_000_000.0) * pricing["input"]
        output_cost = (output_tokens / 1_000_000.0) * pricing["output"]
        cost = input_cost + output_cost

        self.total_cost += cost
        self.requests.append(
            RequestCost(
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
            )
        )
        return cost

    def get_summary(self) -> Dict[str, float]:
        """Return aggregated request and spend metrics."""
        total_input = sum(r.input_tokens for r in self.requests)
        total_output = sum(r.output_tokens for r in self.requests)
        total_requests = len(self.requests)
        average_cost = self.total_cost / max(total_requests, 1)
        return {
            "total_requests": float(total_requests),
            "total_cost": self.total_cost,
            "total_input_tokens": float(total_input),
            "total_output_tokens": float(total_output),
            "average_cost": average_cost,
        }

    def check_budget(self, daily_budget: float) -> None:
        """Raise if budget is exceeded and warn near 90% usage."""
        if self.total_cost >= daily_budget:
            raise BudgetExceededError(
                f"Daily budget ${daily_budget:.2f} exceeded. Current: ${self.total_cost:.4f}"
            )
        percent_used = (self.total_cost / daily_budget) * 100 if daily_budget > 0 else 0.0
        if percent_used >= 90:
            logger.warning("Budget warning: %.1f%% of daily budget used", percent_used)


class LLMProviders:
    """Manage OpenAI/Cohere calls with fallback and cost/rate control."""

    def __init__(
        self,
        openai_client: Optional[OpenAI] = None,
        cohere_client: Optional[cohere.ClientV2] = None,
        sleep_fn=time.sleep,
    ) -> None:
        self.openai_client = openai_client or OpenAI(api_key=Config.OPENAI_API_KEY)
        self.cohere_client = cohere_client or cohere.ClientV2(api_key=Config.COHERE_API_KEY)
        self.cost_tracker = CostTracker()
        self.sleep_fn = sleep_fn

        # Fixed-interval rate limiting per provider.
        self._openai_last_call = 0.0
        self._cohere_last_call = 0.0
        self._openai_interval = 60.0 / float(Config.OPENAI_RPM)
        self._cohere_interval = 60.0 / float(Config.COHERE_RPM)
        self._max_retries = max(0, int(Config.MAX_RETRIES))

    def _wait_openai(self) -> None:
        elapsed = time.time() - self._openai_last_call
        if elapsed < self._openai_interval:
            self.sleep_fn(self._openai_interval - elapsed)
        self._openai_last_call = time.time()

    def _wait_cohere(self) -> None:
        elapsed = time.time() - self._cohere_last_call
        if elapsed < self._cohere_interval:
            self.sleep_fn(self._cohere_interval - elapsed)
        self._cohere_last_call = time.time()

    @staticmethod
    def _is_retryable_error(error: Exception) -> bool:
        """Return True for transient network/rate-limit style errors."""
        error_name = type(error).__name__
        retryable_names = {
            "APIConnectionError",
            "APITimeoutError",
            "RateLimitError",
            "ConnectError",
            "ReadTimeout",
            "TimeoutException",
        }
        message = str(error).lower()
        retryable_fragments = (
            "connection",
            "timeout",
            "temporarily unavailable",
            "rate limit",
            "try again",
        )
        return error_name in retryable_names or any(fragment in message for fragment in retryable_fragments)

    def _retry_delay_seconds(self, attempt_index: int) -> float:
        """Exponential backoff with jitter."""
        base_delay = 1.0
        max_delay = 20.0
        delay = min(max_delay, base_delay * (2**attempt_index))
        return delay * random.random()

    def _call_with_retry(self, provider_name: str, func):
        """
        Execute a provider call with retry for transient failures.
        """
        for attempt in range(self._max_retries + 1):
            try:
                return func()
            except Exception as error:
                is_last_attempt = attempt >= self._max_retries
                retryable = self._is_retryable_error(error)
                if is_last_attempt or not retryable:
                    raise

                delay = self._retry_delay_seconds(attempt)
                logger.warning(
                    "%s call failed (%s). Retrying in %.2fs [attempt %s/%s]",
                    provider_name,
                    type(error).__name__,
                    delay,
                    attempt + 1,
                    self._max_retries,
                )
                self.sleep_fn(delay)

    @staticmethod
    def _extract_cohere_text(response: Any) -> str:
        """Extract plain text robustly from Cohere v2 chat response."""
        # Most common v2 response field.
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        # Fallback to nested content structures.
        message = getattr(response, "message", None)
        content = getattr(message, "content", None) if message is not None else None
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                part_text = getattr(item, "text", None)
                if isinstance(part_text, str) and part_text:
                    parts.append(part_text)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            combined = "\n".join(parts).strip()
            if combined:
                return combined

        raise RuntimeError("Unable to extract text from Cohere response.")

    def ask_openai(self, prompt: str, model: Optional[str] = None) -> str:
        """Generate text with OpenAI and record cost usage."""
        selected_model = model or Config.OPENAI_MODEL
        self._wait_openai()

        input_tokens = count_tokens(prompt, selected_model)
        response = self._call_with_retry(
            "openai",
            lambda: self.openai_client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
            ),
        )
        output_text = response.choices[0].message.content or ""
        output_tokens = count_tokens(output_text, selected_model)

        self.cost_tracker.track_request("openai", selected_model, input_tokens, output_tokens)
        self.cost_tracker.check_budget(Config.DAILY_BUDGET)
        return output_text

    def ask_cohere(self, prompt: str, model: Optional[str] = None) -> str:
        """Generate text with Cohere and record cost usage."""
        selected_model = model or Config.COHERE_MODEL
        self._wait_cohere()

        input_tokens = count_tokens(prompt, selected_model)
        response = self._call_with_retry(
            "cohere",
            lambda: self.cohere_client.chat(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            ),
        )
        output_text = self._extract_cohere_text(response)
        output_tokens = count_tokens(output_text, selected_model)

        self.cost_tracker.track_request("cohere", selected_model, input_tokens, output_tokens)
        self.cost_tracker.check_budget(Config.DAILY_BUDGET)
        return output_text

    def ask_with_fallback(self, prompt: str, primary: str = "openai") -> Dict[str, str]:
        """
        Ask a prompt with provider fallback.

        Returns:
            {"provider": "<provider-used>", "response": "<text>"}
        """
        try:
            if primary == "openai":
                response = self.ask_openai(prompt)
                return {"provider": "openai", "response": response}

            response = self.ask_cohere(prompt)
            return {"provider": "cohere", "response": response}

        except Exception as primary_error:
            logger.warning("Primary provider '%s' failed: %s", primary, primary_error)
            try:
                if primary == "openai":
                    response = self.ask_cohere(prompt)
                    return {"provider": "cohere", "response": response}

                response = self.ask_openai(prompt)
                return {"provider": "openai", "response": response}
            except Exception as secondary_error:
                logger.error("Secondary provider also failed: %s", secondary_error)
                raise RuntimeError("All providers failed.") from secondary_error
            


# Test the module
if __name__ == "__main__":
    providers = LLMProviders()
    
    # Test OpenAI
    print("Testing OpenAI:")
    try:
        response = providers.ask_openai("What is Python? Answer in one sentence.")
        print(f"Response: {response}\n")
    except Exception as error:
        print(f"OpenAI test failed: {type(error).__name__}: {error}\n")
    
    # Test Cohere
    print("Testing Cohere:")
    try:
        response = providers.ask_cohere("What is Python? Answer in one sentence.")
        print(f"Response: {response}\n")
    except Exception as error:
        print(f"Cohere test failed: {type(error).__name__}: {error}\n")
    
    # Test fallback
    print("Testing fallback:")
    try:
        result = providers.ask_with_fallback("What is machine learning? Answer in one sentence.")
        print(f"Provider used: {result['provider']}")
        print(f"Response: {result['response']}\n")
    except Exception as error:
        print(f"Fallback test failed: {type(error).__name__}: {error}\n")
    
    # Show cost summary
    summary = providers.cost_tracker.get_summary()
    print(f"Total cost: ${summary['total_cost']:.4f}")
    print(f"Total requests: {summary['total_requests']}")
