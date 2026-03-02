import pytest
from pydantic import ValidationError

from investment_agent.schemas import (
    MarketDataSnapshot,
    Opportunity,
    ReportJSON,
    ReportMeta,
    ScoreBreakdown,
    ToolCallMeta,
)


def test_market_data_snapshot_requires_meta() -> None:
    with pytest.raises(ValidationError):
        MarketDataSnapshot(
            ticker="AAPL",
            as_of="2026-03-02",
        )


def test_report_json_v2_shape() -> None:
    report = ReportJSON(
        meta=ReportMeta(run_id="run_2026_03_02_001"),
        executive_summary="Example summary",
        ranked=[
            Opportunity(
                ticker="AAPL",
                score=ScoreBreakdown(total_score=75.0),
                confidence=0.7,
            )
        ],
    )
    assert report.meta.run_id == "run_2026_03_02_001"
    assert report.ranked[0].ticker == "AAPL"

    with pytest.raises(ValidationError):
        ReportJSON(
            executive_summary="missing meta should fail",
        )
