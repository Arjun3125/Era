"""Embedding helpers for v2 ingestion pipeline (compat stub)."""
from __future__ import annotations

from typing import Dict, Any, List


def normalize_doctrine(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure doctrine keys exist with list defaults."""
    if doc is None:
        doc = {}
    normalized = dict(doc)
    for key in ("principles", "rules", "claims", "warnings", "domains"):
        value = normalized.get(key)
        if value is None:
            normalized[key] = []
        elif not isinstance(value, list):
            normalized[key] = [value]
    return normalized


def doctrine_to_nodes(doc: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
    """Convert doctrine fields to embeddable nodes."""
    nodes: List[Dict[str, Any]] = []
    base_id = prefix or "DOC"
    for field in ("principles", "rules", "claims", "warnings"):
        items = doc.get(field, []) or []
        for idx, item in enumerate(items, start=1):
            nodes.append(
                {
                    "id": f"{base_id}_{field}_{idx}",
                    "content": str(item),
                    "field": field,
                }
            )
    return nodes


def embed_nodes(nodes: List[Dict[str, Any]], client=None, progress_cb=None) -> List[Dict[str, Any]]:
    """Return zero embeddings for nodes (stub)."""
    embeddings = []
    for idx, node in enumerate(nodes, start=1):
        if progress_cb:
            try:
                progress_cb(stage="embedding", current=idx, total=len(nodes))
            except Exception:
                pass
        embeddings.append(
            {
                "id": node.get("id"),
                "embedding": [0.0] * 8,
                "content": node.get("content", ""),
                "field": node.get("field", ""),
            }
        )
    return embeddings
