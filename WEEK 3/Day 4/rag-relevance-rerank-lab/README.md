# Week 3 Day 4 - Relevance Scoring and Rerankers Lab

Scaffold for building a trustworthy RAG pipeline over Trustworthy AI podcast transcripts and the EU AI Act.

## Learning goals

- Build a baseline retrieval pipeline with metadata filtering.
- Evaluate retrieval quality before reranking.
- Add optional relevance scoring and reranking.
- Compare retrieval behavior across approaches.

## Project structure

- `src/rag_relevance_rerank_lab/config.py`: env + model configuration
- `src/rag_relevance_rerank_lab/io_utils.py`: document loading helpers
- `src/rag_relevance_rerank_lab/eval.py`: retrieval metrics scaffolding
- `src/rag_relevance_rerank_lab/main.py`: end-to-end pipeline (ingest, metadata filter, rerank, answer, manual eval)
- `data/raw/`: put EU AI Act and transcript source files here
- `outputs/`: experiment outputs and reports
- `docs/comparison_report.md`: reporting template for before/after reranking analysis

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Create local env file:
   - `cp .env.example .env`
4. Add your `OPENAI_API_KEY` in `.env`.

## Run starter

```bash
PYTHONPATH=src python -m rag_relevance_rerank_lab.main
```

## Suggested implementation flow

1. Put transcript + EU AI Act text/PDF in `data/raw/`.
2. Ensure transcript `.txt` files are present in `data/processed/transcripts/`.
3. Tune metadata filters in `main.py` (`category`, `doc_type`, `section`, `source`).
4. Run manual evaluation to compare baseline vs reranked results.
5. Record findings in `docs/comparison_report.md`.
