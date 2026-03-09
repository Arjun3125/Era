#!/usr/bin/env python
"""
Build KIS 2.0 principle embedding index.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from evaluation.kis2_retrieval import ensure_default_principles_file, fetch_ollama_embedding


def main() -> int:
    parser = argparse.ArgumentParser(description="Build KIS2 principle embeddings index")
    parser.add_argument(
        "--principles",
        default="knowledge/principles.json",
        help="Principles catalog JSON",
    )
    parser.add_argument(
        "--output",
        default="knowledge/embeddings.npy",
        help="Output embeddings .npy path",
    )
    parser.add_argument(
        "--embed-model",
        default="nomic-embed-text:latest",
        help="Embedding model served by Ollama",
    )
    args = parser.parse_args()

    principles_path = Path(args.principles)
    ensure_default_principles_file(principles_path)
    rows = json.loads(principles_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Invalid principles file: {principles_path}")

    vectors = []
    for row in rows:
        text = str(row.get("text", "")).strip()
        if not text:
            continue
        vec = fetch_ollama_embedding(text, model=args.embed_model, timeout_sec=20.0)
        vectors.append([float(v) for v in vec])
    if not vectors:
        raise RuntimeError("No embeddings built from principles catalog.")

    matrix = np.asarray(vectors, dtype=np.float32)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, matrix)
    print(f"[KIS2] Saved embeddings: {out} shape={tuple(matrix.shape)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
