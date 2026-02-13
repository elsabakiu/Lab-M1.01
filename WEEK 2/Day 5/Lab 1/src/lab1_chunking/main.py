from pathlib import Path

from lab1_chunking.chunking import fixed_character_chunks, recursive_chunks, summarize_chunk_sizes
from lab1_chunking.io_utils import read_pdf_text, read_text_file


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw"

    transcript_path = raw_dir / "podcast_transcript.txt"
    pdf_path = raw_dir / "trustworthy_ai.pdf"

    if transcript_path.exists():
        transcript_text = read_text_file(transcript_path)
        fixed = fixed_character_chunks(transcript_text)
        rec = recursive_chunks(transcript_text)
        print("Transcript fixed:", summarize_chunk_sizes(fixed))
        print("Transcript recursive:", summarize_chunk_sizes(rec))
    else:
        print(f"Missing file: {transcript_path}")

    if pdf_path.exists():
        pdf_text = read_pdf_text(pdf_path)
        fixed = fixed_character_chunks(pdf_text)
        rec = recursive_chunks(pdf_text)
        print("PDF fixed:", summarize_chunk_sizes(fixed))
        print("PDF recursive:", summarize_chunk_sizes(rec))
    else:
        print(f"Missing file: {pdf_path}")


if __name__ == "__main__":
    main()
