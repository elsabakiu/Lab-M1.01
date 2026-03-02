from investment_agent.schemas import FundamentalsSnapshot, MarketDataSnapshot, ToolCallMeta
from investment_agent.strategies import MomentumStrategy, QualityStrategy


def _meta(provider: str) -> ToolCallMeta:
    return ToolCallMeta(provider=provider, endpoint="test", success=True)


def test_quality_strategy_scores_with_valid_inputs() -> None:
    strategy = QualityStrategy()
    snap = FundamentalsSnapshot(
        ticker="AAPL",
        as_of="2026-03-02",
        revenue_growth_yoy=12.0,
        gross_margin=0.44,
        operating_margin=0.28,
        debt_to_equity=1.2,
        roic=0.19,
        pe_ratio=27.0,
        meta=_meta("fundamentals"),
    )

    result = strategy.evaluate(snap)
    assert result.name == "quality"
    assert 0.0 <= result.score <= 100.0
    assert "Quality score" in result.explanation


def test_momentum_strategy_scores_with_valid_inputs() -> None:
    strategy = MomentumStrategy()
    snap = MarketDataSnapshot(
        ticker="AAPL",
        as_of="2026-03-02",
        close=250.0,
        change_pct_1d=0.8,
        return_1m=3.2,
        return_3m=9.5,
        return_6m=16.1,
        return_12m=21.8,
        volatility_30d=25.0,
        meta=_meta("market_data"),
    )

    result = strategy.evaluate(snap)
    assert result.name == "momentum"
    assert 0.0 <= result.score <= 100.0
    assert "Momentum score" in result.explanation
