from dataclasses import dataclass

import numpy as np

from lab2_rag_openai.chunking import Chunk


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    embedding: list[float]


class InMemoryVectorStore:
    """Minimal in-memory store for learning before switching to Pinecone/FAISS/etc."""

    def __init__(self) -> None:
        self._items: list[EmbeddedChunk] = []

    def add(self, items: list[EmbeddedChunk]) -> None:
        self._items.extend(items)

    def search(self, query_embedding: list[float], top_k: int = 3) -> list[EmbeddedChunk]:
        return [item for item, _ in self.search_with_scores(query_embedding=query_embedding, top_k=top_k)]

    def search_with_scores(
        self, query_embedding: list[float], top_k: int = 3
    ) -> list[tuple[EmbeddedChunk, float]]:
        if not self._items:
            return []

        query = np.array(query_embedding, dtype=float)
        scored: list[tuple[float, EmbeddedChunk]] = []
        for item in self._items:
            emb = np.array(item.embedding, dtype=float)
            denom = np.linalg.norm(query) * np.linalg.norm(emb)
            similarity = float(np.dot(query, emb) / denom) if denom else 0.0
            scored.append((similarity, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [(item, score) for score, item in scored[:top_k]]
