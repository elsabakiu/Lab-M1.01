from pathlib import Path

from investment_agent.schemas import FundamentalsSnapshot, MarketDataSnapshot, NewsSnapshot, ToolCallMeta
from investment_agent.tools.base import ToolResponse
from investment_agent.workflow import ToolBundle, run_workflow


class FakeTool:
    def __init__(self, payload, provider: str, fail: bool = False):
        self.payload = payload
        self.provider = provider
        self.fail = fail

    def fetch(self, ticker: str, limit: int = 10):  # noqa: ARG002
        meta = ToolCallMeta(provider=self.provider, endpoint="fake", success=not self.fail)
        if self.fail:
            meta.error = "forced_failure"
            return ToolResponse(payload=None, meta=meta)
        return ToolResponse(payload=self.payload, meta=meta)


def test_workflow_generates_json_and_markdown(tmp_path: Path) -> None:
    tools = ToolBundle(
        market_data=FakeTool(
            MarketDataSnapshot(
                ticker="AAPL",
                as_of="2026-03-02",
                close=250,
                return_1m=2,
                return_3m=4,
                volatility_30d=20,
                meta=ToolCallMeta(provider="market_data", endpoint="fake", success=True),
            ),
            provider="market_data",
        ),
        fundamentals=FakeTool(
            FundamentalsSnapshot(
                ticker="AAPL",
                as_of="2026-03-02",
                revenue_growth_yoy=10,
                gross_margin=0.4,
                operating_margin=0.2,
                debt_to_equity=1.0,
                roic=0.15,
                pe_ratio=24,
                meta=ToolCallMeta(provider="fundamentals", endpoint="fake", success=True),
            ),
            provider="fundamentals",
        ),
        news=FakeTool(
            NewsSnapshot(
                ticker="AAPL",
                as_of="2026-03-02",
                headlines=[],
                risk_flags=[],
                meta=ToolCallMeta(provider="news", endpoint="fake", success=True),
            ),
            provider="news",
        ),
    )

    state = run_workflow("AAPL", tmp_path / "AAPL", tools)

    assert state.report_json
    assert "meta" in state.report_json
    assert "ranked" in state.report_json
    assert state.report_markdown
    assert (tmp_path / "AAPL" / "report.json").exists()
    assert (tmp_path / "AAPL" / "report.md").exists()
    assert (tmp_path / "AAPL" / "react_trace.md").exists()


def test_workflow_handles_partial_failure(tmp_path: Path) -> None:
    tools = ToolBundle(
        market_data=FakeTool(
            MarketDataSnapshot(
                ticker="AAPL",
                as_of="2026-03-02",
                close=250,
                return_1m=1,
                return_3m=2,
                volatility_30d=20,
                meta=ToolCallMeta(provider="market_data", endpoint="fake", success=True),
            ),
            provider="market_data",
        ),
        fundamentals=FakeTool(None, provider="fundamentals", fail=True),
        news=FakeTool(None, provider="news", fail=True),
    )

    state = run_workflow("AAPL", tmp_path / "AAPL", tools, max_graph_retries=1, max_react_iterations=2)

    assert state.report_json
    assert len(state.errors) >= 1
    assert state.report_json["meta"]["partial"] is True
    assert (tmp_path / "AAPL" / "state.json").exists()
