from lab2_rag_openai.chunking import simple_character_chunking


def test_simple_character_chunking_multiple_chunks() -> None:
    text = "abc " * 1000
    chunks = simple_character_chunking(text=text, source="test", chunk_size=200, overlap=20)
    assert len(chunks) > 1
    assert all(c.text for c in chunks)
