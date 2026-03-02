from __future__ import annotations

from datetime import datetime, timezone

from investment_agent.schemas import FundamentalsSnapshot
from investment_agent.tools.base import BaseAPITool, ToolResponse


class FundamentalsTool(BaseAPITool):
    provider_name = "fundamentals"

    def _endpoint(self, path: str) -> str:
        if "/api/v3" in self.base_url:
            return path
        return f"api/v3/{path.lstrip('/')}"

    def fetch(self, ticker: str) -> ToolResponse:
        if "financialmodelingprep.com" in self.base_url:
            stable_resp = self._request(
                endpoint="stable/key-metrics-ttm",
                params={"symbol": ticker, "apikey": self.api_key},
            )

            metrics_row = {}
            meta = stable_resp.meta
            if stable_resp.meta.success and isinstance(stable_resp.payload, list) and stable_resp.payload:
                metrics_row = stable_resp.payload[0]
            else:
                # Fallback for accounts/environments where stable routes are unavailable.
                v3_resp = self._request(
                    endpoint=self._endpoint(f"key-metrics-ttm/{ticker}"),
                    params={"apikey": self.api_key},
                )
                if not v3_resp.meta.success:
                    return stable_resp
                meta = v3_resp.meta
                if isinstance(v3_resp.payload, list) and v3_resp.payload:
                    metrics_row = v3_resp.payload[0]

            normalized = {
                "ticker": ticker,
                "as_of": metrics_row.get("date") or datetime.now(timezone.utc).isoformat(),
                "revenue_growth_yoy": metrics_row.get("revenueGrowthTTM")
                or metrics_row.get("revenueGrowth"),
                "gross_margin": metrics_row.get("grossProfitMarginTTM"),
                "operating_margin": metrics_row.get("operatingProfitMarginTTM"),
                "debt_to_equity": metrics_row.get("debtToEquityTTM")
                or metrics_row.get("debtEquityRatioTTM"),
                "roic": metrics_row.get("roicTTM"),
                "pe_ratio": metrics_row.get("peRatioTTM"),
                "meta": meta.model_dump(),
            }
            response = ToolResponse(payload=normalized, meta=meta)
        else:
            response = self._request(endpoint="fundamentals", params={"ticker": ticker})
            if not response.meta.success or not isinstance(response.payload, dict):
                return response

            normalized = {
                "ticker": ticker,
                "as_of": response.payload.get("as_of")
                or datetime.now(timezone.utc).isoformat(),
                "revenue_growth_yoy": response.payload.get("revenue_growth_yoy"),
                "gross_margin": response.payload.get("gross_margin"),
                "operating_margin": response.payload.get("operating_margin"),
                "debt_to_equity": response.payload.get("debt_to_equity"),
                "roic": response.payload.get("roic"),
                "pe_ratio": response.payload.get("pe_ratio"),
                "meta": response.meta.model_dump(),
            }

        model, validation_error = self._validate(FundamentalsSnapshot, normalized)
        if validation_error:
            response.meta.success = False
            response.meta.error = f"schema_validation_error: {validation_error}"
            return ToolResponse(payload=None, meta=response.meta)

        return ToolResponse(payload=model, meta=response.meta)
