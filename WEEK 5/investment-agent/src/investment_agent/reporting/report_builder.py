from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from investment_agent.schemas import (
    DataSnapshotItem,
    EvidenceItem,
    FundamentalsSnapshotOut,
    MarketSnapshotOut,
    NewsSnapshotOut,
    Opportunity,
    ReportJSON,
    ReportMeta,
    ScoreBreakdown,
    ToolCallRecord,
)
from investment_agent.state import AgentState


def _recommendation(overall_score: float, confidence: float) -> str:
    if confidence < 0.35:
        return "Watch"
    if overall_score >= 80:
        return "Strong Buy"
    if overall_score >= 67:
        return "Buy"
    if overall_score >= 50:
        return "Hold"
    if overall_score >= 35:
        return "Watch"
    return "Avoid"


def _opportunity_from_state(state: AgentState) -> Opportunity:
    quality = state.scores.get("quality", 0.0)
    momentum = state.scores.get("momentum", 0.0)
    total = (quality * state.quality_weight) + (momentum * state.momentum_weight)

    all_factors: dict[str, float] = {}
    for bucket in state.score_factors.values():
        all_factors.update(bucket)

    notes: list[str] = []
    for bucket in state.score_notes.values():
        notes.extend(bucket)

    risks = list(state.collected_news.risk_flags if state.collected_news else [])
    if state.errors:
        risks.append("Partial data coverage reduced confidence")

    catalysts: list[str] = []
    if state.collected_market_data and state.collected_market_data.return_3m is not None:
        if state.collected_market_data.return_3m > 8:
            catalysts.append("Positive 3-month price trend")
        if state.collected_market_data.return_12m and state.collected_market_data.return_12m > 20:
            catalysts.append("Strong 12-month price momentum")

    bull_case: list[str] = []
    if quality >= 65:
        bull_case.append("Strong quality profile with healthy profitability and balance sheet metrics")
    if momentum >= 65:
        bull_case.append("Sustained momentum across multiple return windows")

    bear_case: list[str] = []
    if quality < 45:
        bear_case.append("Fundamentals are weak or incomplete for conviction")
    if momentum < 45:
        bear_case.append("Price trend is weak or volatile")

    evidence: list[EvidenceItem] = []
    if state.collected_news:
        for item in state.collected_news.headlines[:3]:
            evidence.append(
                EvidenceItem(
                    claim=item.title,
                    source_url=str(item.url) if item.url else None,
                    source_title=item.source,
                    published_at=item.published_at,
                    snippet=item.title,
                )
            )

    summary = (
        f"{state.ticker} combines quality score {quality:.1f} and momentum score {momentum:.1f}, "
        f"producing total score {total:.1f}."
    )

    return Opportunity(
        ticker=state.ticker,
        company_name=state.company_name,
        summary=summary,
        bull_case=bull_case,
        bear_case=bear_case,
        catalysts=sorted(set(catalysts)),
        risks=sorted(set(risks)),
        evidence=evidence,
        confidence=round(state.confidence, 2),
        score=ScoreBreakdown(
            quality_score=round(quality, 2),
            momentum_score=round(momentum, 2),
            total_score=round(total, 2),
            factors={k: round(v, 2) for k, v in all_factors.items()},
            notes=notes,
        ),
    )


def _snapshot_from_state(state: AgentState) -> DataSnapshotItem:
    market = state.collected_market_data
    fundamentals = state.collected_financials
    news = state.collected_news

    return DataSnapshotItem(
        ticker=state.ticker,
        market=MarketSnapshotOut(
            ticker=state.ticker,
            return_3m=market.return_3m if market else None,
            return_12m=market.return_12m if market else None,
            volatility_30d=market.volatility_30d if market else None,
        ),
        fundamentals=FundamentalsSnapshotOut(
            ticker=state.ticker,
            revenue_growth_yoy=fundamentals.revenue_growth_yoy if fundamentals else None,
            gross_margin=fundamentals.gross_margin if fundamentals else None,
            operating_margin=fundamentals.operating_margin if fundamentals else None,
            debt_to_equity=fundamentals.debt_to_equity if fundamentals else None,
            pe_ttm=fundamentals.pe_ratio if fundamentals else None,
        ),
        news=NewsSnapshotOut(
            query=f"{state.ticker} last 30 days",
            items=[item.model_dump(mode="json") for item in (news.headlines[:5] if news else [])],
        ),
    )


def build_report_json(state: AgentState) -> ReportJSON:
    opp = _opportunity_from_state(state)

    if state.previous_total_score is None:
        change = "No previous run found for comparison."
    else:
        delta = opp.score.total_score - state.previous_total_score
        sign = "+" if delta >= 0 else ""
        change = (
            f"{state.ticker} changed by {sign}{delta:.1f} points vs last run "
            f"({state.previous_total_score:.1f} -> {opp.score.total_score:.1f})."
        )

    state.change_since_last_run = change

    summary = (
        f"Analysis for {state.ticker}: recommendation {_recommendation(opp.score.total_score, state.confidence)}. "
        f"Quality={opp.score.quality_score:.1f}, Momentum={opp.score.momentum_score:.1f}."
    )

    tool_calls = [ToolCallRecord.model_validate(item) for item in state.tool_calls]

    return ReportJSON(
        meta=ReportMeta(
            run_id=state.run_id or f"run_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%M%S')}",
            created_at=datetime.now(timezone.utc).isoformat(),
            universe_id=state.universe_id,
            risk_profile=state.risk_profile,
            quality_weight=state.quality_weight,
            momentum_weight=state.momentum_weight,
            partial=bool(state.errors),
            warnings=state.errors,
        ),
        executive_summary=summary,
        top_opportunities=[opp],
        ranked=[opp],
        data_snapshots=[_snapshot_from_state(state)],
        change_since_last_run=change,
        tool_calls=tool_calls,
    )


def build_markdown_report(report: ReportJSON, state: AgentState) -> str:
    lines = [
        "# Investment Intelligence Report",
        "",
        f"- Run ID: {report.meta.run_id}",
        f"- Created At: {report.meta.created_at}",
        f"- Universe: {report.meta.universe_id}",
        f"- Risk Profile: {report.meta.risk_profile}",
        f"- Partial: {report.meta.partial}",
        "",
        "## Executive Summary",
        report.executive_summary,
        "",
        "## Top Opportunities",
    ]

    for idx, opp in enumerate(report.top_opportunities, start=1):
        lines.extend(
            [
                f"### {idx}. {opp.ticker}",
                f"- Summary: {opp.summary}",
                f"- Confidence: {opp.confidence:.2f}",
                f"- Quality Score: {opp.score.quality_score:.2f}",
                f"- Momentum Score: {opp.score.momentum_score:.2f}",
                f"- Total Score: {opp.score.total_score:.2f}",
                "- Bull Case:",
            ]
        )
        lines.extend([f"  - {item}" for item in (opp.bull_case or ["N/A"])])
        lines.append("- Bear Case:")
        lines.extend([f"  - {item}" for item in (opp.bear_case or ["N/A"])])
        lines.append("- Catalysts:")
        lines.extend([f"  - {item}" for item in (opp.catalysts or ["N/A"])])
        lines.append("- Risks:")
        lines.extend([f"  - {item}" for item in (opp.risks or ["N/A"])])

    lines.extend(["", "## Change Since Last Run", report.change_since_last_run, "", "## Tool Calls"])
    for call in report.tool_calls:
        lines.append(
            f"- {call.tool} attempt {call.attempt}: ok={call.ok} | {call.started_at} -> {call.ended_at} | {call.response_summary}"
        )

    if state.errors:
        lines.extend(["", "## Warnings", *[f"- {err}" for err in state.errors]])

    return "\n".join(lines).strip() + "\n"


def build_batch_summary(reports: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    parsed = [ReportJSON.model_validate(item) for item in reports]
    ranked_all = []
    snapshots = []
    tool_calls = []
    warnings: list[str] = []

    for report in parsed:
        ranked_all.extend(report.ranked)
        snapshots.extend(report.data_snapshots)
        tool_calls.extend(report.tool_calls)
        warnings.extend(report.meta.warnings)

    ranked_all = sorted(ranked_all, key=lambda item: item.score.total_score, reverse=True)
    top_opportunities = ranked_all[:3]

    if top_opportunities:
        tickers = ", ".join([opp.ticker for opp in top_opportunities[:2]])
        executive_summary = (
            f"This run identified {tickers} as the strongest opportunities under the configured "
            f"quality/momentum blend."
        )
    else:
        executive_summary = "No opportunities were ranked due to missing or invalid data."

    if len(parsed) >= 2:
        changes = [p.change_since_last_run for p in parsed if p.change_since_last_run]
        change_summary = changes[0] if changes else "No prior run deltas available."
    else:
        change_summary = parsed[0].change_since_last_run if parsed else "No prior run deltas available."

    run_id = parsed[0].meta.run_id if parsed else f"run_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%M%S')}"
    meta = ReportMeta(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        universe_id=parsed[0].meta.universe_id if parsed else "US_MegaCaps_v1",
        risk_profile=parsed[0].meta.risk_profile if parsed else "balanced",
        quality_weight=parsed[0].meta.quality_weight if parsed else 0.6,
        momentum_weight=parsed[0].meta.momentum_weight if parsed else 0.4,
        partial=any(p.meta.partial for p in parsed),
        warnings=warnings,
    )

    summary_report = ReportJSON(
        meta=meta,
        executive_summary=executive_summary,
        top_opportunities=top_opportunities,
        ranked=ranked_all,
        data_snapshots=snapshots,
        change_since_last_run=change_summary,
        tool_calls=tool_calls,
    )

    lines = [
        "# Batch Investment Intelligence Report",
        "",
        f"- Run ID: {summary_report.meta.run_id}",
        f"- Reports generated: {len(parsed)}",
        f"- Partial: {summary_report.meta.partial}",
        "",
        "## Executive Summary",
        summary_report.executive_summary,
        "",
        "## Top Opportunities",
    ]

    if summary_report.top_opportunities:
        for idx, opp in enumerate(summary_report.top_opportunities, start=1):
            lines.append(
                f"{idx}. {opp.ticker} - total={opp.score.total_score:.2f}, quality={opp.score.quality_score:.2f}, momentum={opp.score.momentum_score:.2f}"
            )
    else:
        lines.append("No opportunities available.")

    lines.extend(["", "## Full Ranking"])
    for idx, opp in enumerate(summary_report.ranked, start=1):
        lines.append(f"{idx}. {opp.ticker} - {opp.score.total_score:.2f} (confidence {opp.confidence:.2f})")

    return summary_report.model_dump(mode="json"), "\n".join(lines).strip() + "\n"
