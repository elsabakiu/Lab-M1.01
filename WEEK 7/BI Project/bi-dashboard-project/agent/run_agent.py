from __future__ import annotations

from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

try:
    from .insights_generator import generate_insights, serialize_insights
    from .validators import validate_insights
except ImportError:
    from insights_generator import generate_insights, serialize_insights
    from validators import validate_insights


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "agent_insights_latest.csv"


def run_agent() -> pd.DataFrame:
    load_dotenv(PROJECT_ROOT / ".env")
    insights = generate_insights()
    errors = validate_insights(insights)
    if errors:
        raise ValueError("Insight validation failed:\n" + "\n".join(errors))

    rows = serialize_insights(insights)
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_PATH, index=False)
    return df


def main() -> None:
    df = run_agent()
    print(f"Wrote {len(df)} insights to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
