"""Sequential, step-by-step LangChain RAG pipeline using Pinecone."""

from __future__ import annotations

import os
from pathlib import Path
import urllib.error
import urllib.request

from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

try:
    import cohere
except ImportError:  # pragma: no cover - optional dependency at runtime
    cohere = None

# Support both:
# 1) module execution: python -m rag_relevance_rerank_lab.main
# 2) direct file execution: python path/to/main.py
if __package__ in (None, ""):
    import sys

    # Add ".../src" so "rag_relevance_rerank_lab" package is importable.
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from rag_relevance_rerank_lab.config import load_settings
    from rag_relevance_rerank_lab.io_utils import read_pdf_file, read_text_file
else:
    from .config import load_settings
    from .io_utils import read_pdf_file, read_text_file

EVAL_QUERIES = [
    "What does the EU AI Act require for high-risk AI transparency?",
    "What obligations exist around human oversight in high-risk AI systems?",
    "How does the EU AI Act describe risk management requirements?",
]


def _step_1_load_source_documents(
    raw_dir: Path, transcript_dir: Path
) -> list[Document]:
    """Step 1: Load PDF docs and existing transcript docs into one list."""
    pdf_docs = _load_pdf_documents(raw_dir)
    transcript_files = _discover_transcript_files(transcript_dir)
    transcript_docs = _load_transcript_documents(transcript_files)

    all_docs = pdf_docs + transcript_docs
    print(f"Loaded {len(pdf_docs)} PDF docs and {len(transcript_docs)} transcript docs.")
    return all_docs


def _resolve_data_dirs() -> tuple[Path, Path]:
    """Resolve raw/transcript dirs from project root, with one-level-up fallback."""
    project_root = Path(__file__).resolve().parents[2]
    primary_raw = project_root / "data" / "raw"
    primary_transcripts = project_root / "data" / "processed" / "transcripts"

    fallback_raw = project_root.parent / "data" / "raw"
    fallback_transcripts = project_root.parent / "data" / "processed" / "transcripts"

    if primary_raw.exists() and any(primary_raw.iterdir()):
        return primary_raw, primary_transcripts
    if fallback_raw.exists() and any(fallback_raw.iterdir()):
        return fallback_raw, fallback_transcripts
    return primary_raw, primary_transcripts


def _discover_transcript_files(transcript_dir: Path) -> list[Path]:
    """Load existing transcript text files without re-transcribing audio."""
    if not transcript_dir.exists():
        return []
    return sorted(transcript_dir.glob("*.txt"))


def _step_2_chunk_documents(docs: list[Document], chunk_size: int, chunk_overlap: int) -> list[Document]:
    """Step 2: Split source documents into chunks for retrieval."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunked_docs = splitter.split_documents(docs)
    for idx, chunk in enumerate(chunked_docs):
        chunk.metadata["chunk_index"] = str(idx)
        chunk.metadata["section"] = _extract_section_label(chunk.page_content)
    print(f"Created {len(chunked_docs)} chunks.")
    return chunked_docs


def _step_3_build_vector_store(
    docs: list[Document], embeddings: Embeddings, settings
) -> PineconeVectorStore:
    """Step 3: Ensure Pinecone index exists and upsert all chunks."""
    pc = Pinecone(api_key=settings.pinecone_api_key)
    existing_index_names = {item["name"] for item in pc.list_indexes()}
    if settings.pinecone_index_name not in existing_index_names:
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=settings.embedding_dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=settings.pinecone_cloud,
                region=settings.pinecone_region,
            ),
        )

    vector_store = PineconeVectorStore(
        index_name=settings.pinecone_index_name,
        embedding=embeddings,
        namespace=settings.pinecone_namespace,
        pinecone_api_key=settings.pinecone_api_key,
    )
    vector_store.add_documents(docs)
    return vector_store


def _step_4_retrieve_candidates(
    vector_store: PineconeVectorStore,
    query: str,
    top_k: int,
    metadata_filter: dict | None = None,
) -> list[tuple[Document, float]]:
    """Step 4: Retrieve by similarity with optional metadata filter."""
    retrieved = vector_store.similarity_search_with_relevance_scores(
        query=query,
        k=max(top_k * 3, top_k),
        filter=metadata_filter,
    )
    return retrieved


def _cohere_dedicated_rerank(
    settings,
    query: str,
    retrieved: list[tuple[Document, float]],
    similarity_weight: float = 0.4,
    rerank_weight: float = 0.6,
) -> list[tuple[Document, float]]:
    if cohere is None:
        return []
    if not settings.cohere_api_key:
        return []
    if not retrieved:
        return []

    client = cohere.ClientV2(api_key=settings.cohere_api_key)
    docs_text = [doc.page_content[:3000] for doc, _ in retrieved]
    response = client.rerank(
        model=settings.cohere_rerank_model,
        query=query,
        documents=docs_text,
        top_n=len(docs_text),
    )

    scores_by_idx: dict[int, float] = {}
    for item in getattr(response, "results", []):
        idx = getattr(item, "index", None)
        rel = getattr(item, "relevance_score", None)
        if idx is not None and rel is not None:
            scores_by_idx[int(idx)] = float(rel)

    combined: list[tuple[Document, float]] = []
    for idx, (doc, sim_score) in enumerate(retrieved):
        rerank_score = scores_by_idx.get(idx, 0.0)
        combined_score = similarity_weight * sim_score + rerank_weight * rerank_score
        combined.append((doc, combined_score))

    combined.sort(key=lambda x: x[1], reverse=True)
    return combined


def _step_5_dedicated_rerank(
    settings,
    query: str,
    retrieved: list[tuple[Document, float]],
) -> tuple[list[tuple[Document, float]], str]:
    """Dedicated reranker: Cohere only, with baseline fallback."""
    cohere_ranked = _cohere_dedicated_rerank(settings, query, retrieved)
    if cohere_ranked:
        return cohere_ranked, "cohere"
    return retrieved, "baseline-fallback"


def _step_6_generate_answer(llm: ChatOpenAI, query: str, top_chunks: list[tuple[Document, float]]) -> str:
    """Step 6: Build prompt context from top chunks and ask the LLM."""
    context = _format_context(top_chunks)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a legal-tech assistant. Answer using only the provided context. "
                "If context is insufficient, say what is missing.",
            ),
            ("user", "Question: {query}\n\nContext:\n{context}"),
        ]
    )
    answer_chain = prompt | llm | StrOutputParser()
    return answer_chain.invoke({"query": query, "context": context})


def _run_manual_evaluation(
    settings,
    llm: ChatOpenAI,
    vector_store: PineconeVectorStore,
    queries: list[str],
    metadata_filter: dict | None,
) -> None:
    """Compare baseline vs reranked retrieval for manual quality evaluation."""
    print("\n=== Manual Evaluation: Baseline vs Reranked ===")
    print("For each query, review both answers and mark which one is better.\n")

    for i, query in enumerate(queries, start=1):
        retrieved = _step_4_retrieve_candidates(
            vector_store=vector_store,
            query=query,
            top_k=settings.top_k,
            metadata_filter=metadata_filter,
        )
        baseline_top = retrieved[: settings.rerank_top_n]
        reranked, backend = _step_5_dedicated_rerank(
            settings=settings,
            query=query,
            retrieved=retrieved,
        )
        reranked_top = reranked[: settings.rerank_top_n]

        baseline_answer = _step_6_generate_answer(
            llm=llm, query=query, top_chunks=baseline_top
        )
        reranked_answer = _step_6_generate_answer(
            llm=llm, query=query, top_chunks=reranked_top
        )

        print(f"\n{'=' * 80}")
        print(f"Query {i}: {query}")
        print(f"{'=' * 80}")
        print("\nBaseline top sources:")
        for doc, score in baseline_top:
            print(f"- {doc.metadata.get('source', 'unknown')} ({score:.4f})")
        print(f"\nReranked top sources ({backend}):")
        for doc, score in reranked_top:
            print(f"- {doc.metadata.get('source', 'unknown')} ({score:.4f})")

        print("\nBaseline answer:")
        print(baseline_answer)
        print("\nReranked answer:")
        print(reranked_answer)
        print("\nManual score template:")
        print("- Baseline correctness (0-1): ____")
        print("- Reranked correctness (0-1): ____")
        print("- Preferred answer (baseline/reranked): ____")


def main() -> int:
    settings = load_settings()

    raw_dir, transcript_dir = _resolve_data_dirs()
    print(f"Using raw data dir: {raw_dir}")

    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )
    llm = ChatOpenAI(
        model=settings.chat_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )

    # Step 1
    all_docs = _step_1_load_source_documents(
        raw_dir=raw_dir,
        transcript_dir=transcript_dir,
    )
    if not all_docs:
        print("No PDFs or transcript files found.")
        print("Add .pdf files to data/raw and transcript .txt files to data/processed/transcripts.")
        return 1

    # Step 2
    chunked_docs = _step_2_chunk_documents(
        docs=all_docs,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # Step 3
    vector_store = _step_3_build_vector_store(
        docs=chunked_docs,
        embeddings=embeddings,
        settings=settings,
    )

    # Step 4
    retrieval_filter = _build_metadata_filter(
        category="eu_ai_act",
        doc_type="pdf",
    )
    _run_manual_evaluation(
        settings=settings,
        llm=llm,
        vector_store=vector_store,
        queries=EVAL_QUERIES,
        metadata_filter=retrieval_filter,
    )
    return 0

def _load_pdf_documents(raw_dir: Path) -> list[Document]:
    """Load legal PDFs as LangChain Documents."""
    docs: list[Document] = []
    for path in sorted(raw_dir.rglob("*.pdf")):
        text = read_pdf_file(path).strip()
        if not text:
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": str(path.relative_to(raw_dir)),
                    "category": "eu_ai_act",
                    "doc_type": "pdf",
                    "section": "unknown",
                },
            )
        )
    return docs


def _load_transcript_documents(transcript_files: list[Path]) -> list[Document]:
    """Load transcript .txt files as podcast Documents."""
    docs: list[Document] = []
    for path in transcript_files:
        text = read_text_file(path).strip()
        if not text:
            continue
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": path.name,
                    "category": "podcast",
                    "doc_type": "transcript",
                    "section": "unknown",
                },
            )
        )
    return docs


def _extract_section_label(text: str) -> str:
    """Best-effort section label extraction from chunk text."""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("article "):
            return line[:80]
        if lower.startswith("chapter "):
            return line[:80]
        if lower.startswith("section "):
            return line[:80]
    return "unknown"


def _build_metadata_filter(
    category: str | None = None,
    doc_type: str | None = None,
    section: str | None = None,
    source: str | None = None,
) -> dict | None:
    """Build Pinecone metadata filter for retrieval."""
    clauses: list[dict] = []
    if category:
        clauses.append({"category": {"$eq": category}})
    if doc_type:
        clauses.append({"doc_type": {"$eq": doc_type}})
    if section:
        clauses.append({"section": {"$eq": section}})
    if source:
        clauses.append({"source": {"$eq": source}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _format_context(chunks: list[tuple[Document, float]]) -> str:
    """Format top chunks into one prompt context block."""
    lines: list[str] = []
    for i, (doc, score) in enumerate(chunks, start=1):
        lines.append(
            f"[Chunk {i} | {doc.metadata.get('source', 'unknown')} | score={score:.4f}]"
        )
        lines.append(doc.page_content[:700])
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
