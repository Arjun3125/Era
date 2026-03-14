"""Scenario embedding encoder for unified feature representation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np


@dataclass
class ScenarioEncoderConfig:
    backend: str = "sentence_transformers"
    model_name: str = "all-MiniLM-L6-v2"
    local_files_only: bool = False
    normalize: bool = True


class ScenarioEncoder:
    def __init__(self, config: ScenarioEncoderConfig | None = None) -> None:
        self.config = config or ScenarioEncoderConfig()
        self._model = None
        self._cache: Dict[str, np.ndarray] = {}

    def encode_scenario(
        self,
        *,
        prompt: str,
        context: Dict[str, Any] | None = None,
        knowledge: Iterable[Any] | None = None,
    ) -> np.ndarray:
        text = self._format_scenario(prompt=prompt, context=context, knowledge=knowledge)
        return self.encode_text(text)

    def encode_text(self, text: str) -> np.ndarray:
        normalized = self._normalize_text(text)
        cached = self._cache.get(normalized)
        if cached is not None:
            return cached

        self._ensure_model()
        vector = np.asarray(self._model.encode([normalized])[0], dtype=float)
        if self.config.normalize:
            vector = self._l2_normalize(vector)
        self._cache[normalized] = vector
        return vector

    def warm_cache(self, texts: List[str]) -> None:
        if not texts:
            return
        self._ensure_model()
        missing = [self._normalize_text(text) for text in texts if text not in self._cache]
        if not missing:
            return
        vectors = self._model.encode(missing)
        for text, vec in zip(missing, vectors):
            arr = np.asarray(vec, dtype=float)
            if self.config.normalize:
                arr = self._l2_normalize(arr)
            self._cache[text] = arr

    def dimension(self) -> Optional[int]:
        self._ensure_model()
        try:
            return int(self._model.get_sentence_embedding_dimension())
        except Exception:
            return None

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        backend = self._normalize_text(self.config.backend).lower()
        if backend in {"sentence_transformers", "e5", "nomic", "embedding"}:
            from sentence_transformers import SentenceTransformer

            model_name = self.config.model_name or "all-MiniLM-L6-v2"
            self._model = SentenceTransformer(
                model_name,
                local_files_only=bool(self.config.local_files_only),
            )
            return
        raise ValueError(f"Unsupported encoder backend: {self.config.backend}")

    @staticmethod
    def _format_scenario(
        *,
        prompt: str,
        context: Dict[str, Any] | None,
        knowledge: Iterable[Any] | None,
    ) -> str:
        parts: List[str] = [str(prompt or "").strip()]
        if context:
            for key in sorted(context.keys()):
                parts.append(f"{key}: {context[key]}")
        if knowledge:
            knowledge_items = [str(item).strip() for item in knowledge if str(item).strip()]
            if knowledge_items:
                parts.append("knowledge: " + " | ".join(knowledge_items))
        return "\n".join(part for part in parts if part)

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _l2_normalize(vec: np.ndarray) -> np.ndarray:
        denom = np.linalg.norm(vec)
        if denom <= 0:
            return vec
        return vec / denom
