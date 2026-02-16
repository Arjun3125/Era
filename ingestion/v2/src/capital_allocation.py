"""Capital allocation layer (Phase 4-8) implementation.

Implements the pseudocode provided for scoring, decision gate, memory commit,
doctrine diff, reinforcement, and retrieval optimization.

This module uses `memory_db.MemoryDB` as a backend. If Postgres isn't
configured the MemoryDB will fall back to a file-backed stub.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import math
import os
import json

try:
    import numpy as np
except Exception:
    np = None

# support both package-relative and top-level import
try:
    from .memory_db import MemoryDB
except Exception:
    from memory_db import MemoryDB

# vector DB (combined + per-domain) integration
try:
    from .vector_db import VectorDBStub, validate_domain
except Exception:
    from vector_db import VectorDBStub, validate_domain


DOCTRINE_THRESHOLD = 0.75


@dataclass
class ScoreBundle:
    relevance: float
    novelty: float
    emotional_weight: float
    strategic_weight: float
    importance_score: float


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    if np is not None:
        a_arr = np.array(a, dtype=float)
        b_arr = np.array(b, dtype=float)
        denom = (np.linalg.norm(a_arr) * np.linalg.norm(b_arr))
        return float((a_arr @ b_arr) / denom) if denom > 0 else 0.0
    # pure python fallback
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def weighted_sum(mapping: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
    if weights is None:
        weights = {"relevance": 0.4, "novelty": 0.2, "emotional": 0.2, "strategic": 0.2}
    total = 0.0
    for k, v in mapping.items():
        w = weights.get(k, 0.0)
        total += w * v
    return float(total)


def score_event(event: Dict[str, Any], memory_db: MemoryDB, mission_vector: Optional[List[float]] = None) -> ScoreBundle:
    """Score a single event (node/embedding).

    event is expected to contain `embedding` (list of floats) and `raw_text`.
    """
    emb = event.get("embedding") or event.get("vector") or []
    # relevance
    if mission_vector:
        relevance = max(0.0, _cosine(emb, mission_vector))
    else:
        relevance = 0.0

    # novelty: 1 - max similarity to recent memory window
    recent = memory_db.get_recent_embeddings(window=50)
    max_sim = 0.0
    for r in recent:
        try:
            sim = _cosine(emb, r)
            if sim > max_sim:
                max_sim = sim
        except Exception:
            continue
    novelty = 1.0 - max_sim

    # emotional weight (simple heuristic: presence of exclamation or emotion tokens)
    text = (event.get("raw_text") or "")
    emotional_weight = 0.0
    if "!" in text:
        emotional_weight += 0.2
    # basic sentiment proxy
    emotional_weight += min(0.8, abs(sum(1 for t in ["fear","anger","joy","sad"] if t in text.lower()) * 0.2))

    # strategic weight: placeholder classifier (presence of strategic keywords)
    strategic_keywords = ["strategy", "plan", "goal", "objective", "mission", "risk", "execute"]
    strategic_weight = 0.0
    lowered = text.lower()
    for kw in strategic_keywords:
        if kw in lowered:
            strategic_weight += 0.15
    strategic_weight = min(1.0, strategic_weight)

    importance_score = weighted_sum({
        "relevance": relevance,
        "novelty": novelty,
        "emotional": emotional_weight,
        "strategic": strategic_weight
    })

    return ScoreBundle(
        relevance=relevance,
        novelty=novelty,
        emotional_weight=emotional_weight,
        strategic_weight=strategic_weight,
        importance_score=importance_score,
    )


def decision_gate(scores: ScoreBundle) -> str:
    if scores.importance_score < 0.30:
        return "DROP"
    if scores.importance_score < 0.55:
        return "SESSION_MEMORY"
    if scores.importance_score < 0.75:
        return "PROJECT_MEMORY"
    return "GLOBAL_MEMORY"


def commit_memory(event: Dict[str, Any], scores: ScoreBundle, route: str, memory_db: MemoryDB) -> str:
    content = event.get("raw_text") or event.get("text") or ""
    domain = event.get("domain") or "general"
    mem_id = memory_db.insert_memory(content, route, {
        "importance_score": scores.importance_score,
        "novelty": scores.novelty,
        "strategic_weight": scores.strategic_weight,
        "emotional_weight": scores.emotional_weight
    }, domain)
    # attach embedding if present
    emb = event.get("embedding") or event.get("vector")
    if emb:
        memory_db.insert_embedding(mem_id, emb)
    # attach entities
    entities = event.get("entities") or []
    # memory_db.update_graph_edges equivalent: just store entities as weights
    for e in entities:
        # entities are represented by string ids in stub mode
        pass
    return mem_id


def doctrine_diff(memory_id: str, memory_db: MemoryDB):
    # fetch embedding from stub
    data = memory_db._read()
    emb = data.get("embeddings", {}).get(memory_id)
    if not emb:
        return
    candidate_beliefs = memory_db.retrieve_related_beliefs(emb)
    contradictions = []
    # naive textual contradiction detection: opposite words
    for b in candidate_beliefs:
        if "not" in (b.get("belief_text") or ""):
            contradictions.append(b)
    if contradictions:
        # create patches for first conflicting belief
        for cb in contradictions:
            memory_db.create_doctrine_patch(memory_id, cb.get("id"))


def reinforce_feedback(memory_id: str, scores: ScoreBundle, memory_db: MemoryDB):
    # adjust attention priors and entities
    # domain lookup
    data = memory_db._read()
    mem = data.get("memories", {}).get(memory_id, {})
    domain = mem.get("domain", "general")
    memory_db.adjust_attention_priors(domain, delta=scores.importance_score * 0.1)
    # entities: stub - no-op
    memory_db.adjust_entity_weights([], delta=scores.importance_score * 0.05)


def optimize_retrieval_indices(memory_id: str, memory_db: MemoryDB):
    memory_db.update_topk_cache(memory_id)
    memory_db.recompute_cluster_centroids()
    memory_db.update_memory_salience(memory_id)


def ingest_post_phase3(event: Dict[str, Any]):
    """Master orchestrator for post-Phase3 processing.

    `event` should contain at minimum:
      - storage: path to rag_storage book folder
      - book_id
      - optionally mission_vector
    """
    storage = event.get("storage")
    book_id = event.get("book_id")
    mission_vector = event.get("mission_vector")

    db = MemoryDB(storage_root=os.path.join(os.getcwd(), "data"))

    # vector DB stub for local retrieval; domain enforcement via validate_domain
    vdb = VectorDBStub(storage_root=os.path.join(os.getcwd(), "data"))

    # load embeddings saved in the pipeline
    emb_path = os.path.join(storage, "03_embeddings.json")
    embeddings = []
    
    try:
        if not os.path.exists(emb_path):
            # File doesn't exist - async pipeline may have already processed
            return []
            
        with open(emb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle two formats:
        # 1. New format (async pipeline): {"pipeline_metrics": {...}}
        # 2. Old format (fallback): [list of embedding dicts]
        if isinstance(data, dict):
            if "pipeline_metrics" in data:
                # New format - embeddings are in ministers/ directory from async pipeline
                # Post-phase3 processing already handled by AsyncIngestionPipeline
                return []
            else:
                # Dict but no pipeline_metrics - treat as empty
                embeddings = []
        elif isinstance(data, list):
            # Old format - list of embeddings
            embeddings = data
        else:
            # Unexpected format
            embeddings = []
    except Exception as e:
        # If we can't load embeddings, silently continue
        return []

    created_ids = []
    for ev in embeddings:
        # Validate ev is a dict before processing
        if not isinstance(ev, dict):
            continue
            
        try:
            # each ev is expected to be a node dict with embedding + raw_text
            scores = score_event(ev, db, mission_vector=mission_vector)
            route = decision_gate(scores)
            if route == "DROP":
                continue
            mem_id = commit_memory(ev, scores, route, db)
            # index into vector DB (combined + per-domain) when possible
            emb = ev.get("embedding") or ev.get("vector")
            domain = ev.get("domain")
            try:
                if emb and domain:
                    # only insert if domain is valid; enforce VALID_DOMAINS
                    validate_domain(domain)
                    try:
                        vdb.insert_combined(domain=domain, category=ev.get("category", "unknown"), text=ev.get("raw_text") or ev.get("text", ""), embedding=emb, source_book=book_id, source_chapter=ev.get("chapter"), weight=1.0)
                    except Exception:
                        pass
                    try:
                        vdb.insert_domain(domain=domain, category=ev.get("category", "unknown"), text=ev.get("raw_text") or ev.get("text", ""), embedding=emb, weight=1.0)
                    except Exception:
                        pass
            except ValueError:
                # domain not in VALID_DOMAINS; skip domain-scoped indexing to enforce whitelist
                pass
            if scores.importance_score >= DOCTRINE_THRESHOLD:
                doctrine_diff(mem_id, db)
            reinforce_feedback(mem_id, scores, db)
            optimize_retrieval_indices(mem_id, db)
            created_ids.append(mem_id)
        except Exception:
            # Skip individual embedding processing errors
            continue

    return created_ids


__all__ = [
    "ingest_post_phase3",
    "score_event",
    "decision_gate",
    "commit_memory",
    "doctrine_diff",
    "reinforce_feedback",
    "optimize_retrieval_indices",
    "ScoreBundle",
]
