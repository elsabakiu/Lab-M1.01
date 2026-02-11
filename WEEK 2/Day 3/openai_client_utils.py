from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from refactor_helpers import report_error


# Builds possible .env locations to check.
def build_env_candidates(explicit_env_path: Optional[Path]) -> List[Path]:
    if explicit_env_path is not None:
        return [explicit_env_path]

    cwd = Path.cwd()
    script_dir = Path(__file__).resolve().parent
    return [script_dir / ".env", cwd / ".env", cwd.parent.parent / ".env"]


# Returns the first .env path that exists.
def resolve_env_path(explicit_env_path: Optional[Path] = None) -> Optional[Path]:
    for path in build_env_candidates(explicit_env_path):
        if path.exists():
            return path
    return None


# Loads environment variables from a .env file.
def load_environment_variables(env_path: Optional[Path]) -> None:
    if env_path is None:
        return
    try:
        load_dotenv(dotenv_path=env_path, override=True)
    except OSError as error:
        report_error(
            function_name="load_environment_variables",
            error=error,
            location=f"path={env_path}",
            suggestion="Check that the .env file path exists and is readable.",
        )
        raise


# Reads OpenAI key from environment.
def read_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        error = RuntimeError("OPENAI_API_KEY is not set.")
        report_error(
            function_name="read_openai_api_key",
            error=error,
            location="environment variable OPENAI_API_KEY",
            suggestion="Add OPENAI_API_KEY to your shell environment or .env file.",
        )
        raise error
    return api_key


# Custom exception carrying standardized API error details.
class OpenAIWrapperError(Exception):
    def __init__(self, details: Dict[str, Any]):
        self.details = details
        super().__init__(json.dumps(details, ensure_ascii=False))


# Wrapper for OpenAI calls with retry and standardized errors.
class OpenAIWrapper:
    """Wrapper for OpenAI API calls with error handling and retry logic."""

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        initial_backoff_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        client: Optional[OpenAI] = None,
    ):
        self.api_key = api_key
        self.max_retries = max_retries
        self.initial_backoff_seconds = initial_backoff_seconds
        self.backoff_multiplier = backoff_multiplier
        self.client = client or OpenAI(api_key=api_key)

    # Creates one consistent error payload shape.
    def _build_error_response(
        self,
        error_type: str,
        message: str,
        model: str,
        attempt: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "error": {
                "type": error_type,
                "message": message,
                "model": model,
                "attempt": attempt,
                "max_retries": self.max_retries,
                "context": context or {},
            }
        }

    # Waits before the next retry using exponential backoff.
    def _sleep_before_retry(self, attempt: int) -> None:
        delay = self.initial_backoff_seconds * (self.backoff_multiplier ** (attempt - 1))
        if delay > 0:
            time.sleep(delay)

    # Calls Responses API and returns output text.
    def request_response_text(
        self,
        model: str,
        input_payload: Any,
        temperature: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        request_kwargs: Dict[str, Any] = {"model": model, "input": input_payload}
        if temperature is not None:
            request_kwargs["temperature"] = temperature

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.responses.create(**request_kwargs)
                raw_text = response.output_text
                if not raw_text:
                    raise RuntimeError("Empty response.output_text")
                return raw_text
            except Exception as error:
                if attempt < self.max_retries:
                    self._sleep_before_retry(attempt)
                    continue

                details = self._build_error_response(
                    error_type=type(error).__name__,
                    message=str(error),
                    model=model,
                    attempt=attempt,
                    context=context,
                )
                wrapped_error = OpenAIWrapperError(details)
                report_error(
                    function_name="OpenAIWrapper.request_response_text",
                    error=wrapped_error,
                    location=f"model={model}, attempt={attempt}",
                    suggestion="Check API key, quota/rate limits, model name, and network connectivity.",
                    message_override=json.dumps(details, ensure_ascii=False),
                )
                raise wrapped_error from error

        fallback_details = self._build_error_response(
            error_type="RuntimeError",
            message="Retry loop ended unexpectedly",
            model=model,
            attempt=self.max_retries,
            context=context,
        )
        raise OpenAIWrapperError(fallback_details)

    # Generic simple text generation helper.
    def generate_description(
        self,
        prompt: str,
        model: str = "gpt-4.1-mini",
        temperature: Optional[float] = 0.7,
    ) -> Dict[str, Any]:
        input_payload = [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}]
        text = self.request_response_text(
            model=model,
            input_payload=input_payload,
            temperature=temperature,
            context={"operation": "generate_description"},
        )
        return {"text": text}


# Creates a wrapper from environment settings.
def build_openai_wrapper(
    explicit_env_path: Optional[Path] = None,
    max_retries: int = 3,
    initial_backoff_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
) -> OpenAIWrapper:
    env_path = resolve_env_path(explicit_env_path)
    load_environment_variables(env_path)
    api_key = read_openai_api_key()
    return OpenAIWrapper(
        api_key=api_key,
        max_retries=max_retries,
        initial_backoff_seconds=initial_backoff_seconds,
        backoff_multiplier=backoff_multiplier,
    )
