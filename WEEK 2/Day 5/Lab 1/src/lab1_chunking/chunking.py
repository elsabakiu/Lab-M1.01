"""Chunking primitives used by the Lab 1 analysis pipeline.

This module is intentionally small:
- one function per chunking strategy
- one shared stats helper
- lightweight semantic fallback when sentence-transformers is unavailable
"""

import re
from collections import Counter
from dataclasses import dataclass
from math import sqrt
from statistics import mean

from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter, TokenTextSplitter


@dataclass
class ChunkStats:
    """Simple summary of chunk lengths for one run."""

    total_chunks: int
    min_size: int
    max_size: int
    avg_size: float


def estimate_token_count(text: str) -> int:
    """Lightweight token approximation used for recursive token-aware splitting."""
    return len(text.split())


def fixed_character_chunks(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[str]:
    """Fixed-size chunking with a single space separator."""
    splitter = CharacterTextSplitter(
        separator=" ",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(text)


def recursive_token_chunks(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    separators: list[str] | None = None,
) -> list[str]:
    """Recursive splitting using separator fallbacks and approximate token sizing."""
    splitter = RecursiveCharacterTextSplitter(
        separators=separators or ["\n\n", "\n", ". ", " ", ""],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=estimate_token_count,
    )
    return splitter.split_text(text)


def token_based_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """TokenTextSplitter-based chunking aligned with model token windows."""
    splitter = TokenTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_text(text)


def split_sentences(text: str) -> list[str]:
    """Split into sentences while keeping punctuation attached."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _tokenize_for_similarity(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def _cosine_similarity_from_counters(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a.keys()) | set(b.keys())
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    norm_a = sqrt(sum(v * v for v in a.values()))
    norm_b = sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _fallback_semantic_chunks(sentences: list[str], threshold: float) -> list[str]:
    """Fallback semantic splitter for offline environments."""
    vectors = [Counter(_tokenize_for_similarity(sentence)) for sentence in sentences]
    chunks: list[str] = []
    current_chunk = [sentences[0]]

    for i in range(1, len(sentences)):
        similarity = _cosine_similarity_from_counters(vectors[i - 1], vectors[i])
        if similarity < threshold:
            chunks.append(" ".join(current_chunk).strip())
            current_chunk = [sentences[i]]
        else:
            current_chunk.append(sentences[i])

    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())
    return chunks


def semantic_chunks(text: str, threshold: float = 0.7) -> list[str]:
    """Semantic chunking using sentence-transformers, with local fallback."""
    sentences = split_sentences(text)
    if len(sentences) < 2:
        return [text.strip()] if text.strip() else []

    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        # Any import/runtime issue falls back to local similarity chunking.
        return _fallback_semantic_chunks(sentences=sentences, threshold=threshold)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(sentences, normalize_embeddings=True)

    chunks: list[str] = []
    current_chunk = [sentences[0]]

    for i in range(1, len(sentences)):
        similarity = float(embeddings[i - 1] @ embeddings[i])
        if similarity < threshold:
            chunks.append(" ".join(current_chunk).strip())
            current_chunk = [sentences[i]]
        else:
            current_chunk.append(sentences[i])

    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())

    return chunks


def summarize_chunk_sizes(chunks: list[str]) -> ChunkStats:
    """Compute chunk length summary metrics."""
    if not chunks:
        return ChunkStats(total_chunks=0, min_size=0, max_size=0, avg_size=0.0)

    sizes = [len(chunk) for chunk in chunks]
    return ChunkStats(
        total_chunks=len(chunks),
        min_size=min(sizes),
        max_size=max(sizes),
        avg_size=mean(sizes),
    )
