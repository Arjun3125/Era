"""Vector DB schema and helper functions for combined and per-domain embeddings.

Provides SQL schema strings for Postgres + pgvector and a file-backed stub
implementation for local testing and retrieval.
"""
import json
import os
import uuid
import threading
from typing import List, Dict, Any, Optional

COMBINED_SCHEMA = """
CREATE TABLE IF NOT EXISTS minister_embeddings (
    id UUID PRIMARY KEY,
    domain VARCHAR(50),
    category VARCHAR(50),
    text TEXT,
    embedding VECTOR(1536),
    source_book VARCHAR(255),
    source_chapter INT,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS minister_embeddings_idx ON minister_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 200);
"""

DOMAIN_SCHEMA = """
CREATE TABLE IF NOT EXISTS minister_domain_embeddings (
    id UUID PRIMARY KEY,
    domain VARCHAR(50),
    category VARCHAR(50),
    text TEXT,
    embedding VECTOR(1536),
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS minister_domain_embeddings_idx ON minister_domain_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
"""

VALID_DOMAINS = [
    "adaptation",
    "base",
    "conflict",
    "constraints",
    "data",
    "diplomacy",
    "discipline",
    "executor",
    "legitimacy",
    "optionality",
    "power",
    "psychology",
    "registry",
    "risk",
    "strategy",
    "technology",
    "timing",
    "truth",
    "key_constr",
]


class VectorDBStub:
    """File-backed stub for storing embeddings and performing naive searches."""

    def __init__(self, storage_root: str = "data"):
        self.storage_root = storage_root
        self.path = os.path.join(self.storage_root, "vector_db_stub.json")
        self._lock = threading.RLock()  # Recursive lock for concurrent access protection
        os.makedirs(self.storage_root, exist_ok=True)
        with self._lock:
            if not os.path.exists(self.path):
                with open(self.path, "w", encoding="utf-8") as f:
                    json.dump({"combined": {}, "domain": {}}, f, indent=2)

    def _read(self) -> Dict[str, Any]:
        with self._lock:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)

    def _write(self, data: Dict[str, Any]):
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def insert_combined(self, domain: str, category: str, text: str, embedding: List[float], source_book: Optional[str] = None, source_chapter: Optional[int] = None, weight: float = 1.0) -> str:
        assert domain in VALID_DOMAINS, f"Invalid domain: {domain}"
        data = self._read()
        eid = str(uuid.uuid4())
        data["combined"][eid] = {
            "id": eid,
            "domain": domain,
            "category": category,
            "text": text,
            "embedding": embedding,
            "source_book": source_book,
            "source_chapter": source_chapter,
            "weight": weight,
        }
        self._write(data)
        return eid

    def insert_combined_batch(self, records: List[Dict[str, Any]]):
        """Insert multiple combined records in a single read/write to reduce I/O."""
        data = self._read()
        for rec in records:
            eid = str(uuid.uuid4())
            data["combined"][eid] = {
                "id": eid,
                "domain": rec.get("domain"),
                "category": rec.get("category"),
                "text": rec.get("text"),
                "embedding": rec.get("embedding"),
                "source_book": rec.get("source_book"),
                "source_chapter": rec.get("source_chapter"),
                "weight": rec.get("weight", 1.0),
            }
        self._write(data)
        return True

    def insert_domain(self, domain: str, category: str, text: str, embedding: List[float], weight: float = 1.0) -> str:
        assert domain in VALID_DOMAINS, f"Invalid domain: {domain}"
        data = self._read()
        eid = str(uuid.uuid4())
        domain_map = data.setdefault("domain", {}).setdefault(domain, {})
        domain_map[eid] = {
            "id": eid,
            "domain": domain,
            "category": category,
            "text": text,
            "embedding": embedding,
            "weight": weight,
        }
        self._write(data)
        return eid

    def insert_domain_batch(self, domain: str, records: List[Dict[str, Any]]):
        """Insert multiple records for a domain in a single write."""
        data = self._read()
        domain_map = data.setdefault("domain", {}).setdefault(domain, {})
        for rec in records:
            eid = str(uuid.uuid4())
            domain_map[eid] = {
                "id": eid,
                "domain": domain,
                "category": rec.get("category"),
                "text": rec.get("text"),
                "embedding": rec.get("embedding"),
                "weight": rec.get("weight", 1.0),
            }
        self._write(data)
        return True

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        # simple dot / norms
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    def search_domain(self, domain: str, query_embedding: List[float], topk: int = 10) -> List[Dict[str, Any]]:
        assert domain in VALID_DOMAINS, f"Invalid domain: {domain}"
        data = self._read()
        items = list(data.get("domain", {}).get(domain, {}).values())
        scored = []
        for it in items:
            sim = self._cosine(query_embedding, it.get("embedding", []))
            scored.append((sim * (it.get("weight", 1.0) or 1.0), it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:topk]]

    def search_combined(self, query_embedding: List[float], topk: int = 10) -> List[Dict[str, Any]]:
        data = self._read()
        items = list(data.get("combined", {}).values())
        scored = []
        for it in items:
            sim = self._cosine(query_embedding, it.get("embedding", []))
            scored.append((sim * (it.get("weight", 1.0) or 1.0), it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:topk]]


def validate_domain(domain: str):
    if domain not in VALID_DOMAINS:
        raise ValueError(f"Domain '{domain}' is not in VALID_DOMAINS")


__all__ = ["COMBINED_SCHEMA", "DOMAIN_SCHEMA", "VectorDBStub", "VALID_DOMAINS", "validate_domain"]
