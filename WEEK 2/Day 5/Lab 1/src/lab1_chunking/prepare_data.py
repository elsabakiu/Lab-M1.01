import sys
from pathlib import Path

from openai import OpenAI

# Support direct script execution:
# python src/lab1_chunking/prepare_data.py
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from lab1_chunking.config import PROJECT_ROOT, require_env
from lab1_chunking.io_utils import read_pdf_text


RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

SOURCE_AUDIO_PATH = RAW_DIR / "The_Blueprint_For_Trustworthy_AI.m4a"
SOURCE_PDF_PATH = RAW_DIR / "ethics_guidelines_for_trustworthy_ai-fr_87FE7A3C-D03D-9305-81A653DDA84B5A60_60427.pdf"
TRANSCRIPT_OUT_PATH = PROCESSED_DIR / "podcast_transcript.txt"
PDF_TEXT_OUT_PATH = PROCESSED_DIR / "trustworthy_ai_extracted.txt"


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def get_openai_client() -> OpenAI:
    api_key = require_env("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def transcribe_audio(audio_path: Path, transcript_path: Path, model: str = "gpt-4o-mini-transcribe") -> None:
    client = get_openai_client()

    with audio_path.open("rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
        )

    transcript_text = result.text.strip()
    transcript_path.write_text(transcript_text + "\n", encoding="utf-8")


def save_pdf_extracted_text(pdf_path: Path, output_txt_path: Path) -> None:
    text = read_pdf_text(pdf_path)
    output_txt_path.write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()

    if not SOURCE_AUDIO_PATH.exists():
        raise FileNotFoundError(f"Audio file not found: {SOURCE_AUDIO_PATH}")
    if not SOURCE_PDF_PATH.exists():
        raise FileNotFoundError(f"PDF file not found: {SOURCE_PDF_PATH}")

    print(f"[1/4] Loading environment variables from: {PROJECT_ROOT / '.env'}")
    require_env("OPENAI_API_KEY")

    print(f"[2/4] Loading audio file: {SOURCE_AUDIO_PATH}")

    print(f"[3/4] Transcribing and saving transcript: {TRANSCRIPT_OUT_PATH}")
    transcribe_audio(
        audio_path=SOURCE_AUDIO_PATH,
        transcript_path=TRANSCRIPT_OUT_PATH,
        model="gpt-4o-mini-transcribe",
    )

    print(f"[4/4] Loading PDF file: {SOURCE_PDF_PATH}")
    save_pdf_extracted_text(pdf_path=SOURCE_PDF_PATH, output_txt_path=PDF_TEXT_OUT_PATH)

    print("Done.")
    print(f"- Transcript: {TRANSCRIPT_OUT_PATH}")
    print(f"- PDF file:   {SOURCE_PDF_PATH}")
    print(f"- PDF text:   {PDF_TEXT_OUT_PATH}")


if __name__ == "__main__":
    main()
