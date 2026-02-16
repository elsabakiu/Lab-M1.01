# Week 2 Day 5 - Lab 2 (RAG with OpenAI Native APIs)

Build a complete Retrieval-Augmented Generation (RAG) pipeline using OpenAI APIs directly.

## Learning Goals

- Implement embeddings with OpenAI directly
- Store vectors and perform similarity retrieval
- Build end-to-end RAG question answering over documents
- Understand each pipeline stage without framework abstraction

## Project Structure

- `src/lab2_rag_openai/config.py`: env + model config helpers
- `src/lab2_rag_openai/io_utils.py`: text/PDF loading
- `src/lab2_rag_openai/chunking.py`: baseline chunking
- `src/lab2_rag_openai/openai_client.py`: native OpenAI API wrappers
- `src/lab2_rag_openai/vector_store.py`: in-memory vector storage + cosine search
- `src/lab2_rag_openai/pipeline.py`: indexing + retrieval + answering flow
- `src/lab2_rag_openai/main.py`: runnable starter script
- `data/raw/`: source docs
- `outputs/`: future reports/results

## Setup

1. Create and activate virtual env.
2. Install requirements:
   - `pip install -r requirements.txt`
3. Create local env:
   - `cp .env.example .env`
4. Add your `OPENAI_API_KEY` in `.env`.

## Quick Run

1. Put your document in `data/raw/` (PDF or TXT).
2. Update `default_doc` in `src/lab2_rag_openai/main.py` if needed.
3. Run:
   - `PYTHONPATH=src python -m lab2_rag_openai.main`

## Current Pipeline (Starter)

1. Load document text
2. Chunk document into fixed-size chunks
3. Generate embeddings via OpenAI
4. Store embeddings in in-memory vector store
5. Embed question and retrieve top-k chunks
6. Generate answer from retrieved context using OpenAI chat

## Notes

- This scaffold intentionally uses an in-memory store first.
- You can later swap `vector_store.py` with Pinecone/FAISS/Weaviate.
- Keep this implementation as the "native baseline" before adding abstractions.
