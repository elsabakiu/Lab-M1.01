from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

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


# Creates an OpenAI client from a key.
def create_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


# Full helper to build an OpenAI client from env settings.
def build_openai_client(explicit_env_path: Optional[Path] = None) -> OpenAI:
    env_path = resolve_env_path(explicit_env_path)
    load_environment_variables(env_path)
    api_key = read_openai_api_key()
    return create_openai_client(api_key)


# Sends one generic Responses API call and returns output_text.
def request_response_text(
    client: OpenAI,
    model: str,
    input_payload: Any,
    temperature: Optional[float] = None,
) -> str:
    request_kwargs: dict[str, Any] = {"model": model, "input": input_payload}
    if temperature is not None:
        request_kwargs["temperature"] = temperature

    try:
        response = client.responses.create(**request_kwargs)
    except Exception as error:
        report_error(
            function_name="request_response_text",
            error=error,
            location=f"model={model}",
            suggestion="Check internet access, API key, model name, quota, and rate limits.",
        )
        raise

    raw_text = response.output_text
    if not raw_text:
        error = RuntimeError("Empty response.output_text")
        report_error(
            function_name="request_response_text",
            error=error,
            location=f"model={model}",
            suggestion="Retry request or check if the model returned non-text output.",
        )
        raise error
    return raw_text
