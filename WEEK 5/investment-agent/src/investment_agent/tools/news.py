from __future__ import annotations

from datetime import datetime, timedelta, timezone

from investment_agent.schemas import NewsSnapshot
from investment_agent.tools.base import BaseAPITool, ToolResponse


class NewsTool(BaseAPITool):
    provider_name = "news"

    def _endpoint(self, path: str) -> str:
        if "/api/v1" in self.base_url:
            return path
        return f"api/v1/{path.lstrip('/')}"

    def fetch(self, ticker: str, limit: int = 10) -> ToolResponse:
        if "finnhub.io" in self.base_url:
            now = datetime.now(timezone.utc).date()
            from_date = (now - timedelta(days=30)).isoformat()
            to_date = now.isoformat()

            response = self._request(
                endpoint=self._endpoint("company-news"),
                params={
                    "symbol": ticker,
                    "from": from_date,
                    "to": to_date,
                    "token": self.api_key,
                },
            )
            if not response.meta.success or not isinstance(response.payload, list):
                return response

            raw_items = response.payload[: max(limit, 1)]
            headlines = []
            risk_flags: set[str] = set()
            risk_terms = {
                "lawsuit": "Legal risk",
                "investigation": "Regulatory risk",
                "downgrade": "Analyst downgrade",
                "layoff": "Workforce risk",
                "recall": "Product recall risk",
                "miss": "Earnings miss risk",
            }

            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                ts = item.get("datetime")
                published_at = datetime.now(timezone.utc).isoformat()
                if isinstance(ts, (int, float)):
                    published_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                title = str(item.get("headline", "")).strip()
                source = str(item.get("source", "")).strip()
                url = item.get("url")
                text = f"{title} {item.get('summary', '')}".lower()
                for key, label in risk_terms.items():
                    if key in text:
                        risk_flags.add(label)
                headlines.append(
                    {
                        "published_at": published_at,
                        "title": title,
                        "source": source or "unknown",
                        "url": url,
                    }
                )

            sentiment_resp = self._request(
                endpoint=self._endpoint("news-sentiment"),
                params={"symbol": ticker, "token": self.api_key},
            )
            sentiment_score = None
            if sentiment_resp.meta.success and isinstance(sentiment_resp.payload, dict):
                sentiment_score = sentiment_resp.payload.get("sentiment")

            normalized = {
                "ticker": ticker,
                "as_of": datetime.now(timezone.utc).isoformat(),
                "headlines": headlines,
                "sentiment_score": sentiment_score,
                "risk_flags": sorted(risk_flags),
                "meta": response.meta.model_dump(),
            }
        else:
            response = self._request(
                endpoint="news",
                params={"ticker": ticker, "limit": limit},
            )
            if not response.meta.success or not isinstance(response.payload, dict):
                return response

            items = response.payload.get("headlines")
            if not isinstance(items, list):
                items = []

            normalized = {
                "ticker": ticker,
                "as_of": response.payload.get("as_of")
                or datetime.now(timezone.utc).isoformat(),
                "headlines": items,
                "sentiment_score": response.payload.get("sentiment_score"),
                "risk_flags": response.payload.get("risk_flags") or [],
                "meta": response.meta.model_dump(),
            }

        model, validation_error = self._validate(NewsSnapshot, normalized)
        if validation_error:
            response.meta.success = False
            response.meta.error = f"schema_validation_error: {validation_error}"
            return ToolResponse(payload=None, meta=response.meta)

        return ToolResponse(payload=model, meta=response.meta)
