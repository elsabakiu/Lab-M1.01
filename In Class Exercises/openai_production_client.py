"""
Production-ready OpenAI utilities.

This module merges:
1) Environment loading + API-key helpers.
2) Responses API wrapper helpers.
3) Reliability patterns (jittered retries + circuit breaker).
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)


def build_env_candidates(explicit_env_path: Optional[Path]) -> List[Path]:
    """Build a prioritized list of .env files to try."""
    if explicit_env_path is not None:
        return [explicit_env_path]

    cwd = Path.cwd()
    script_dir = Path(__file__).resolve().parent
    return [script_dir.parent.parent / ".env", script_dir.parent / ".env", script_dir / ".env", cwd / ".env", cwd.parent.parent / ".env", cwd.parent.parent.parent / ".env"]


def resolve_env_path(explicit_env_path: Optional[Path] = None) -> Optional[Path]:
    """Return the first existing .env path, or None if none are found."""
    for path in build_env_candidates(explicit_env_path):
        if path.exists():
            return path
    return None


def load_environment_variables(env_path: Optional[Path]) -> None:
    """Load environment variables from .env when a path is provided."""
    if env_path is None:
        logger.info("No .env file found; using current environment variables.")
        return
    load_dotenv(dotenv_path=env_path, override=True)
    logger.info("Environment variables loaded from %s", env_path)


def read_openai_api_key() -> str:
    """Read OPENAI_API_KEY from environment and fail with a clear message if missing."""
    load_environment_variables(resolve_env_path())
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return api_key


class CircuitBreakerOpenError(RuntimeError):
    """Raised when the circuit breaker is open and blocks requests."""


class ProductionOpenAIClientError(Exception):
    """Custom error that carries a standardized machine-readable payload."""

    def __init__(self, details: Dict[str, Any]):
        self.details = details
        super().__init__(json.dumps(details, ensure_ascii=False))


class CircuitState(str, Enum):
    """Enum values for circuit breaker state transitions."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """
    Circuit breaker implementation used to fail fast after repeated failures.
    """

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    clock_fn: Callable[[], float] = time.monotonic
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at_seconds: Optional[float] = None

    def before_request(self) -> None:
        """Decide whether the next request is allowed right now."""
        if self.state != CircuitState.OPEN:
            return

        if self.opened_at_seconds is None:
            raise CircuitBreakerOpenError("Circuit is OPEN and blocked.")

        elapsed = self.clock_fn() - self.opened_at_seconds
        if elapsed >= self.recovery_timeout_seconds:
            self.state = CircuitState.HALF_OPEN
            return

        remaining = self.recovery_timeout_seconds - elapsed
        raise CircuitBreakerOpenError(f"Circuit is OPEN; retry after {remaining:.2f}s.")

    def record_success(self) -> None:
        """Reset failure counters and close the circuit after success."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.opened_at_seconds = None

    def record_failure(self) -> None:
        """Increment failures and open the circuit once threshold is reached."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at_seconds = self.clock_fn()

    def get_status(self) -> Dict[str, Any]:
        """Expose internal state in a simple dictionary for logging/inspection."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout_seconds,
        }


class ProductionOpenAIClient:
    """
    Full OpenAI utility class with resilient execution and helper methods.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        jitter_fn: Callable[[], float] = random.random,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
        client: Optional[OpenAI] = None,
        request_executor: Optional[Callable[[Dict[str, Any]], str]] = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be > 0")
        if max_delay_seconds <= 0:
            raise ValueError("max_delay_seconds must be > 0")
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be > 0")

        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.jitter_fn = jitter_fn
        self.sleep_fn = sleep_fn
        self.client = client or OpenAI(api_key=api_key)
        self.request_executor = request_executor or self._default_request_executor
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
            clock_fn=clock_fn,
        )

    def _build_error_response(
        self,
        error_type: str,
        message: str,
        model: str,
        attempt: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create one stable error structure for downstream handling."""
        return {
            "error": {
                "type": error_type,
                "message": message,
                "model": model,
                "attempt": attempt,
                "max_retries": self.max_retries,
                "context": context or {},
                "circuit_breaker": self.circuit_breaker.get_status(),
            }
        }

    def _default_request_executor(self, request_kwargs: Dict[str, Any]) -> str:
        """Default request path that calls OpenAI Responses API."""
        response = self.client.responses.create(**request_kwargs)
        raw_text = response.output_text
        if not raw_text:
            raise RuntimeError("Empty response.output_text")
        return raw_text

    def _jittered_backoff_delay(self, attempt_index: int) -> float:
        """
        Compute exponential backoff delay with jitter.
        attempt_index is zero-based for retries: 0, 1, 2, ...
        """
        exponential_delay = self.base_delay_seconds * (2**attempt_index)
        capped_delay = min(exponential_delay, self.max_delay_seconds)
        jitter_multiplier = self.jitter_fn()
        return capped_delay * jitter_multiplier

    def _sleep_before_retry(self, attempt_index: int) -> float:
        """Sleep for jittered delay and return that delay (useful for tests/logging)."""
        delay = self._jittered_backoff_delay(attempt_index)
        if delay > 0:
            logger.warning("Retrying request in %.2f seconds (retry #%s)", delay, attempt_index + 1)
            self.sleep_fn(delay)
        return delay

    def request_response_text(
        self,
        model: str,
        input_payload: Any,
        temperature: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Main resilient call method for OpenAI Responses API.
        """
        request_kwargs: Dict[str, Any] = {"model": model, "input": input_payload}
        if temperature is not None:
            request_kwargs["temperature"] = temperature

        # total_attempts = first attempt + retries
        total_attempts = self.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                self.circuit_breaker.before_request()
                text = self.request_executor(request_kwargs)
                self.circuit_breaker.record_success()
                return text
            except CircuitBreakerOpenError as error:
                details = self._build_error_response(
                    error_type=type(error).__name__,
                    message=str(error),
                    model=model,
                    attempt=attempt,
                    context=context,
                )
                raise ProductionOpenAIClientError(details) from error
            except Exception as error:
                self.circuit_breaker.record_failure()

                if self.circuit_breaker.state == CircuitState.OPEN:
                    details = self._build_error_response(
                        error_type=CircuitBreakerOpenError.__name__,
                        message="Circuit opened after repeated request failures.",
                        model=model,
                        attempt=attempt,
                        context=context,
                    )
                    raise ProductionOpenAIClientError(details) from error

                if attempt >= total_attempts:
                    details = self._build_error_response(
                        error_type=type(error).__name__,
                        message=str(error),
                        model=model,
                        attempt=attempt,
                        context=context,
                    )
                    raise ProductionOpenAIClientError(details) from error

                self._sleep_before_retry(attempt - 1)

        fallback_details = self._build_error_response(
            error_type="RuntimeError",
            message="Retry loop ended unexpectedly",
            model=model,
            attempt=total_attempts,
            context=context,
        )
        raise ProductionOpenAIClientError(fallback_details)

    def call(self, prompt: str, model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        """Simple convenience method for one prompt -> one output string."""
        return self.request_response_text(
            model=model or self.model,
            input_payload=prompt,
            temperature=temperature,
            context={"operation": "call"},
        )

    def get_status(self) -> Dict[str, Any]:
        """Expose circuit breaker status."""
        return self.circuit_breaker.get_status()


def build_openai_wrapper(
    explicit_env_path: Optional[Path] = None,
    model: str = "gpt-4.1-mini",
    max_retries: int = 3,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 60.0,
    failure_threshold: int = 5,
    recovery_timeout_seconds: float = 30.0,
) -> ProductionOpenAIClient:
    """
    Build ProductionOpenAIClient from environment variables.
    """
    env_path = resolve_env_path(explicit_env_path)
    load_environment_variables(env_path)
    api_key = read_openai_api_key()
    return ProductionOpenAIClient(
        api_key=api_key,
        model=model,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
        max_delay_seconds=max_delay_seconds,
        failure_threshold=failure_threshold,
        recovery_timeout_seconds=recovery_timeout_seconds,
    )
