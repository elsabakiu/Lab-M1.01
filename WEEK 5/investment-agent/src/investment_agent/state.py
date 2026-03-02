from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from investment_agent.schemas import FundamentalsSnapshot, MarketDataSnapshot, NewsSnapshot


class AgentState(BaseModel):
    ticker: str
    company_name: str = ""
    run_dir: str = ""
    run_id: str = ""
    universe_id: str = "US_MegaCaps_v1"
    risk_profile: str = "balanced"
    quality_weight: float = 0.6
    momentum_weight: float = 0.4

    collected_market_data: MarketDataSnapshot | None = None
    collected_financials: FundamentalsSnapshot | None = None
    collected_news: NewsSnapshot | None = None

    evidence_chunks: list[dict[str, Any]] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    score_explanations: dict[str, str] = Field(default_factory=dict)
    score_factors: dict[str, dict[str, float]] = Field(default_factory=dict)
    score_notes: dict[str, list[str]] = Field(default_factory=dict)
    tool_health: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    react_trace: list[dict[str, Any]] = Field(default_factory=list)
    workflow_path: list[str] = Field(default_factory=list)

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    errors: list[str] = Field(default_factory=list)
    retries: dict[str, int] = Field(default_factory=dict)
    previous_total_score: float | None = None
    change_since_last_run: str = ""

    report_markdown: str = ""
    report_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
