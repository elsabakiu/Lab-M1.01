"""Configuration helpers for the lab."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    pinecone_api_key: str
    cohere_api_key: str
    pinecone_index_name: str
    pinecone_namespace: str
    pinecone_cloud: str
    pinecone_region: str
    embedding_dimension: int
    embedding_model: str
    chat_model: str
    cohere_rerank_model: str = "rerank-v3.5"
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 8
    rerank_top_n: int = 4


def load_settings() -> Settings:
    # Load env vars from both:
    # 1) this project folder (.env)
    # 2) parent "Weekly Assignments" folder (.env)
    # The second load uses override=False (default), so local/project values stay
    # if already set, and parent values fill in missing keys.
    project_root = Path(__file__).resolve().parents[2]
    weekly_assignments_root = Path(__file__).resolve().parents[5]
    load_dotenv(project_root / ".env")
    load_dotenv(weekly_assignments_root / ".env")

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    pinecone_api_key = os.getenv("PINECONE_API_KEY", "").strip()
    cohere_api_key = os.getenv("COHERE_API_KEY", "").strip()
    if not openai_api_key:
        raise ValueError("Missing OPENAI_API_KEY. Add it to .env or your environment.")
    if not pinecone_api_key:
        raise ValueError("Missing PINECONE_API_KEY. Add it to .env or your environment.")
    return Settings(
        openai_api_key=openai_api_key,
        pinecone_api_key=pinecone_api_key,
        cohere_api_key=cohere_api_key,
        pinecone_index_name=os.getenv("PINECONE_INDEX_NAME", "w3d4-rag-rerank-lab"),
        pinecone_namespace=os.getenv("PINECONE_NAMESPACE", "default"),
        pinecone_cloud=os.getenv("PINECONE_CLOUD", "aws"),
        pinecone_region=os.getenv("PINECONE_REGION", "us-east-1"),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        cohere_rerank_model=os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5"),
    )
