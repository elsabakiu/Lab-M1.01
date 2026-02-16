from pathlib import Path

from lab2_rag_openai.chunking import Chunk, recursive_character_chunking
from lab2_rag_openai.io_utils import read_pdf_text, read_text_file
from lab2_rag_openai.openai_client import OpenAIService
from lab2_rag_openai.vector_store import EmbeddedChunk, InMemoryVectorStore


def load_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return read_pdf_text(path)
    return read_text_file(path)


def discover_documents(dataset_root: Path) -> list[Path]:
    allowed = {".pdf", ".txt", ".htm", ".html", ".md", ".csv"}
    return sorted(path for path in dataset_root.rglob("*") if path.is_file() and path.suffix.lower() in allowed)


def build_index(
    document_path: Path,
    source_name: str,
    service: OpenAIService,
    chunk_size: int = 1000,
    overlap: int = 120,
    embedding_batch_size: int = 100,
) -> tuple[InMemoryVectorStore, list[Chunk]]:
    text = load_document(document_path)
    chunks = recursive_character_chunking(
        text=text,
        source=source_name,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    embeddings = service.get_embeddings_batch(
        texts=[c.text for c in chunks],
        batch_size=embedding_batch_size,
        log_progress=True,
    )

    store = InMemoryVectorStore()
    store.add([EmbeddedChunk(chunk=chunk, embedding=embedding) for chunk, embedding in zip(chunks, embeddings)])
    return store, chunks


def build_index_from_documents(
    document_paths: list[Path],
    dataset_root: Path,
    service: OpenAIService,
    chunk_size: int = 1000,
    overlap: int = 120,
    embedding_batch_size: int = 100,
) -> tuple[InMemoryVectorStore, list[Chunk]]:
    store = InMemoryVectorStore()
    all_chunks: list[Chunk] = []

    for path in document_paths:
        source_name = str(path.relative_to(dataset_root)).replace("/", "-")
        text = load_document(path)
        chunks = recursive_character_chunking(
            text=text,
            source=source_name,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        if not chunks:
            continue
        embeddings = service.get_embeddings_batch(
            texts=[c.text for c in chunks],
            batch_size=embedding_batch_size,
            log_progress=True,
        )
        store.add([EmbeddedChunk(chunk=chunk, embedding=embedding) for chunk, embedding in zip(chunks, embeddings)])
        all_chunks.extend(chunks)

    return store, all_chunks


def answer_question(
    store: InMemoryVectorStore,
    question: str,
    service: OpenAIService,
    top_k: int = 3,
) -> tuple[str, list[EmbeddedChunk]]:
    answer, retrieved, _ = rag_query(
        store=store,
        question=question,
        service=service,
        top_k=top_k,
    )
    return answer, retrieved


def retrieve_top_k_chunks(
    store: InMemoryVectorStore,
    query: str,
    service: OpenAIService,
    top_k: int = 3,
) -> list[tuple[EmbeddedChunk, float]]:
    """
    Vector search step:
    1) Embed query
    2) Compute cosine similarity vs all chunk embeddings
    3) Return top-k chunks with similarity scores
    """
    query_embedding = service.embed_texts([query])[0]
    return store.search_with_scores(query_embedding=query_embedding, top_k=top_k)


def format_context_for_llm(retrieved_with_scores: list[tuple[EmbeddedChunk, float]]) -> list[str]:
    """Format retrieved chunks with source metadata for grounding."""
    context_blocks: list[str] = []
    for idx, (item, score) in enumerate(retrieved_with_scores, start=1):
        context_blocks.append(
            (
                f"[Context {idx}] source={item.chunk.source} chunk_id={item.chunk.id} "
                f"similarity={score:.4f}\n{item.chunk.text}"
            )
        )
    return context_blocks


def rag_query(
    store: InMemoryVectorStore,
    question: str,
    service: OpenAIService,
    top_k: int = 3,
) -> tuple[str, list[EmbeddedChunk], list[tuple[EmbeddedChunk, float]]]:
    """
    Complete RAG step:
    retrieval + context formatting + answer generation.
    """
    retrieved_with_scores = retrieve_top_k_chunks(
        store=store,
        query=question,
        service=service,
        top_k=top_k,
    )
    retrieved = [item for item, _ in retrieved_with_scores]
    context_chunks = format_context_for_llm(retrieved_with_scores)
    answer = service.answer_with_context(question=question, context_chunks=context_chunks)
    return answer, retrieved, retrieved_with_scores
