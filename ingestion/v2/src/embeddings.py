"""Embedding generation and node construction."""
import json
import os
import re
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import MAX_WORKERS
from .utils import sha
from .ollama_client import OllamaClient


def doctrine_to_nodes(doctrine: Dict[str, Any], prefix: str) -> List[Dict[str, Any]]:
    """
    Convert doctrine dict to atomic node structures.
    
    Each principle, rule, warning, and claim becomes a searchable node.
    
    Args:
        doctrine: Doctrine dict from extraction
        prefix: Book prefix for node IDs (e.g., "BOOK_NAME")
        
    Returns:
        List of node dicts with node_id, type, text, metadata
    """
    nodes: List[Dict[str, Any]] = []
    idx = doctrine["chapter_index"]
    short_book = prefix.replace("\n", "").upper()

    counters = {"principle": 0, "rule": 0, "warning": 0, "claim": 0}

    # principles
    for p in doctrine.get("principles", []):
        pid = p.get("id") if isinstance(p, dict) else None
        counters["principle"] += 1
        seq = counters["principle"]
        id_part = pid if pid else f"P{seq:03d}"
        node_id = f"{short_book}-C{idx:02d}-P-{id_part}"
        nodes.append({
            "node_id": node_id,
            "type": "principle",
            "text": p.get("statement") if isinstance(p, dict) else p,
            "metadata": {
                "chapter": idx,
                "abstracted_from": p.get("abstracted_from") if isinstance(p, dict) else None,
            },
        })

    # rules
    for r in doctrine.get("rules", []):
        counters["rule"] += 1
        seq = counters["rule"]
        node_id = f"{short_book}-C{idx:02d}-R-{seq:03d}"
        cond = r.get("condition") if isinstance(r, dict) else ""
        act = r.get("action") if isinstance(r, dict) else r
        text = f"IF {cond} THEN {act}"
        nodes.append({
            "node_id": node_id,
            "type": "rule",
            "text": text,
            "metadata": {"chapter": idx},
        })

    # warnings
    for w in doctrine.get("warnings", []):
        counters["warning"] += 1
        seq = counters["warning"]
        node_id = f"{short_book}-C{idx:02d}-W-{seq:03d}"
        sit = w.get("situation") if isinstance(w, dict) else ""
        risk = w.get("risk") if isinstance(w, dict) else ""
        text = f"SITUATION: {sit}. RISK: {risk}"
        nodes.append({
            "node_id": node_id,
            "type": "warning",
            "text": text,
            "metadata": {"chapter": idx},
        })

    # claims
    for c in doctrine.get("claims", []):
        counters["claim"] += 1
        seq = counters["claim"]
        node_id = f"{short_book}-C{idx:02d}-L-{seq:03d}"
        claim_text = c.get("claim") if isinstance(c, dict) else c
        text = f"CLAIM: {claim_text}"
        nodes.append({
            "node_id": node_id,
            "type": "claim",
            "text": text,
            "metadata": {
                "chapter": idx,
                "confidence": c.get("confidence") if isinstance(c, dict) else None,
            },
        })

    return nodes


def normalize_doctrine(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize doctrine dict to ensure consistent structure.
    
    Converts string items to dicts for consistency.
    
    Args:
        d: Doctrine dict
        
    Returns:
        Normalized doctrine dict
    """
    out = dict(d)

    # normalize principles
    p_out = []
    for p in out.get("principles", []) or []:
        if isinstance(p, str):
            p_out.append({"id": sha(p), "statement": p, "abstracted_from": None})
        elif isinstance(p, dict):
            p_out.append(p)
    out["principles"] = p_out

    # normalize rules
    r_out = []
    for r in out.get("rules", []) or []:
        if isinstance(r, str):
            # try to parse IF/THEN
            parts = re.split(r"\bTHEN\b", r, flags=re.IGNORECASE)
            if len(parts) == 2:
                cond = parts[0].strip()
                act = parts[1].strip()
            else:
                cond = ""
                act = r
            r_out.append({"condition": cond, "action": act})
        elif isinstance(r, dict):
            r_out.append(r)
    out["rules"] = r_out

    # normalize claims
    c_out = []
    for c in out.get("claims", []) or []:
        if isinstance(c, str):
            c_out.append({"claim": c, "confidence": None})
        elif isinstance(c, dict):
            c_out.append(c)
    out["claims"] = c_out

    # normalize warnings
    w_out = []
    for w in out.get("warnings", []) or []:
        if isinstance(w, str):
            w_out.append({"situation": w, "risk": None})
        elif isinstance(w, dict):
            w_out.append(w)
    out["warnings"] = w_out

    return out


def embed_nodes(
    nodes: List[Dict[str, Any]],
    client: OllamaClient,
    progress_cb=None,
) -> List[Dict[str, Any]]:
    """
    Generate embeddings for doctrine nodes.
    
    Phase 3: Converts nodes to vector embeddings using LLM client.
    
    Args:
        nodes: List of node dicts
        client: OllamaClient instance for embedding
        progress_cb: Optional progress callback
        
    Returns:
        List of embedding dicts with vectors
    """
    embeddings = []
    total_nodes = len(nodes)
    
    if total_nodes == 0:
        return embeddings

    completed = 0
    if progress_cb:
        try:
            progress_cb(phase="phase_3", message="Embedding nodes", current=0, total=total_nodes)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        future_to_node = {ex.submit(client.embed, n.get("text", "")): n for n in nodes}
        
        for fut in as_completed(future_to_node):
            n = future_to_node[fut]
            try:
                vec = fut.result()
            except Exception:
                vec = None

            if vec:
                embeddings.append({
                    "embedding_id": f"emb-{n['node_id']}",
                    "node_id": n["node_id"],
                    "node_type": n["type"],
                    "text": n.get("text"),
                    "vector": vec,
                    "metadata": n.get("metadata", {}),
                })

            completed += 1
            if progress_cb:
                try:
                    progress_cb(phase="phase_3", message="Embedding nodes", current=completed, total=total_nodes)
                except Exception:
                    pass

    return embeddings