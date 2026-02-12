import sys
import unittest
from pathlib import Path

# Add this test file's folder to import path for direct `python -m unittest` runs.
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from openai_production_client import CircuitBreakerOpenError, ProductionOpenAIClient


class TestProductionOpenAIClient(unittest.TestCase):
    def test_jitter_retry_then_circuit_open_fail_fast(self) -> None:
        """
        This single test method verifies BOTH patterns:
        1) First call uses jittered retry after a failure.
        2) Repeated failures open the circuit breaker.
        3) Next call fails fast without touching the upstream function.
        """
        # This list records all sleep delays used between retries.
        recorded_sleeps = []

        # This mutable counter lets us track how many times upstream was called.
        call_counter = {"value": 0}

        # Fake upstream function: always fails to force retry + breaker behavior.
        def fake_request(_prompt: str) -> str:
            call_counter["value"] += 1
            raise ConnectionError("Simulated temporary outage")

        # Sleep stub avoids waiting in unit tests and captures chosen delay.
        def fake_sleep(seconds: float) -> None:
            recorded_sleeps.append(seconds)

        # Deterministic jitter makes retry delay predictable for assertions.
        fixed_jitter = lambda: 0.5

        # Fixed clock keeps breaker timing stable in this test.
        fixed_clock = lambda: 1000.0

        # failure_threshold=2 means two consecutive failures will open circuit.
        # max_retries=3 allows retries, but breaker should stop us earlier.
        client = ProductionOpenAIClient(
            api_key="test-key",
            model="gpt-4.1-mini",
            max_retries=3,
            base_delay_seconds=2.0,
            max_delay_seconds=30.0,
            failure_threshold=2,
            recovery_timeout_seconds=60.0,
            jitter_fn=fixed_jitter,
            sleep_fn=fake_sleep,
            clock_fn=fixed_clock,
            request_fn=fake_request,
        )

        # First user call:
        # - Attempt 1 fails
        # - One jittered sleep occurs (2.0 * 2^0 * 0.5 = 1.0 second)
        # - Attempt 2 fails and opens circuit
        with self.assertRaises(CircuitBreakerOpenError):
            client.call("Hello")

        self.assertEqual(call_counter["value"], 2)
        self.assertEqual(recorded_sleeps, [1.0])

        # Second user call happens while circuit is still open.
        # It should fail fast before fake_request is called again.
        with self.assertRaises(CircuitBreakerOpenError):
            client.call("Hello again")

        self.assertEqual(call_counter["value"], 2)
        self.assertEqual(recorded_sleeps, [1.0])


if __name__ == "__main__":
    unittest.main()
