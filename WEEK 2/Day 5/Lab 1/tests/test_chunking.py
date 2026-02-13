from lab1_chunking.chunking import fixed_character_chunks, recursive_chunks, summarize_chunk_sizes


def test_chunking_produces_chunks() -> None:
    text = "Paragraph one. " * 120
    fixed = fixed_character_chunks(text, chunk_size=200, chunk_overlap=20)
    rec = recursive_chunks(text, chunk_size=200, chunk_overlap=20)

    assert len(fixed) > 1
    assert len(rec) > 1


def test_chunk_stats_non_empty() -> None:
    chunks = ["a" * 10, "b" * 20, "c" * 30]
    stats = summarize_chunk_sizes(chunks)

    assert stats.total_chunks == 3
    assert stats.min_size == 10
    assert stats.max_size == 30
    assert stats.avg_size == 20
