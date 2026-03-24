"""Daily scoring script — generates today's no-show risk report.

Run from the project root:
    python agent/run_daily_risk.py

Output: data/processed/daily_risk_report.csv
"""
from __future__ import annotations

from pathlib import Path

from agent.no_show_predictor import generate_daily_risk_report

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "daily_risk_report.csv"


def main() -> None:
    print("Generating daily no-show risk report...")
    report = generate_daily_risk_report(n_appointments=60)

    high_risk = (report["Risk Tier"] == "High").sum()
    medium_risk = (report["Risk Tier"] == "Medium").sum()
    print(f"  {len(report)} appointments scored | High: {high_risk} | Medium: {medium_risk}")

    report.to_csv(OUTPUT_PATH, index=False)
    print(f"  Saved to {OUTPUT_PATH}")

    print("\nTop 5 high-risk appointments:")
    cols = ["Date", "Time", "Specialty", "Provider", "No-Show Risk", "Risk Tier", "Key Risk Factors"]
    print(report[cols].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
