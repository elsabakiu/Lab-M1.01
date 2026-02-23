"""Input loading and lightweight metadata assignment."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_pdf_file(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def load_documents(raw_dir: Path) -> list[dict[str, str]]:
    """Load documents from a directory with simple source/category metadata."""
    docs: list[dict[str, str]] = []
    for path in sorted(raw_dir.glob("*")):
        if path.suffix.lower() == ".txt":
            text = read_text_file(path)
        elif path.suffix.lower() == ".pdf":
            text = read_pdf_file(path)
        else:
            continue

        filename = path.name.lower()
        category = "eu_ai_act" if "ai_act" in filename or "eu" in filename else "podcast"
        docs.append(
            {
                "source": path.name,
                "category": category,
                "text": text.strip(),
            }
        )
    return docs

