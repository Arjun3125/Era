"""Feature extraction for value model training and inference."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


@dataclass
class FeatureConfig:
    backend: str = "tfidf"
    model_name: str = ""
    local_files_only: bool = False


class FeatureExtractor:
    def __init__(self, config: FeatureConfig | None = None):
        self.config = config or FeatureConfig()
        self.prompt_vectorizer = None
        self.option_vectorizer = None
        self._st_model = None

    def fit(self, prompt_texts: List[str], option_texts: List[str]) -> None:
        if self.config.backend == "sentence_transformers":
            self._ensure_sentence_transformer()
            return

        from sklearn.feature_extraction.text import TfidfVectorizer

        self.prompt_vectorizer = TfidfVectorizer(max_features=2000)
        self.option_vectorizer = TfidfVectorizer(max_features=1000)
        self.prompt_vectorizer.fit(prompt_texts)
        self.option_vectorizer.fit(option_texts)

    def encode(self, prompt: str, option: str, context: Dict[str, Any]) -> np.ndarray:
        prompt_text = self._format_prompt(prompt, context)
        option_text = str(option or "")

        if self.config.backend == "sentence_transformers":
            self._ensure_sentence_transformer()
            prompt_vec = np.asarray(self._st_model.encode([prompt_text])[0], dtype=float)
            option_vec = np.asarray(self._st_model.encode([option_text])[0], dtype=float)
            return np.concatenate([prompt_vec, option_vec], axis=0)

        if self.prompt_vectorizer is None or self.option_vectorizer is None:
            raise RuntimeError("TF-IDF feature extractor not fitted.")
        prompt_vec = self.prompt_vectorizer.transform([prompt_text]).toarray()[0]
        option_vec = self.option_vectorizer.transform([option_text]).toarray()[0]
        return np.concatenate([prompt_vec, option_vec], axis=0)

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        config_path = path / "feature_config.json"
        config_path.write_text(json.dumps(self.config.__dict__, indent=2), encoding="utf-8")

        if self.config.backend == "sentence_transformers":
            return

        import pickle

        with (path / "prompt_vectorizer.pkl").open("wb") as handle:
            pickle.dump(self.prompt_vectorizer, handle)
        with (path / "option_vectorizer.pkl").open("wb") as handle:
            pickle.dump(self.option_vectorizer, handle)

    @classmethod
    def load(cls, path: Path) -> "FeatureExtractor":
        config_path = path / "feature_config.json"
        config = FeatureConfig(**json.loads(config_path.read_text(encoding="utf-8")))
        extractor = cls(config=config)
        if config.backend == "sentence_transformers":
            extractor._ensure_sentence_transformer()
            return extractor

        import pickle

        with (path / "prompt_vectorizer.pkl").open("rb") as handle:
            extractor.prompt_vectorizer = pickle.load(handle)
        with (path / "option_vectorizer.pkl").open("rb") as handle:
            extractor.option_vectorizer = pickle.load(handle)
        return extractor

    def _ensure_sentence_transformer(self) -> None:
        if self._st_model is not None:
            return
        from sentence_transformers import SentenceTransformer

        model_name = self.config.model_name or "all-MiniLM-L6-v2"
        self._st_model = SentenceTransformer(
            model_name,
            local_files_only=bool(self.config.local_files_only),
        )

    @staticmethod
    def _format_prompt(prompt: str, context: Dict[str, Any]) -> str:
        context_items = [f"{key}: {context[key]}" for key in sorted(context.keys())]
        context_text = "\n".join(context_items)
        return f"{prompt}\n{context_text}".strip()
