from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp


class WebhookClient:
    def __init__(self, webhook_url: str, timeout_seconds: int = 10) -> None:
        self._webhook_url = webhook_url
        self._logger = logging.getLogger(self.__class__.__name__)
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_with_retries(self, payload: dict[str, Any]) -> bool:
        if self._session is None or self._session.closed:
            await self.start()

        assert self._session is not None
        backoffs = [0.5, 1.0, 2.0]

        for attempt, backoff in enumerate(backoffs, start=1):
            try:
                async with self._session.post(
                    self._webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if 200 <= response.status < 300:
                        self._logger.debug(
                            "Webhook POST succeeded for message_id=%s",
                            payload.get("message_id"),
                        )
                        return True

                    response_text = await response.text()
                    self._logger.error(
                        "Webhook POST failed (attempt %s/%s): status=%s body=%s",
                        attempt,
                        len(backoffs),
                        response.status,
                        response_text[:300],
                    )
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                self._logger.error(
                    "Webhook POST exception (attempt %s/%s): %s",
                    attempt,
                    len(backoffs),
                    exc,
                )

            if attempt < len(backoffs):
                await asyncio.sleep(backoff)

        self._logger.error(
            "Webhook POST permanently failed after %s attempts for message_id=%s",
            len(backoffs),
            payload.get("message_id"),
        )
        return False

