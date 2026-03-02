from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow running this file directly without setting PYTHONPATH.
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from investment_agent.config import load_config, load_universe
from investment_agent.reporting import build_batch_summary
from investment_agent.tools import FundamentalsTool, MarketDataTool, NewsTool
from investment_agent.workflow import ToolBundle, run_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _timestamped_run_root(base: str = "runs") -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (PROJECT_ROOT / base) / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _make_run_id() -> str:
    now = datetime.now(timezone.utc)
    date_tag = now.strftime("%Y_%m_%d")
    runs_root = PROJECT_ROOT / "runs"
    existing = sorted(runs_root.glob("*"))
    seq = len(existing) + 1
    return f"run_{date_tag}_{seq:03d}"


def _extract_total_score(report_obj: dict[str, Any]) -> float | None:
    try:
        ranked = report_obj.get("ranked", [])
        if isinstance(ranked, list) and ranked:
            score = ranked[0].get("score", {})
            if isinstance(score, dict) and "total_score" in score:
                return float(score["total_score"])
        if "overall_score" in report_obj:
            return float(report_obj["overall_score"])
    except Exception:
        return None
    return None


def _previous_total_score(current_run_root: Path, ticker: str) -> float | None:
    runs_root = PROJECT_ROOT / "runs"
    if not runs_root.exists():
        return None

    candidates = sorted([p for p in runs_root.iterdir() if p.is_dir() and p != current_run_root], reverse=True)
    for run_dir in candidates:
        report_path = run_dir / ticker / "report.json"
        if not report_path.exists():
            continue
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        score = _extract_total_score(payload)
        if score is not None:
            return score
    return None


def _build_tools() -> ToolBundle:
    cfg = load_config()
    return ToolBundle(
        market_data=MarketDataTool(cfg.market_data.base_url, cfg.market_data.api_key, cfg.http),
        fundamentals=FundamentalsTool(cfg.fundamentals.base_url, cfg.fundamentals.api_key, cfg.http),
        news=NewsTool(cfg.news.base_url, cfg.news.api_key, cfg.http),
    )


def run_single(
    ticker: str,
    run_root: Path,
    run_id: str,
    universe_id: str = "US_MegaCaps_v1",
    risk_profile: str = "balanced",
    quality_weight: float = 0.6,
    momentum_weight: float = 0.4,
) -> dict:
    run_dir = run_root / ticker
    run_dir.mkdir(parents=True, exist_ok=True)
    state = run_workflow(
        ticker=ticker,
        run_dir=run_dir,
        tools=_build_tools(),
        run_id=run_id,
        universe_id=universe_id,
        risk_profile=risk_profile,
        quality_weight=quality_weight,
        momentum_weight=momentum_weight,
        previous_total_score=_previous_total_score(run_root, ticker),
    )

    report_json = state.report_json or {}
    total_score = _extract_total_score(report_json) or 0.0

    return {
        "ticker": ticker,
        "errors": state.errors,
        "run_dir": str(run_dir),
        "report": report_json,
        "total_score": total_score,
        "confidence": state.confidence,
    }


def run_batch(
    universe: list[str],
    run_root: Path,
    run_id: str,
    max_symbols: int | None = None,
) -> dict:
    tickers = universe[:max_symbols] if max_symbols else universe
    results: list[dict] = []
    report_rows: list[dict] = []

    for ticker in tickers:
        result = run_single(ticker=ticker, run_root=run_root, run_id=run_id)
        results.append(result)
        report_rows.append(result["report"])

    summary_json, summary_md = build_batch_summary(report_rows)
    (run_root / "ranked_summary.json").write_text(
        json.dumps(summary_json, indent=2),
        encoding="utf-8",
    )
    (run_root / "ranked_summary.md").write_text(summary_md, encoding="utf-8")

    return {
        "num_tickers": len(tickers),
        "results": results,
        "summary_json_path": str(run_root / "ranked_summary.json"),
        "summary_md_path": str(run_root / "ranked_summary.md"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run autonomous investment workflow locally.")
    parser.add_argument("--ticker", help="Ticker to analyze (e.g., AAPL)")
    parser.add_argument("--batch", action="store_true", help="Run full universe batch mode")
    parser.add_argument("--max-symbols", type=int, default=None, help="Optional batch cap")
    parser.add_argument(
        "--universe-config",
        default=str(PROJECT_ROOT / "config/universe.yaml"),
        help="Universe config path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_root = _timestamped_run_root()
    run_id = _make_run_id()
    run_batch_mode = args.batch or not (args.ticker or "").strip()

    if run_batch_mode:
        universe = load_universe(args.universe_config)
        if not universe:
            raise SystemExit("Universe is empty.")
        result = run_batch(
            universe=universe,
            run_root=run_root,
            run_id=run_id,
            max_symbols=args.max_symbols,
        )
        print(f"Mode: batch ({result['num_tickers']} tickers)")
        print(f"Summary JSON: {result['summary_json_path']}")
        print(f"Summary Markdown: {result['summary_md_path']}")
        return

    ticker = (args.ticker or "").strip().upper()

    result = run_single(ticker=ticker, run_root=run_root, run_id=run_id)
    print(f"Mode: single ({ticker})")
    print(f"Errors: {len(result['errors'])}")
    print(f"Output Dir: {result['run_dir']}")


if __name__ == "__main__":
    main()
