from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ToolCallMeta(BaseModel):
    provider: str
    endpoint: str
    requested_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latency_ms: int = 0
    success: bool = False
    status_code: int | None = None
    retries: int = 0
    error: str | None = None


class MarketDataSnapshot(BaseModel):
    ticker: str
    as_of: str
    close: float | None = None
    change_pct_1d: float | None = None
    return_1m: float | None = None
    return_3m: float | None = None
    return_6m: float | None = None
    return_12m: float | None = None
    volatility_30d: float | None = None
    meta: ToolCallMeta


class FundamentalsSnapshot(BaseModel):
    ticker: str
    as_of: str
    revenue_growth_yoy: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    debt_to_equity: float | None = None
    roic: float | None = None
    pe_ratio: float | None = None
    meta: ToolCallMeta


class NewsItem(BaseModel):
    published_at: str
    title: str
    source: str
    url: HttpUrl | None = None
    sentiment: float | None = None


class NewsSnapshot(BaseModel):
    ticker: str
    as_of: str
    headlines: list[NewsItem] = Field(default_factory=list)
    sentiment_score: float | None = None
    risk_flags: list[str] = Field(default_factory=list)
    meta: ToolCallMeta


class ScoreBreakdown(BaseModel):
    quality_score: float = 0.0
    momentum_score: float = 0.0
    total_score: float = 0.0
    factors: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    claim: str
    source_url: str | None = None
    source_title: str = ""
    published_at: str = ""
    snippet: str = ""


class Opportunity(BaseModel):
    ticker: str
    company_name: str = ""
    summary: str = ""
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: float = 0.0
    score: ScoreBreakdown = Field(default_factory=ScoreBreakdown)


class MarketSnapshotOut(BaseModel):
    ticker: str
    currency: str = "USD"
    bars: list[dict] = Field(default_factory=list)
    return_3m: float | None = None
    return_12m: float | None = None
    volatility_30d: float | None = None


class FundamentalsSnapshotOut(BaseModel):
    ticker: str
    fiscal_year: int | None = None
    revenue_growth_yoy: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    pe_ttm: float | None = None
    price_to_sales: float | None = None
    free_cash_flow: float | None = None


class NewsSnapshotOut(BaseModel):
    query: str
    items: list[dict] = Field(default_factory=list)


class DataSnapshotItem(BaseModel):
    ticker: str
    market: MarketSnapshotOut
    fundamentals: FundamentalsSnapshotOut
    news: NewsSnapshotOut


class ToolCallRecord(BaseModel):
    tool: str
    attempt: int = 1
    started_at: str
    ended_at: str
    ok: bool
    request: dict = Field(default_factory=dict)
    response_summary: str = ""


class ReportMeta(BaseModel):
    run_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    universe_id: str = "US_MegaCaps_v1"
    risk_profile: str = "balanced"
    quality_weight: float = 0.6
    momentum_weight: float = 0.4
    partial: bool = False
    warnings: list[str] = Field(default_factory=list)


class ReportJSON(BaseModel):
    meta: ReportMeta
    executive_summary: str = ""
    top_opportunities: list[Opportunity] = Field(default_factory=list)
    ranked: list[Opportunity] = Field(default_factory=list)
    data_snapshots: list[DataSnapshotItem] = Field(default_factory=list)
    change_since_last_run: str = ""
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)


class StrategyResult(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=100.0)
    explanation: str
    factors: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
