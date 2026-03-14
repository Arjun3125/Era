"""Embedding model wrapper for scenario similarity search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import numpy as np


@dataclass
class ScenarioEmbeddingConfig:
    backend: str = "sentence_transformers"
    model_name: str = "all-MiniLM-L6-v2"
    local_files_only: bool = False
    max_features: int = 4096


class ScenarioEmbedder:
    def __init__(self, config: ScenarioEmbeddingConfig | None = None) -> None:
        self.config = config or ScenarioEmbeddingConfig()
        self._st_model = None
        self._tfidf = None

    def fit(self, texts: Iterable[str]) -> None:
        if self.config.backend == "sentence_transformers":
            self._ensure_sentence_transformer()
            return
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(max_features=int(self.config.max_features))
        vectorizer.fit(list(texts))
        self._tfidf = vectorizer

    def embed(self, text: str) -> np.ndarray:
        return self.embed_many([text])[0]

    def embed_many(self, texts: Iterable[str]) -> np.ndarray:
        items = [str(item) for item in texts]
        if self.config.backend == "sentence_transformers":
            self._ensure_sentence_transformer()
            vectors = self._st_model.encode(items)
            return np.asarray(vectors, dtype="float32")
        if self._tfidf is None:
            raise RuntimeError("TF-IDF embedder must be fitted before encoding.")
        vectors = self._tfidf.transform(items).toarray()
        return np.asarray(vectors, dtype="float32")

    def dimension(self, sample_text: str | None = None) -> int:
        if self.config.backend == "sentence_transformers":
            self._ensure_sentence_transformer()
            sample = sample_text or "sample"
            return int(self._st_model.encode([sample]).shape[1])
        if self._tfidf is None:
            raise RuntimeError("TF-IDF embedder must be fitted before determining dimension.")
        return int(len(self._tfidf.get_feature_names_out()))

    def _ensure_sentence_transformer(self) -> None:
        if self._st_model is not None:
            return
        from sentence_transformers import SentenceTransformer

        self._st_model = SentenceTransformer(
            self.config.model_name,
            local_files_only=bool(self.config.local_files_only),
        )
