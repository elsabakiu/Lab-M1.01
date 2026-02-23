# Relevance Scoring and Rerankers Lab (Week 3, Day 4)

This project builds an advanced RAG pipeline for legal-tech style questions over:
- EU AI Act PDF content
- Trustworthy AI podcast transcript text files

It demonstrates retrieval quality improvements using:
- Baseline vector similarity retrieval
- LLM-based chunk relevance scoring
- Dedicated reranking with Cohere
- A controlled comparison across all methods

## Lab goals covered
- Metadata-enriched chunking and metadata filtering
- Retrieval with and without reranking
- LLM relevance scoring (optional advanced step)
- Cohere reranker integration (optional advanced step)
- Side-by-side method comparison:
  - baseline
  - llm-only
  - cohere-only
  - combined (llm -> cohere)

## Project layout
- `src/rag_relevance_rerank_lab/main.py`: end-to-end pipeline and evaluation loop
- `src/rag_relevance_rerank_lab/config.py`: environment and runtime settings
- `src/rag_relevance_rerank_lab/io_utils.py`: PDF/text loaders
- `src/rag_relevance_rerank_lab/eval.py`: metric helper functions
- `docs/comparison_report.md`: manual comparison report
- `data/raw/`: source PDFs
- `data/processed/transcripts/`: transcript `.txt` files

## Requirements
- Python 3.11+
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `COHERE_API_KEY` (required if you want Cohere reranking)

Install:

```bash
pip install -r requirements.txt
```

## Environment setup
Create `.env` in project root (or use existing root-level `.env`):

```bash
cp .env.example .env
```

Minimum keys:
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`

Optional/advanced:
- `COHERE_API_KEY`

## Data setup
1. Place EU AI Act and related PDFs in `data/raw/`.
2. Place transcript files in `data/processed/transcripts/` as `.txt`.

If no transcript files are present, the pipeline still runs on PDFs only.

## Run
From `WEEK 3/Day 4/rag-relevance-rerank-lab`:

```bash
PYTHONPATH=src python -m rag_relevance_rerank_lab.main
```

## What the script does
`main.py` currently executes this flow:
1. Load PDFs and transcript text docs.
2. Chunk documents and enrich metadata (`source`, `category`, `doc_type`, `section`, `chunk_index`).
3. Build/upsert Pinecone vector index.
4. Retrieve candidates with metadata filter.
5. Run controlled comparison for each query:
   - baseline retrieval
   - llm-only relevance reordering
   - cohere-only reranking
   - combined llm->cohere reranking
6. Generate answer per method and print a manual scoring template.

## Current retrieval filter behavior
The default evaluation in `main.py` applies:
- `category = "eu_ai_act"`
- `doc_type = "pdf"`

This intentionally focuses comparison on legal PDF chunks.

## Configurable settings
Key `.env` / config options:
- `OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-small`)
- `OPENAI_CHAT_MODEL` (default `gpt-4o-mini`)
- `COHERE_RERANK_MODEL` (default `rerank-v3.5`)
- `PINECONE_INDEX_NAME`, `PINECONE_NAMESPACE`, `PINECONE_CLOUD`, `PINECONE_REGION`
- `EMBEDDING_DIMENSION` (default `1536`)

LLM relevance controls:
- `ENABLE_LLM_RELEVANCE` (default `true`)
- `LLM_RELEVANCE_TOP_N` (default `12`)
- `LLM_SIMILARITY_WEIGHT` (default `0.4`)
- `LLM_RELEVANCE_WEIGHT` (default `0.6`)

## Expected terminal output
The run prints:
- loaded document counts
- chunk count
- per-query top sources for each method
- per-query answers for each method
- manual scoring template fields

Use those outputs to fill `docs/comparison_report.md`.

## Notes
- If one source dominates the corpus, method differences may appear small.
- The controlled comparison is method-isolated and useful for analysis, even when answers are similar.
- For stronger conclusions, expand query coverage and add automated metrics in the loop.
