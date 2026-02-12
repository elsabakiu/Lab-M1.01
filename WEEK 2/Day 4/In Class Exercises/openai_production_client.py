"""
Beginner-friendly, production-style OpenAI client.

This module combines two reliability patterns:
1) Jittered exponential backoff for retries.
2) Circuit breaker fail-fast protection.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from openai import OpenAI


class CircuitBreakerOpenError(RuntimeError):
    """Raised when the circuit breaker is open and blocks the request."""


class CircuitState(str, Enum):
    """Small enum that makes circuit state values explicit and typo-safe."""

    CLOSED = "closed"  # Normal operation: requests are allowed.
    OPEN = "open"  # Too many failures: fail fast, do not call upstream.
    HALF_OPEN = "half_open"  # Recovery trial mode after timeout.


@dataclass
class CircuitBreaker:
    """
    Tracks repeated failures and temporarily blocks new calls when unhealthy.

    Args:
        failure_threshold: How many consecutive failures we tolerate.
        recovery_timeout_seconds: Wait time before a half-open trial request.
        clock_fn: Injectable clock for testing (defaults to monotonic time).
    """

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    clock_fn: Callable[[], float] = time.monotonic
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at_seconds: Optional[float] = None

    def before_request(self) -> None:
        """
        Called immediately before sending a request.

        - If circuit is open and timeout has not elapsed: block call.
        - If circuit is open and timeout has elapsed: move to half-open.
        """
        if self.state != CircuitState.OPEN:
            return

        # If we do not have an open timestamp for any reason, we fail fast.
        if self.opened_at_seconds is None:
            raise CircuitBreakerOpenError("Circuit is OPEN and blocked.")

        elapsed = self.clock_fn() - self.opened_at_seconds
        if elapsed >= self.recovery_timeout_seconds:
            # Half-open allows one trial call to check if service recovered.
            self.state = CircuitState.HALF_OPEN
            return

        remaining = self.recovery_timeout_seconds - elapsed
        raise CircuitBreakerOpenError(
            f"Circuit is OPEN; retry after {remaining:.2f}s."
        )

    def record_success(self) -> None:
        """Reset breaker to healthy state after any successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.opened_at_seconds = None

    def record_failure(self) -> None:
        """
        Track a failed call and open breaker if threshold is reached.
        """
        self.failure_count += 1

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at_seconds = self.clock_fn()


class ProductionOpenAIClient:
    """
    Production-ready wrapper for OpenAI text calls.

    Reliability behavior:
    - Retries transient failures with exponential backoff + jitter.
    - Opens a circuit breaker after repeated failures.
    - Fails fast while the breaker is open.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        jitter_fn: Callable[[], float] = random.random,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
        request_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        # Validate configuration early so runtime failures are clearer.
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be > 0")
        if max_delay_seconds <= 0:
            raise ValueError("max_delay_seconds must be > 0")
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be > 0")

        self.model = model
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.jitter_fn = jitter_fn
        self.sleep_fn = sleep_fn
        self.client = OpenAI(api_key=api_key)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
            clock_fn=clock_fn,
        )

        # request_fn allows easy mocking in tests.
        self.request_fn = request_fn or self._default_request

    def _default_request(self, prompt: str) -> str:
        """
        Default request implementation using OpenAI Responses API.
        """
        response = self.client.responses.create(model=self.model, input=prompt)
        output_text = response.output_text
        if not output_text:
            raise RuntimeError("OpenAI returned empty output_text.")
        return output_text

    def _jittered_backoff_delay(self, attempt: int) -> float:
        """
        Calculate retry delay:
        - Exponential growth: base * 2^attempt
        - Max cap to avoid unbounded waits
        - Jitter multiplier [0.0, 1.0) to spread traffic across clients
        """
        exponential_delay = self.base_delay_seconds * (2 ** attempt)
        capped_delay = min(exponential_delay, self.max_delay_seconds)
        jitter_multiplier = self.jitter_fn()
        return capped_delay * jitter_multiplier

    def call(self, prompt: str) -> str:
        """
        Execute the OpenAI call with retry and circuit breaker protection.

        Args:
            prompt: User prompt to send to OpenAI.

        Returns:
            Model output text.
        """
        # Number of retries already performed after an initial failed attempt.
        retries_used = 0

        while True:
            # Circuit breaker can block the request before we hit OpenAI.
            self.circuit_breaker.before_request()

            try:
                result = self.request_fn(prompt)
                self.circuit_breaker.record_success()
                return result
            except Exception as error:
                self.circuit_breaker.record_failure()

                # If this failure opened the circuit, stop immediately.
                if self.circuit_breaker.state == CircuitState.OPEN:
                    raise CircuitBreakerOpenError(
                        "Circuit opened after repeated request failures."
                    ) from error

                # If we consumed all retries, propagate a final clear error.
                if retries_used >= self.max_retries:
                    raise RuntimeError("OpenAI call failed after all retries.") from error

                # Wait using jittered exponential backoff before next attempt.
                delay = self._jittered_backoff_delay(retries_used)
                self.sleep_fn(delay)
                retries_used += 1

