"""Starter retrieval evaluation metrics."""

from __future__ import annotations


def precision_at_k(relevant_flags: list[bool], k: int) -> float:
    if k <= 0:
        return 0.0
    window = relevant_flags[:k]
    if not window:
        return 0.0
    return sum(window) / len(window)


def recall_at_k(relevant_flags: list[bool], total_relevant: int, k: int) -> float:
    if total_relevant <= 0:
        return 0.0
    return sum(relevant_flags[:k]) / total_relevant

