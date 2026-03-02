from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone

from investment_agent.schemas import MarketDataSnapshot
from investment_agent.tools.base import BaseAPITool, ToolResponse


class MarketDataTool(BaseAPITool):
    provider_name = "market_data"

    def fetch(self, ticker: str) -> ToolResponse:
        if "alphavantage.co" in self.base_url:
            response = self._request(
                endpoint="query",
                params={
                    "function": "TIME_SERIES_DAILY",
                    "symbol": ticker,
                    "outputsize": "compact",
                    "apikey": self.api_key,
                },
            )
            if not response.meta.success or not isinstance(response.payload, dict):
                return response

            series = response.payload.get("Time Series (Daily)")
            if not isinstance(series, dict) or not series:
                response.meta.success = False
                response.meta.error = (
                    response.payload.get("Error Message")
                    or response.payload.get("Note")
                    or response.payload.get("Information")
                    or "unexpected_alpha_vantage_response"
                )
                return ToolResponse(payload=None, meta=response.meta)

            dates = sorted(series.keys(), reverse=True)
            closes: list[float] = []
            for date in dates:
                row = series.get(date, {})
                try:
                    closes.append(float(row.get("4. close")))
                except (TypeError, ValueError):
                    continue

            if not closes:
                response.meta.success = False
                response.meta.error = "no_close_prices_found"
                return ToolResponse(payload=None, meta=response.meta)

            def pct_return(window: int) -> float | None:
                if len(closes) <= window:
                    return None
                base = closes[window]
                if base == 0:
                    return None
                return ((closes[0] / base) - 1.0) * 100.0

            daily_returns: list[float] = []
            for idx in range(min(len(closes) - 1, 30)):
                prev = closes[idx + 1]
                curr = closes[idx]
                if prev == 0:
                    continue
                daily_returns.append((curr / prev) - 1.0)

            volatility_30d = None
            if len(daily_returns) >= 2:
                volatility_30d = statistics.pstdev(daily_returns) * math.sqrt(252) * 100.0

            change_pct_1d = None
            if len(closes) >= 2 and closes[1] != 0:
                change_pct_1d = ((closes[0] / closes[1]) - 1.0) * 100.0

            normalized = {
                "ticker": ticker,
                "as_of": dates[0],
                "close": closes[0],
                "change_pct_1d": change_pct_1d,
                "return_1m": pct_return(21),
                "return_3m": pct_return(63),
                "return_6m": pct_return(126),
                "return_12m": pct_return(252),
                "volatility_30d": volatility_30d,
                "meta": response.meta.model_dump(),
            }
        else:
            response = self._request(endpoint="market-data", params={"ticker": ticker})
            if not response.meta.success or not isinstance(response.payload, dict):
                return response

            normalized = {
                "ticker": ticker,
                "as_of": response.payload.get("as_of")
                or datetime.now(timezone.utc).isoformat(),
                "close": response.payload.get("close"),
                "change_pct_1d": response.payload.get("change_pct_1d"),
                "return_1m": response.payload.get("return_1m"),
                "return_3m": response.payload.get("return_3m"),
                "return_6m": response.payload.get("return_6m"),
                "return_12m": response.payload.get("return_12m"),
                "volatility_30d": response.payload.get("volatility_30d"),
                "meta": response.meta.model_dump(),
            }

        model, validation_error = self._validate(MarketDataSnapshot, normalized)
        if validation_error:
            response.meta.success = False
            response.meta.error = f"schema_validation_error: {validation_error}"
            return ToolResponse(payload=None, meta=response.meta)

        return ToolResponse(payload=model, meta=response.meta)
