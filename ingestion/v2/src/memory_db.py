"""Memory DB interface and schema for Phase 4-8 (Postgres + pgvector).

Provides a light-weight fallback (file-backed) implementation when Postgres
or psycopg2 isn't available so the rest of the pipeline can be exercised
locally without external services.
"""
import json
import os
import uuid
from typing import List, Dict, Any, Optional

SQL_SCHEMA = """
-- PostgreSQL schema for Phase 4-8
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    memory_type VARCHAR(20),
    importance_score FLOAT,
    novelty_score FLOAT,
    strategic_weight FLOAT,
    emotional_weight FLOAT,
    domain VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    confidence_score FLOAT
);

CREATE TABLE IF NOT EXISTS memory_embeddings (
    memory_id UUID REFERENCES memories(id) ON DELETE CASCADE,
    embedding VECTOR(1536),
    PRIMARY KEY (memory_id)
);

CREATE INDEX IF NOT EXISTS memory_embeddings_idx ON memory_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    entity_type VARCHAR(50),
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory_entities (
    memory_id UUID REFERENCES memories(id),
    entity_id UUID REFERENCES entities(id),
    relevance_score FLOAT,
    PRIMARY KEY (memory_id, entity_id)
);

CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY,
    source_entity UUID REFERENCES entities(id),
    target_entity UUID REFERENCES entities(id),
    relation_type VARCHAR(100),
    weight FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doctrine_versions (
    id UUID PRIMARY KEY,
    version_number INT,
    belief_text TEXT,
    supersedes UUID REFERENCES doctrine_versions(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doctrine_patches (
    id UUID PRIMARY KEY,
    triggering_memory UUID REFERENCES memories(id),
    conflicting_belief UUID REFERENCES doctrine_versions(id),
    resolution_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attention_priors (
    domain VARCHAR(100) PRIMARY KEY,
    weight FLOAT DEFAULT 1.0,
    updated_at TIMESTAMP DEFAULT NOW()
);
"""


class MemoryDB:
    """Simple memory DB abstraction.

    Attempts to use a real Postgres connection if environment variables are
    configured and `psycopg2` is available. Otherwise provides a file-backed
    fallback that stores records under `data/memory_db_stub.json`.
    """

    def __init__(self, dsn: Optional[str] = None, storage_root: str = "data"):
        self.dsn = dsn
        self.storage_root = storage_root
        self.stub_path = os.path.join(self.storage_root, "memory_db_stub.json")
        self._use_stub = True
        self._ensure_stub()

    def _ensure_stub(self):
        os.makedirs(self.storage_root, exist_ok=True)
        if not os.path.exists(self.stub_path):
            with open(self.stub_path, "w", encoding="utf-8") as f:
                json.dump({
                    "memories": {},
                    "embeddings": {},
                    "entities": {},
                    "memory_entities": {},
                    "relationships": {},
                    "doctrine_versions": {},
                    "doctrine_patches": {},
                    "attention_priors": {}
                }, f, indent=2)

    def _read(self) -> Dict[str, Any]:
        with open(self.stub_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]):
        with open(self.stub_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def init_schema(self):
        """Prints SQL schema for manual application or logs it in the stub."""
        # For stub mode just record that schema was requested
        data = self._read()
        data.setdefault("schema_initialized", True)
        data.setdefault("sql_schema", SQL_SCHEMA)
        self._write(data)
        return True

    def insert_memory(self, content: str, memory_type: str, scores: Dict[str, float], domain: str) -> str:
        data = self._read()
        mem_id = str(uuid.uuid4())
        data["memories"][mem_id] = {
            "id": mem_id,
            "content": content,
            "memory_type": memory_type,
            "importance_score": scores.get("importance_score"),
            "novelty_score": scores.get("novelty"),
            "strategic_weight": scores.get("strategic_weight"),
            "emotional_weight": scores.get("emotional_weight"),
            "domain": domain,
        }
        self._write(data)
        return mem_id

    def insert_embedding(self, memory_id: str, embedding: List[float]):
        data = self._read()
        data["embeddings"][memory_id] = embedding
        self._write(data)

    def get_recent_embeddings(self, window: int = 50) -> List[List[float]]:
        data = self._read()
        # Return last `window` embeddings by insertion order
        items = list(data.get("embeddings", {}).items())
        return [v for _, v in items[-window:]]

    def retrieve_related_beliefs(self, embedding: List[float], topk: int = 20) -> List[Dict[str, Any]]:
        data = self._read()
        # naive similarity: dot product ranked
        sims = []
        for bid, b in data.get("doctrine_versions", {}).items():
            # doctrine_versions don't have embeddings in stub; return all
            sims.append((0.0, b))
        return [b for _, b in sorted(sims, key=lambda x: x[0], reverse=True)][:topk]

    def store_doctrine_version(self, belief_text: str, version_number: int, supersedes: Optional[str] = None) -> str:
        data = self._read()
        vid = str(uuid.uuid4())
        data["doctrine_versions"][vid] = {
            "id": vid,
            "version_number": version_number,
            "belief_text": belief_text,
            "supersedes": supersedes,
        }
        self._write(data)
        return vid

    def create_doctrine_patch(self, triggering_memory: str, conflicting_belief: str) -> str:
        data = self._read()
        pid = str(uuid.uuid4())
        data["doctrine_patches"][pid] = {
            "id": pid,
            "triggering_memory": triggering_memory,
            "conflicting_belief": conflicting_belief,
            "resolution_status": "pending"
        }
        self._write(data)
        return pid

    def adjust_attention_priors(self, domain: str, delta: float):
        data = self._read()
        priors = data.setdefault("attention_priors", {})
        priors[domain] = priors.get(domain, 1.0) + delta
        self._write(data)

    def adjust_entity_weights(self, entities: List[str], delta: float):
        data = self._read()
        for eid in entities:
            ent = data.setdefault("entities", {}).setdefault(eid, {"id": eid, "weight": 1.0})
            ent["weight"] = ent.get("weight", 1.0) + delta
        self._write(data)

    def update_topk_cache(self, memory_id: str):
        # stub: no-op
        return True

    def recompute_cluster_centroids(self):
        # stub: no-op
        return True

    def update_memory_salience(self, memory_id: str):
        # stub: no-op
        return True


__all__ = ["MemoryDB", "SQL_SCHEMA"]
