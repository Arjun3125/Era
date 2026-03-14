"""Vector index for scenario similarity search."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import json
import numpy as np


def _normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return vectors / norms


def _try_import_faiss() -> Any | None:
    try:
        import faiss  # type: ignore
    except Exception:
        return None
    return faiss


@dataclass
class ScenarioRecord:
    scenario_id: str
    prompt: str
    expected_decision: str
    category: str = ""
    difficulty: str = ""
    context: Dict[str, Any] | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "prompt": self.prompt,
            "expected_decision": self.expected_decision,
            "category": self.category,
            "difficulty": self.difficulty,
            "context": dict(self.context or {}),
        }


@dataclass
class ScenarioMatch:
    record: ScenarioRecord
    similarity: float


class ScenarioIndex:
    def __init__(self, dim: int, *, use_faiss: bool = True) -> None:
        self.dim = int(dim)
        self._use_faiss = bool(use_faiss)
        self._faiss = _try_import_faiss() if use_faiss else None
        self._index = None
        self._vectors: Optional[np.ndarray] = None
        self._records: List[ScenarioRecord] = []
        self.metadata: Dict[str, Any] = {}

    @property
    def size(self) -> int:
        return len(self._records)

    def add(self, vector: np.ndarray, record: ScenarioRecord) -> None:
        self.add_many(np.asarray([vector], dtype="float32"), [record])

    def add_many(self, vectors: np.ndarray, records: Sequence[ScenarioRecord]) -> None:
        if len(records) != len(vectors):
            raise ValueError("Vectors and records must be the same length.")
        vectors = np.asarray(vectors, dtype="float32")
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError("Vectors must be 2D with matching dimension.")
        normalized = _normalize_vectors(vectors)
        if self._vectors is None:
            self._vectors = normalized.copy()
        else:
            self._vectors = np.vstack([self._vectors, normalized])
        self._records.extend(records)
        if self._faiss is not None:
            if self._index is None:
                self._index = self._faiss.IndexFlatIP(self.dim)
            self._index.add(normalized)

    def search(
        self, vector: np.ndarray, *, k: int = 5, min_similarity: float | None = None
    ) -> List[ScenarioMatch]:
        if self._vectors is None or not self._records:
            return []
        query = np.asarray(vector, dtype="float32").reshape(1, -1)
        if query.shape[1] != self.dim:
            raise ValueError("Query vector dimension mismatch.")
        query = _normalize_vectors(query)
        k = max(1, min(int(k), len(self._records)))
        scores: np.ndarray
        indices: np.ndarray
        if self._index is not None:
            scores, indices = self._index.search(query, k)
        else:
            scores = (self._vectors @ query.T).reshape(1, -1)
            indices = np.argsort(-scores, axis=1)[:, :k]
            scores = np.take_along_axis(scores, indices, axis=1)
        results: List[ScenarioMatch] = []
        for score, idx in zip(scores[0], indices[0]):
            similarity = float(score)
            if min_similarity is not None and similarity < min_similarity:
                continue
            record = self._records[int(idx)]
            results.append(ScenarioMatch(record=record, similarity=round(similarity, 4)))
        return results

    def save(self, path: Path, *, metadata: Dict[str, Any] | None = None) -> None:
        base = self._normalize_base_path(path)
        base.parent.mkdir(parents=True, exist_ok=True)
        if self._vectors is None:
            raise RuntimeError("ScenarioIndex has no vectors to save.")
        np.savez_compressed(base.with_suffix(".npz"), vectors=self._vectors)
        if metadata is not None:
            self.metadata = dict(metadata)
        payload = {
            "version": "1.0",
            "dimension": self.dim,
            "metric": "cosine",
            "metadata": dict(self.metadata),
            "records": [record.as_dict() for record in self._records],
        }
        base.with_suffix(".json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "ScenarioIndex":
        base = cls._normalize_base_path(path)
        json_path = base.with_suffix(".json")
        npz_path = base.with_suffix(".npz")
        if not json_path.exists() or not npz_path.exists():
            raise FileNotFoundError(f"Scenario index files not found for base path: {base}")
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        vectors = np.load(npz_path)["vectors"]
        index = cls(int(payload.get("dimension", vectors.shape[1])))
        index.metadata = payload.get("metadata", {}) or {}
        records = []
        for raw in payload.get("records", []):
            records.append(
                ScenarioRecord(
                    scenario_id=str(raw.get("scenario_id", "")),
                    prompt=str(raw.get("prompt", "")),
                    expected_decision=str(raw.get("expected_decision", "")),
                    category=str(raw.get("category", "")),
                    difficulty=str(raw.get("difficulty", "")),
                    context=raw.get("context") or {},
                )
            )
        index.add_many(vectors, records)
        return index

    @staticmethod
    def _normalize_base_path(path: Path) -> Path:
        suffix = path.suffix.lower()
        if suffix in {".npz", ".json"}:
            return path.with_suffix("")
        return path
