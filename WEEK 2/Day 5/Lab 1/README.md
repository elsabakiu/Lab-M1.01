# Week 2 Day 5 - Lab 1 (Chunking for RAG)

This project compares chunking strategies for two content types:
- Trustworthy AI podcast transcript
- Trustworthy AI PDF

The pipeline runs four strategies and generates chunk files, comparison tables, charts, and trade-off notes.

## Project Structure

- `src/lab1_chunking/`: core code (`prepare_data.py`, `chunking.py`, `main.py`)
- `data/raw/`: source audio/PDF files
- `data/processed/`: extracted transcript/PDF text used by analysis
- `chunks/`: exported chunk text files per strategy
- `outputs/`: analysis artifacts (tables, charts, boundary diagnostics)
- `tests/`: smoke/unit tests

## Strategies Implemented

- `Fixed-Size Chunking`
- `Recursive-Character Chunking`
- `Token-Based Chunking`
- `Semantic Chunking`

## Setup

1. Create and activate a Python environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy env template:
   - `cp .env.example .env`
4. Add your `OPENAI_API_KEY` to `.env`.

## Data Preparation

`prepare_data.py` is currently configured for these exact source files:
- `data/raw/The_Blueprint_For_Trustworthy_AI.m4a`
- `data/raw/ethics_guidelines_for_trustworthy_ai-fr_87FE7A3C-D03D-9305-81A653DDA84B5A60_60427.pdf`

Run from VS Code:
- Open `src/lab1_chunking/prepare_data.py`
- Click Run File

Run from terminal:
- `PYTHONPATH=src python -m lab1_chunking.prepare_data`

Generated files:
- `data/processed/podcast_transcript.txt`
- `data/processed/trustworthy_ai_extracted.txt`

## Run Chunking Analysis

Run from VS Code:
- Open `src/lab1_chunking/main.py`
- Click Run File

Run from terminal:
- `PYTHONPATH=src python -m lab1_chunking.main`

## Output Artifacts

Chunk files:
- `chunks/Fixed-Size-Chunking/`
- `chunks/Recursive-Character-Chunking/`
- `chunks/Token-Based-Chunking/`
- `chunks/Semantic-Chunking/`

Analysis outputs:
- `outputs/chunking_comparison_table.csv`
- `outputs/chunking_comparison_table.md`
- `outputs/chunk_boundary_quality.csv`
- `outputs/chunk_boundary_samples.txt`
- `outputs/chunk_size_distributions.png`
- `outputs/chunk_count_comparison.png`
- `outputs/chunking_tradeoffs.md`

