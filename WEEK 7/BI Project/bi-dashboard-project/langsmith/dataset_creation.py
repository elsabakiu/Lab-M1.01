"""Create or sync the ClinicIQ LangSmith dataset used for evaluation."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from eval_dataset import EVAL_CASES
from langsmith_config import configure_langsmith

RESULTS_DIR = PROJECT_ROOT / "langsmith" / "monitoring_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

LANGSMITH_CONFIG = configure_langsmith()
DEFAULT_DATASET_NAME = os.getenv(
    "LANGSMITH_DATASET_NAME",
    f"{LANGSMITH_CONFIG['project']} - Ops Insights Eval",
)


def create_dataset(dataset_name: str = DEFAULT_DATASET_NAME) -> dict[str, Any]:
    """Create the LangSmith dataset and save a local manifest."""
    manifest: dict[str, Any] = {
        "dataset_name": dataset_name,
        "example_count": len(EVAL_CASES),
        "status": "local_only",
    }

    api_key = LANGSMITH_CONFIG["api_key"]
    if not api_key:
        manifest["note"] = "LANGSMITH_API_KEY not set. Dataset manifest saved locally only."
        _write_manifest(manifest)
        return manifest

    try:
        from langsmith import Client
    except ImportError:
        manifest["note"] = "langsmith package not installed. Dataset manifest saved locally only."
        _write_manifest(manifest)
        return manifest

    client = Client(
        api_key=LANGSMITH_CONFIG["api_key"],
        api_url=LANGSMITH_CONFIG["endpoint"],
    )
    existing = [dataset for dataset in client.list_datasets() if dataset.name == dataset_name]
    if existing:
        dataset = existing[0]
    else:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=(
                "Evaluation cases for ClinicIQ operational insights. Covers no-shows, provider "
                "utilization, wait times, reminder effectiveness, and safety boundaries."
            ),
        )

    examples = [
        {
            "inputs": {"metrics": case["inputs"], "scenario": case["scenario"], "case_id": case["id"]},
            "outputs": {"expected": case["expected"]},
            "metadata": {"case_id": case["id"], "scenario": case["scenario"]},
        }
        for case in EVAL_CASES
    ]

    try:
        client.create_examples(dataset_id=dataset.id, examples=examples)
        manifest.update(
            {
                "status": "uploaded",
                "dataset_id": str(dataset.id),
                "note": "Dataset uploaded to LangSmith successfully.",
            }
        )
    except Exception as exc:
        manifest["note"] = f"Dataset exists, but example upload failed: {exc}"
        manifest["status"] = "partial"
        manifest["dataset_id"] = str(dataset.id)

    _write_manifest(manifest)
    return manifest


def _write_manifest(manifest: dict[str, Any]) -> None:
    output_path = RESULTS_DIR / "dataset_manifest.json"
    output_path.write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    result = create_dataset()
    print(json.dumps(result, indent=2))
