import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import matplotlib.pyplot as plt
import pandas as pd

# Support direct script execution:
# python src/lab1_chunking/main.py
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from lab1_chunking.chunking import (
    fixed_character_chunks,
    recursive_token_chunks,
    semantic_chunks,
    summarize_chunk_sizes,
    token_based_chunks,
)
from lab1_chunking.io_utils import read_text_file


PUNCT_ENDINGS = (".", "!", "?", '"', "'", ")", "]", "}", "...", ".”", "!\"", "?\"")


@dataclass(frozen=True)
class StrategyConfig:
    """One concrete chunking run configuration for a strategy."""

    config_label: str
    kwargs: dict[str, Any]


@dataclass(frozen=True)
class StrategySpec:
    """Metadata + executor function for a chunking strategy."""

    name: str
    folder: str
    file_label: str
    executor: Callable[..., list[str]]
    configs: list[StrategyConfig]


@dataclass
class ExperimentRows:
    """Accumulates flat rows used later for tables/plots/reports."""

    summary: list[dict[str, Any]]
    distribution: list[dict[str, Any]]
    boundary_samples: list[dict[str, Any]]


def dataframe_markdown_or_text(df: pd.DataFrame) -> str:
    """Use markdown when available; fallback to plain text when tabulate is missing."""
    try:
        return df.to_markdown(index=False)
    except Exception:
        return "```\n" + df.to_string(index=False) + "\n```"


def chunk_boundary_metrics(chunks: list[str]) -> tuple[float, float]:
    """Estimate how often chunk boundaries align with sentence/paragraph boundaries."""
    if len(chunks) <= 1:
        return 0.0, 0.0

    sentence_boundary_hits = 0
    paragraph_boundary_hits = 0
    boundaries = len(chunks) - 1

    for i in range(boundaries):
        prev_chunk = chunks[i].rstrip()
        if prev_chunk.endswith(PUNCT_ENDINGS):
            sentence_boundary_hits += 1
        if prev_chunk.endswith("\n") or prev_chunk.endswith("\n\n") or "\n\n" in prev_chunk[-10:]:
            paragraph_boundary_hits += 1

    return sentence_boundary_hits / boundaries, paragraph_boundary_hits / boundaries


def boundary_samples(chunks: list[str], max_samples: int = 5) -> list[tuple[str, str]]:
    """Return short previews around chunk boundaries for qualitative inspection."""
    samples: list[tuple[str, str]] = []
    if len(chunks) <= 1:
        return samples

    for i in range(len(chunks) - 1):
        prev_tail = chunks[i][-80:].replace("\n", " ").strip()
        next_head = chunks[i + 1][:80].replace("\n", " ").strip()
        samples.append((prev_tail, next_head))
        if len(samples) >= max_samples:
            break
    return samples


def append_experiment_rows(
    *,
    rows: ExperimentRows,
    strategy: str,
    document: str,
    config: str,
    chunks: list[str],
) -> None:
    """Store one run in normalized row format for downstream artifacts."""
    stats = summarize_chunk_sizes(chunks)
    sentence_rate, paragraph_rate = chunk_boundary_metrics(chunks)

    rows.summary.append(
        {
            "strategy": strategy,
            "document": document,
            "config": config,
            "total_chunks": stats.total_chunks,
            "min_size": stats.min_size,
            "max_size": stats.max_size,
            "avg_size": round(stats.avg_size, 2),
            "sentence_boundary_rate": round(sentence_rate, 3),
            "paragraph_boundary_rate": round(paragraph_rate, 3),
        }
    )

    for chunk in chunks:
        rows.distribution.append(
            {
                "strategy": strategy,
                "document": document,
                "config": config,
                "chunk_length": len(chunk),
            }
        )

    for idx, (tail, head) in enumerate(boundary_samples(chunks), start=1):
        rows.boundary_samples.append(
            {
                "strategy": strategy,
                "document": document,
                "config": config,
                "boundary_index": idx,
                "prev_tail": tail,
                "next_head": head,
            }
        )


def write_chunk_file(
    *,
    chunks_dir: Path,
    strategy_folder: str,
    strategy_name: str,
    document_name: str,
    config_label: str,
    chunks: list[str],
) -> Path:
    """Persist chunk text to disk for manual review and grading deliverables."""
    strategy_dir = chunks_dir / strategy_folder
    strategy_dir.mkdir(parents=True, exist_ok=True)

    safe_config = re.sub(r"[^a-zA-Z0-9_.-]+", "-", config_label)
    file_name = f"{document_name}_{strategy_name}_{safe_config}.txt"
    output_path = strategy_dir / file_name

    lines: list[str] = [
        f"Document: {document_name}",
        f"Chunking Strategy: {strategy_name}",
        f"Config: {config_label}",
        f"Total Chunks: {len(chunks)}",
        "",
    ]

    for idx, chunk in enumerate(chunks, start=1):
        lines.append(f"===== Chunk {idx} (length={len(chunk)}) =====")
        lines.append(chunk)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_strategy_for_document(
    *,
    text: str,
    document: str,
    spec: StrategySpec,
    chunks_dir: Path,
    rows: ExperimentRows,
) -> None:
    """Execute every config of one strategy for a single document."""
    for config in spec.configs:
        chunks = spec.executor(text=text, **config.kwargs)
        append_experiment_rows(
            rows=rows,
            strategy=spec.name,
            document=document,
            config=config.config_label,
            chunks=chunks,
        )
        write_chunk_file(
            chunks_dir=chunks_dir,
            strategy_folder=spec.folder,
            strategy_name=spec.file_label,
            document_name=document,
            config_label=config.config_label,
            chunks=chunks,
        )


def save_visualizations(
    *,
    outputs_dir: Path,
    summary_df: pd.DataFrame,
    distribution_df: pd.DataFrame,
) -> None:
    """Create summary tables and chart artifacts used in the lab report."""
    if summary_df.empty:
        return

    summary_csv = outputs_dir / "chunking_comparison_table.csv"
    summary_md = outputs_dir / "chunking_comparison_table.md"
    boundary_csv = outputs_dir / "chunk_boundary_quality.csv"

    summary_df.to_csv(summary_csv, index=False)
    summary_md.write_text(dataframe_markdown_or_text(summary_df), encoding="utf-8")
    summary_df[
        ["strategy", "document", "config", "sentence_boundary_rate", "paragraph_boundary_rate"]
    ].to_csv(boundary_csv, index=False)

    if distribution_df.empty:
        return

    documents = sorted(distribution_df["document"].unique())
    strategies = sorted(distribution_df["strategy"].unique())

    fig, axes = plt.subplots(1, len(documents), figsize=(7 * len(documents), 5), squeeze=False)
    for i, document in enumerate(documents):
        ax = axes[0][i]
        subset = distribution_df[distribution_df["document"] == document]
        data = [subset[subset["strategy"] == strategy]["chunk_length"].values for strategy in strategies]
        ax.boxplot(data, tick_labels=strategies, showfliers=False)
        ax.set_title(f"Chunk Length Distribution - {document}")
        ax.set_ylabel("Chunk length (characters)")
        ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(outputs_dir / "chunk_size_distributions.png", dpi=160)
    plt.close(fig)

    avg_counts = (
        summary_df.groupby(["document", "strategy"], as_index=False)["total_chunks"]
        .mean()
        .rename(columns={"total_chunks": "avg_total_chunks"})
    )
    fig, axes = plt.subplots(1, len(documents), figsize=(7 * len(documents), 5), squeeze=False)
    for i, document in enumerate(documents):
        ax = axes[0][i]
        subset = avg_counts[avg_counts["document"] == document]
        ax.bar(subset["strategy"], subset["avg_total_chunks"])
        ax.set_title(f"Average Chunk Count - {document}")
        ax.set_ylabel("Average chunks per config")
        ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(outputs_dir / "chunk_count_comparison.png", dpi=160)
    plt.close(fig)


def write_boundary_samples_report(outputs_dir: Path, rows: ExperimentRows) -> None:
    out_path = outputs_dir / "chunk_boundary_samples.txt"
    if not rows.boundary_samples:
        out_path.write_text("No boundary samples available.\n", encoding="utf-8")
        return

    lines: list[str] = []
    for row in rows.boundary_samples:
        lines.append(f"[{row['strategy']} | {row['document']} | {row['config']} | boundary {row['boundary_index']}]")
        lines.append(f"prev_tail: {row['prev_tail']}")
        lines.append(f"next_head: {row['next_head']}")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_tradeoffs_report(outputs_dir: Path, summary_df: pd.DataFrame) -> None:
    out_path = outputs_dir / "chunking_tradeoffs.md"
    if summary_df.empty:
        out_path.write_text("No chunking results available.\n", encoding="utf-8")
        return

    grouped = summary_df.groupby("strategy", as_index=False).agg(
        avg_chunks=("total_chunks", "mean"),
        avg_chunk_len=("avg_size", "mean"),
        avg_sentence_boundary=("sentence_boundary_rate", "mean"),
        avg_paragraph_boundary=("paragraph_boundary_rate", "mean"),
    )

    lines = [
        "# Chunking Trade-offs",
        "",
        "## Strategy Summary",
        dataframe_markdown_or_text(grouped.round(3)),
        "",
        "## Notes",
        "- Higher `avg_chunks` means more granular retrieval but more index entries.",
        "- Higher `avg_chunk_len` means richer context per chunk but potentially noisier retrieval.",
        "- Higher `avg_sentence_boundary` usually indicates cleaner semantic boundaries.",
        "- Higher `avg_paragraph_boundary` suggests better paragraph-aware splits.",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def load_document_text(candidates: list[Path]) -> str | None:
    for path in candidates:
        if path.exists():
            return read_text_file(path)
    return None


def build_strategy_specs(
    *,
    fixed_sizes: list[int],
    overlaps: list[int],
    token_sizes: list[int],
    separator_profiles: dict[str, list[str]],
    semantic_thresholds: list[float],
    semantic_sample_chars: int,
) -> list[StrategySpec]:
    """Create every strategy/config combination in one place."""
    fixed_configs = [
        StrategyConfig(
            config_label=f"chunk-size={chunk_size},overlap={overlap}",
            kwargs={"chunk_size": chunk_size, "chunk_overlap": overlap},
        )
        for chunk_size in fixed_sizes
        for overlap in overlaps
        if overlap < chunk_size
    ]

    recursive_configs = [
        StrategyConfig(
            config_label=f"profile={profile},chunk-size={chunk_size},overlap={overlap}",
            kwargs={"chunk_size": chunk_size, "chunk_overlap": overlap, "separators": separators},
        )
        for profile, separators in separator_profiles.items()
        for chunk_size in fixed_sizes
        for overlap in overlaps
        if overlap < chunk_size
    ]

    token_configs = [
        StrategyConfig(
            config_label=f"chunk-size={chunk_size},overlap={overlap}",
            kwargs={"chunk_size": chunk_size, "chunk_overlap": overlap},
        )
        for chunk_size in token_sizes
        for overlap in overlaps
        if overlap < chunk_size
    ]

    semantic_configs = [
        StrategyConfig(
            config_label=f"threshold={threshold:.2f},sample={semantic_sample_chars}",
            kwargs={"threshold": threshold},
        )
        for threshold in semantic_thresholds
    ]

    # Semantic runs are intentionally sample-limited for speed.
    def semantic_on_sample(*, text: str, threshold: float) -> list[str]:
        return semantic_chunks(text[:semantic_sample_chars], threshold=threshold)

    return [
        StrategySpec(
            name="Fixed-Size",
            folder="Fixed-Size-Chunking",
            file_label="Fixed-Size Chunking",
            executor=fixed_character_chunks,
            configs=fixed_configs,
        ),
        StrategySpec(
            name="Recursive-Character",
            folder="Recursive-Character-Chunking",
            file_label="Recursive-Character Chunking",
            executor=recursive_token_chunks,
            configs=recursive_configs,
        ),
        StrategySpec(
            name="Token-Based",
            folder="Token-Based-Chunking",
            file_label="Token-Based Chunking",
            executor=token_based_chunks,
            configs=token_configs,
        ),
        StrategySpec(
            name="Semantic",
            folder="Semantic-Chunking",
            file_label="Semantic Chunking",
            executor=semantic_on_sample,
            configs=semantic_configs,
        ),
    ]


def main() -> None:
    # 1) Resolve paths and make sure output folders exist.
    project_root = Path(__file__).resolve().parents[2]
    processed_dir = project_root / "data" / "processed"
    raw_dir = project_root / "data" / "raw"
    chunks_dir = project_root / "chunks"
    outputs_dir = project_root / "outputs"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # 2) Configure strategy grids.
    fixed_sizes = [500, 1000, 2000]
    overlaps = [0, 50, 100]
    token_sizes = [500, 1000]
    semantic_thresholds = [0.65, 0.70, 0.75]
    semantic_sample_chars = 5000
    separator_profiles = {
        "semantic": ["\n\n", "\n", ". ", " ", ""],
        "line_first": ["\n", "\n\n", ". ", " ", ""],
        "sentence": [". ", "\n\n", "\n", " ", ""],
    }

    strategy_specs = build_strategy_specs(
        fixed_sizes=fixed_sizes,
        overlaps=overlaps,
        token_sizes=token_sizes,
        separator_profiles=separator_profiles,
        semantic_thresholds=semantic_thresholds,
        semantic_sample_chars=semantic_sample_chars,
    )

    # 3) Load source documents.
    transcript_candidates = [raw_dir / "podcast_transcript.txt", processed_dir / "podcast_transcript.txt"]
    pdf_text_candidates = [processed_dir / "trustworthy_ai_extracted.txt"]
    documents = {
        "podcast": load_document_text(transcript_candidates),
        "pdf": load_document_text(pdf_text_candidates),
    }

    if documents["podcast"] is None:
        print(f"Missing transcript file. Checked: {', '.join(str(p) for p in transcript_candidates)}")
    if documents["pdf"] is None:
        print(f"Missing PDF extracted text file. Checked: {', '.join(str(p) for p in pdf_text_candidates)}")

    # 4) Run every strategy over every available document and collect rows.
    rows = ExperimentRows(summary=[], distribution=[], boundary_samples=[])
    for document_name, text in documents.items():
        if text is None:
            continue
        for spec in strategy_specs:
            run_strategy_for_document(
                text=text,
                document=document_name,
                spec=spec,
                chunks_dir=chunks_dir,
                rows=rows,
            )

    # 5) Save tabular + visual artifacts for the report.
    summary_df = pd.DataFrame(rows.summary)
    distribution_df = pd.DataFrame(rows.distribution)

    if summary_df.empty:
        print("No experiment results to display.")
        return

    summary_df = summary_df.sort_values(["document", "strategy", "config"]).reset_index(drop=True)
    print("\n=== Chunking Comparison Table ===")
    print(summary_df.to_string(index=False))

    save_visualizations(outputs_dir=outputs_dir, summary_df=summary_df, distribution_df=distribution_df)
    write_boundary_samples_report(outputs_dir=outputs_dir, rows=rows)
    write_tradeoffs_report(outputs_dir=outputs_dir, summary_df=summary_df)

    print("\nSaved analysis artifacts:")
    print(f"- {outputs_dir / 'chunking_comparison_table.csv'}")
    print(f"- {outputs_dir / 'chunking_comparison_table.md'}")
    print(f"- {outputs_dir / 'chunk_boundary_quality.csv'}")
    print(f"- {outputs_dir / 'chunk_boundary_samples.txt'}")
    print(f"- {outputs_dir / 'chunk_size_distributions.png'}")
    print(f"- {outputs_dir / 'chunk_count_comparison.png'}")
    print(f"- {outputs_dir / 'chunking_tradeoffs.md'}")


if __name__ == "__main__":
    main()
