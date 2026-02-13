# Week 2 Day 5 - Lab 1 (Chunking for RAG)

Starter project for experimenting with chunking strategies on:
- Trustworthy AI podcast transcript
- Trustworthy AI PDF

## Project Structure

- `src/lab1_chunking/`: Python package for chunking + evaluation logic
- `tests/`: unit/smoke tests
- `data/raw/`: source files from TA (podcast transcript, PDF)
- `data/processed/`: cleaned/intermediate files
- `notebooks/`: exploratory notebook work
- `docs/`: notes, findings, and final recommendations
- `outputs/`: generated reports/charts
- `chunks/`: exported chunk outputs by strategy

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Create local env file:
   - `cp .env.example .env`
4. Add your API keys to `.env`.
5. Run tests:
   - `pytest -q`

## Data Preparation (Lab Step-by-Step)

This first iteration uses fixed file names in `prepare_data.py`:
- `data/raw/The_Blueprint_For_Trustworthy_AI.m4a`
- `data/raw/ethics_guidelines_for_trustworthy_ai-fr_87FE7A3C-D03D-9305-81A653DDA84B5A60_60427.pdf`

Run from VS Code:
- Open `src/lab1_chunking/prepare_data.py`
- Click Run File

Run from terminal:
- `PYTHONPATH=src python -m lab1_chunking.prepare_data`

Outputs:
- `data/raw/podcast_transcript.txt`
- `data/raw/trustworthy_ai.pdf`
- `data/processed/trustworthy_ai_extracted.txt`

## Suggested Step-by-Step Lab Flow

1. Load podcast transcript and PDF from `data/raw/`.
2. Implement 2+ chunking strategies in `src/lab1_chunking/chunking.py`.
3. Compare chunk stats (count, min/max/avg size, overlap).
4. Visualize chunk boundaries and quality in `notebooks/`.
5. Write trade-offs and recommendations in `docs/`.
