from rag_relevance_rerank_lab.eval import precision_at_k, recall_at_k


def test_precision_at_k() -> None:
    flags = [True, False, True, True]
    assert precision_at_k(flags, 2) == 0.5


def test_recall_at_k() -> None:
    flags = [True, False, True, True]
    assert recall_at_k(flags, total_relevant=3, k=3) == 2 / 3

