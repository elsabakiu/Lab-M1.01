import sys
from pathlib import Path

# Support direct script execution:
# python src/lab2_rag_openai/main.py
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from lab2_rag_openai.openai_client import OpenAIService
from lab2_rag_openai.pipeline import build_index_from_documents, discover_documents, rag_query


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    dataset_root = project_root / "data" / "raw" / "investment_research_assistant"

    if not dataset_root.exists():
        print(f"Missing dataset directory: {dataset_root}")
        return

    document_paths = discover_documents(dataset_root)
    if not document_paths:
        print(f"No documents found under {dataset_root}")
        return

    print("Setting up OpenAI API client...")
    try:
        service = OpenAIService()
    except ValueError as exc:
        print(f"OpenAI client setup failed: {exc}")
        print("Add OPENAI_API_KEY to Lab 2 .env and rerun.")
        return

    embedding_batch_size = 100
    print(f"Embedding model: {service.embedding_model}")
    print("Building index with recursive character chunking...")
    store, chunks = build_index_from_documents(
        document_paths=document_paths,
        dataset_root=dataset_root,
        service=service,
        chunk_size=1000,
        overlap=120,
        embedding_batch_size=embedding_batch_size,
    )
    print(f"Indexed chunks: {len(chunks)}")
    print(f"Indexed documents: {len(document_paths)}")

    questions = [
        "Which company appears to have the strongest near-term growth outlook and why?",
        "What are the biggest product or execution risks called out by management across these companies?",
        "If you were prioritizing one AI-related investment thesis from these documents, what is it and what evidence supports it?",
    ]

    for idx, question in enumerate(questions, start=1):
        answer, _retrieved, retrieved_with_scores = rag_query(
            store=store,
            question=question,
            service=service,
            top_k=4,
        )

        print(f"\n\n=== Question {idx} ===")
        print(question)
        print("\nTop retrieved chunks:")
        for item, score in retrieved_with_scores:
            print(f"- {item.chunk.id} | source={item.chunk.source} | similarity={score:.4f}")

        print("\nAnswer:")
        print(answer)


if __name__ == "__main__":
    main()
