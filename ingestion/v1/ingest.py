"""Legacy ingestion utilities stub for tests."""

from __future__ import annotations

from pathlib import Path
from typing import List

PHASE1_SYSTEM_PROMPT = "You are a chapter segmentation helper."


def extract_pdf_pages(pdf_path: str, **_kwargs) -> List[str]:
    """Return dummy page list for a PDF path."""
    path = Path(pdf_path)
    if not path.exists():
        return []
    return [path.read_text(encoding="utf-8", errors="ignore")]


def split_chapters_with_ollama_streaming(pages: List[str], client=None, book_title: str = "", storage: str = ""):
    """Return a single dummy chapter split."""
    return [
        {
            "chapter_index": 1,
            "chapter_title": f"{book_title or 'Book'} Chapter 1",
            "text": pages[0][:2000] if pages else "",
        }
    ]
