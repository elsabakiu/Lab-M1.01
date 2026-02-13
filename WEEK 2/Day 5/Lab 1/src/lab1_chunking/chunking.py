from dataclasses import dataclass
from statistics import mean

from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter


@dataclass
class ChunkStats:
    total_chunks: int
    min_size: int
    max_size: int
    avg_size: float


def fixed_character_chunks(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[str]:
    splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(text)


def recursive_chunks(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_text(text)


def summarize_chunk_sizes(chunks: list[str]) -> ChunkStats:
    if not chunks:
        return ChunkStats(total_chunks=0, min_size=0, max_size=0, avg_size=0.0)

    sizes = [len(c) for c in chunks]
    return ChunkStats(
        total_chunks=len(chunks),
        min_size=min(sizes),
        max_size=max(sizes),
        avg_size=mean(sizes),
    )
