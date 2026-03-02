from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests
from pydantic import ValidationError

from investment_agent.config import HttpSettings
from investment_agent.schemas import ToolCallMeta


@dataclass
class ToolResponse:
    payload: Any | None
    meta: ToolCallMeta


class BaseAPITool:
    provider_name = "generic"

    def __init__(self, base_url: str, api_key: str, http_settings: HttpSettings):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.http = http_settings

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(self, endpoint: str, params: dict[str, Any]) -> ToolResponse:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retries_used = 0
        start = time.perf_counter()
        last_error = ""
        status_code: int | None = None

        for attempt in range(self.http.max_retries + 1):
            retries_used = attempt
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=self._headers(),
                    timeout=self.http.timeout_seconds,
                )
                status_code = response.status_code
                response.raise_for_status()
                latency_ms = int((time.perf_counter() - start) * 1000)
                return ToolResponse(
                    payload=response.json(),
                    meta=ToolCallMeta(
                        provider=self.provider_name,
                        endpoint=endpoint,
                        latency_ms=latency_ms,
                        success=True,
                        status_code=status_code,
                        retries=retries_used,
                    ),
                )
            except (requests.RequestException, ValueError) as exc:
                last_error = str(exc)
                if attempt < self.http.max_retries:
                    time.sleep(self.http.backoff_seconds * (2**attempt))
                continue

        latency_ms = int((time.perf_counter() - start) * 1000)
        return ToolResponse(
            payload=None,
            meta=ToolCallMeta(
                provider=self.provider_name,
                endpoint=endpoint,
                latency_ms=latency_ms,
                success=False,
                status_code=status_code,
                retries=retries_used,
                error=last_error or "request_failed",
            ),
        )

    @staticmethod
    def _validate(model_cls: Any, data: dict[str, Any]) -> tuple[Any | None, str | None]:
        try:
            return model_cls.model_validate(data), None
        except ValidationError as exc:
            return None, str(exc)
