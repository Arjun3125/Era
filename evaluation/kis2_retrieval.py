"""
KIS 2.0 retrieval path (parallel to KIS 1.0).

Design goals:
- Opt-in only; never replaces KIS 1.0 by default.
- Deterministic embedding retrieval over a fixed principle catalog.
- Optional lightweight reranker loaded from JSON artifact.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import requests

try:
    import torch
    import torch.nn as nn
except Exception:  # pragma: no cover - optional dependency for reranker only
    torch = None
    nn = None


DEFAULT_PRINCIPLES: List[Dict[str, Any]] = [
    {
        "id": "reversibility",
        "text": "Prefer choices that can be reversed cheaply when uncertainty is high.",
        "domain": "optionality",
        "historical_success_rate": 0.5,
    },
    {
        "id": "downside_asymmetry",
        "text": "Protect against asymmetric downside before chasing upside.",
        "domain": "risk",
        "historical_success_rate": 0.5,
    },
    {
        "id": "feedback_loops",
        "text": "Assess second-order and feedback-loop effects before final commitment.",
        "domain": "systems",
        "historical_success_rate": 0.5,
    },
    {
        "id": "systemic_barriers",
        "text": "Account for structural constraints and institutional barriers to execution.",
        "domain": "systems",
        "historical_success_rate": 0.5,
    },
    {
        "id": "time_value",
        "text": "Evaluate the value of acting now versus waiting for better information.",
        "domain": "temporal",
        "historical_success_rate": 0.5,
    },
    {
        "id": "optionality",
        "text": "Preserve strategic optionality when the environment is unstable.",
        "domain": "optionality",
        "historical_success_rate": 0.5,
    },
    {
        "id": "information_value",
        "text": "Estimate what additional signal would materially change the decision.",
        "domain": "information",
        "historical_success_rate": 0.5,
    },
]

PRINCIPLE_CHECKS = {
    "reversibility": "- Evaluate reversibility implications before commitment.",
    "downside_asymmetry": "- Evaluate downside asymmetry and worst-case containment.",
    "systemic_barriers": "- Evaluate systemic barriers and structural constraints.",
    "feedback_loops": "- Evaluate feedback-loop and second-order consequences.",
    "time_value": "- Evaluate time-value impact of delaying vs acting now.",
    "optionality": "- Evaluate optionality preservation under uncertainty.",
    "information_value": "- Evaluate information value: what new signal changes the decision?",
}


def ensure_default_principles_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: List[Dict[str, Any]] = []
    for item in DEFAULT_PRINCIPLES:
        rec = dict(item)
        rec["embedding"] = []
        payload.append(rec)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def _cosine_sim_matrix(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    qn = np.linalg.norm(query) + 1e-12
    mn = np.linalg.norm(matrix, axis=1) + 1e-12
    sims = (matrix @ query) / (mn * qn)
    return np.clip(sims, -1.0, 1.0)


def _category_code(category: str) -> float:
    mapping = {
        "strategic": 0.15,
        "irreversible": 0.30,
        "long_horizon": 0.45,
        "adversarial": 0.60,
        "out_of_distribution": 0.75,
        "emotional": 0.90,
    }
    return float(mapping.get(str(category or "").strip().lower(), 0.0))


if nn is not None:
    class _RerankerMLP(nn.Module):
        def __init__(self, in_dim: int, hidden_dim: int = 16):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, 1),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x).squeeze(-1)
else:  # pragma: no cover - reranker unavailable without torch
    class _RerankerMLP:  # type: ignore[override]
        pass


@dataclass
class KIS2Config:
    enabled: bool
    principles_path: str
    embeddings_path: str
    embed_model: str
    top_k: int
    reranker_json: Optional[str] = None
    auto_build_embeddings: bool = True


class KIS2Retrieval:
    """
    Embedding-based principle retrieval with optional reranking.
    """

    def __init__(self, config: KIS2Config):
        self.config = config
        self.principles_path = Path(config.principles_path)
        self.embeddings_path = Path(config.embeddings_path)
        ensure_default_principles_file(self.principles_path)
        self.principles = self._load_principles(self.principles_path)
        self.embeddings = self._load_or_build_embeddings()
        self._reranker: Optional[_RerankerMLP] = None
        self._reranker_features: List[str] = []
        if config.reranker_json:
            self._load_reranker(Path(config.reranker_json))

    @staticmethod
    def _load_principles(path: Path) -> List[Dict[str, Any]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data:
            raise ValueError(f"Invalid principles catalog: {path}")
        cleaned: List[Dict[str, Any]] = []
        for item in data:
            pid = str(item.get("id", "")).strip()
            text = str(item.get("text", "")).strip()
            domain = str(item.get("domain", "")).strip().lower()
            if not pid or not text:
                continue
            cleaned.append(
                {
                    "id": pid,
                    "text": text,
                    "domain": domain or "general",
                    "historical_success_rate": float(item.get("historical_success_rate", 0.5)),
                }
            )
        if not cleaned:
            raise ValueError("Principles catalog has no valid rows.")
        return cleaned

    def _load_or_build_embeddings(self) -> np.ndarray:
        if self.embeddings_path.exists():
            arr = np.load(self.embeddings_path)
            if arr.ndim != 2:
                raise ValueError(f"Expected 2D embeddings matrix at {self.embeddings_path}")
            if arr.shape[0] != len(self.principles):
                raise ValueError(
                    f"Embedding row count mismatch: {arr.shape[0]} vs {len(self.principles)}"
                )
            return arr.astype(np.float32, copy=False)

        if not self.config.auto_build_embeddings:
            raise FileNotFoundError(
                f"Embeddings file not found: {self.embeddings_path}. "
                "Provide a prebuilt embedding index or enable auto_build_embeddings."
            )

        vectors: List[List[float]] = []
        for p in self.principles:
            vec = fetch_ollama_embedding(
                p["text"],
                model=self.config.embed_model,
                timeout_sec=20.0,
            )
            vectors.append([float(v) for v in vec])
        matrix = np.asarray(vectors, dtype=np.float32)
        self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(self.embeddings_path, matrix)
        return matrix

    def _load_reranker(self, path: Path) -> None:
        if torch is None or nn is None:
            raise RuntimeError(
                "KIS2 reranker requested but torch is unavailable. "
                "Install torch or omit --kis2-reranker-json."
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        artifact = payload.get("artifact", {}) or {}
        feature_names = artifact.get("feature_names", []) or []
        hidden_dim = int((payload.get("training", {}) or {}).get("hidden_dim", 16))
        state_raw = artifact.get("state_dict", {}) or {}
        if not feature_names or not state_raw:
            raise ValueError(f"Invalid KIS2 reranker artifact: {path}")
        model = _RerankerMLP(in_dim=len(feature_names), hidden_dim=hidden_dim)
        state: Dict[str, torch.Tensor] = {
            str(k): torch.tensor(v, dtype=torch.float32) for k, v in state_raw.items()
        }
        model.load_state_dict(state, strict=True)
        self._reranker = model.eval()
        self._reranker_features = [str(x) for x in feature_names]

    @staticmethod
    def _domain_match_score(domain: str, activated_domains: List[str], activated_principles: List[str]) -> float:
        d = str(domain or "").strip().lower()
        if not d:
            return 0.0
        if d in {str(x).strip().lower() for x in activated_domains}:
            return 1.0
        # Fallback: if principle-level activation exists, give partial credit.
        if activated_principles:
            return 0.5
        return 0.0

    def _feature_row(
        self,
        *,
        similarity: float,
        irreversibility: float,
        disagreement_entropy: float,
        domain_match: float,
        historical_success_rate: float,
        scenario_category_code: float,
    ) -> Dict[str, float]:
        return {
            "similarity_score": float(similarity),
            "irreversibility_score": float(_clamp01(irreversibility)),
            "disagreement_entropy": float(_clamp01(disagreement_entropy)),
            "domain_match": float(_clamp01(domain_match)),
            "historical_success_rate": float(_clamp01(historical_success_rate)),
            "scenario_category": float(_clamp01(scenario_category_code)),
        }

    def _rerank_score(self, features: Dict[str, float]) -> Optional[float]:
        if self._reranker is None:
            return None
        values = [float(features.get(name, 0.0)) for name in self._reranker_features]
        x = torch.tensor(values, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            score = torch.sigmoid(self._reranker(x)).cpu().item()
        return _clamp01(float(score))

    def retrieve(
        self,
        *,
        scenario: Dict[str, Any],
        irreversibility: float = 0.5,
        disagreement_entropy: float = 0.0,
        activated_domains: Optional[List[str]] = None,
        activated_principles: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        k = int(top_k if top_k is not None else self.config.top_k)
        k = max(1, min(k, len(self.principles)))
        query = fetch_ollama_embedding(
            scenario_text_for_embedding(scenario),
            model=self.config.embed_model,
            timeout_sec=20.0,
        )
        q = np.asarray(query, dtype=np.float32)
        if q.shape[0] != self.embeddings.shape[1]:
            raise ValueError(
                "Embedding dimension mismatch between scenario embedding and principle index."
            )
        sims = _cosine_sim_matrix(q, self.embeddings)
        idx = np.argsort(sims)[-k:][::-1]
        active_domains = list(activated_domains or [])
        active_principles = list(activated_principles or [])
        category_code = _category_code(str(scenario.get("category", "")))

        rows: List[Dict[str, Any]] = []
        for rank, i in enumerate(idx, start=1):
            p = self.principles[int(i)]
            sim = float((float(sims[int(i)]) + 1.0) / 2.0)  # to [0,1]
            features = self._feature_row(
                similarity=sim,
                irreversibility=irreversibility,
                disagreement_entropy=disagreement_entropy,
                domain_match=self._domain_match_score(
                    p.get("domain", ""),
                    active_domains,
                    active_principles,
                ),
                historical_success_rate=float(p.get("historical_success_rate", 0.5)),
                scenario_category_code=category_code,
            )
            rerank = self._rerank_score(features)
            final_score = sim if rerank is None else (0.65 * sim + 0.35 * rerank)
            rows.append(
                {
                    "rank": int(rank),
                    "id": str(p["id"]),
                    "text": str(p["text"]),
                    "domain": str(p["domain"]),
                    "similarity_score": float(sim),
                    "rerank_score": None if rerank is None else float(rerank),
                    "final_score": float(_clamp01(final_score)),
                    "features": features,
                }
            )
        rows.sort(key=lambda r: float(r["final_score"]), reverse=True)
        return {
            "enabled": True,
            "top_k": int(k),
            "embed_model": self.config.embed_model,
            "reranker_enabled": bool(self._reranker is not None),
            "retrieved": rows,
            "principles": [str(r["id"]) for r in rows],
        }

    @staticmethod
    def build_prompt_block(retrieval: Dict[str, Any] | None) -> str:
        if not retrieval or not retrieval.get("retrieved"):
            return ""
        rows = list(retrieval.get("retrieved", []))
        listed = "\n".join(
            f"{i+1}. {row.get('id')} ({row.get('domain')}, score={float(row.get('final_score', 0.0)):.2f})"
            for i, row in enumerate(rows)
        )
        checks = [PRINCIPLE_CHECKS.get(str(row.get("id")), "") for row in rows]
        checks = [c for c in checks if c]
        checks_blob = "\n".join(checks)
        return f"""
Relevant strategic principles (KIS2 retrieval):
{listed}

Mandatory KIS2 coverage pass (internal; keep final output format unchanged):
- Before finalizing, explicitly address each principle above.
{checks_blob}
- If a principle changes the preferred path, update DECISION and explain tradeoff in RATIONALE.
"""

    def metadata(self) -> Dict[str, Any]:
        return {
            "enabled": bool(self.config.enabled),
            "principles_path": str(self.principles_path),
            "embeddings_path": str(self.embeddings_path),
            "embed_model": self.config.embed_model,
            "top_k": int(self.config.top_k),
            "reranker_json": self.config.reranker_json,
            "catalog_size": int(len(self.principles)),
            "embedding_dim": int(self.embeddings.shape[1]),
            "reranker_enabled": bool(self._reranker is not None),
        }


def scenario_text_for_embedding(scenario: Dict[str, Any]) -> str:
    category = str(scenario.get("category", "")).strip()
    prompt = str(scenario.get("input", "")).strip()
    context = str(scenario.get("context", "")).strip()
    return f"Category: {category}\nScenario: {prompt}\nContext: {context}".strip()


_EMBED_CACHE: Dict[str, List[float]] = {}


def fetch_ollama_embedding(
    text: str,
    *,
    model: str = "nomic-embed-text:latest",
    timeout_sec: float = 20.0,
) -> List[float]:
    key = f"{model}::{text}"
    if key in _EMBED_CACHE:
        return list(_EMBED_CACHE[key])
    base_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    response = requests.post(
        f"{base_url}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=timeout_sec,
    )
    response.raise_for_status()
    payload = response.json()
    vec = payload.get("embedding")
    if not isinstance(vec, list) or not vec:
        raise RuntimeError("Embedding response missing vector.")
    out = [float(v) for v in vec]
    _EMBED_CACHE[key] = out
    return list(out)
