"""Utility helpers for v2 ingestion."""
from __future__ import annotations

import hashlib
import json
from typing import List, Any


def sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()[:16]


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def dedupe_list(items: List[Any]) -> List[Any]:
    """Deduplicate a list of dictionaries or strings while preserving order."""
    if not items:
        return []
    seen = set()
    out = []
    for item in items:
        if isinstance(item, dict):
            key = json.dumps(item, sort_keys=True)
        else:
            key = str(item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def infer_domains_from_text(text: str) -> List[str]:
    """Infer doctrine domains from text keywords if none provided by LLM."""
    from .config import ALLOWED_DOMAINS
    if not text:
        return ["strategy"]
    lower = text.lower()
    found = [d for d in ALLOWED_DOMAINS if d in lower]
    return found if found else ["strategy"]
