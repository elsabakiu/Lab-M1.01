from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    id: str
    text: str
    source: str


DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def simple_character_chunking(text: str, source: str, chunk_size: int = 1000, overlap: int = 100) -> list[Chunk]:
    """Simple baseline chunker for Lab 2; replace with more advanced chunking as needed."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(id=f"{source}-{index}", text=chunk_text, source=source))
            index += 1
        if end == len(text):
            break
        start = end - overlap
    return chunks


def recursive_character_chunking(
    text: str,
    source: str,
    chunk_size: int = 1000,
    overlap: int = 120,
    separators: list[str] | None = None,
) -> list[Chunk]:
    """Recommended chunking strategy for mixed filing/transcript content."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=separators or DEFAULT_SEPARATORS,
        length_function=len,
    )
    parts = splitter.split_text(text)
    return [
        Chunk(id=f"{source}-{idx}", text=part.strip(), source=source)
        for idx, part in enumerate(parts)
        if part.strip()
    ]
