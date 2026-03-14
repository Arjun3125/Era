"""Feature extraction for learning models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from modules.representation import ScenarioEncoder, ScenarioEncoderConfig


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
        self._scenario_encoder: ScenarioEncoder | None = None
        self._prompt_cache: Dict[str, np.ndarray] = {}
        self._option_cache: Dict[str, np.ndarray] = {}

    def fit(self, prompt_texts: List[str], option_texts: List[str]) -> None:
        if self.config.backend == "sentence_transformers":
            self._ensure_sentence_transformer()
            return
        if self.config.backend == "scenario_encoder":
            self._ensure_scenario_encoder()
            return

        from sklearn.feature_extraction.text import TfidfVectorizer

        self.prompt_vectorizer = TfidfVectorizer(max_features=2000)
        self.option_vectorizer = TfidfVectorizer(max_features=1000)
        self.prompt_vectorizer.fit(prompt_texts)
        if any(text.strip() for text in option_texts):
            self.option_vectorizer.fit(option_texts)
        else:
            # Avoid empty-vocabulary errors when options are intentionally blank.
            self.option_vectorizer.fit(["__empty__"])

    def encode(self, prompt: str, option: str, context: Dict[str, Any]) -> np.ndarray:
        prompt_text = self._format_prompt(prompt, context)
        option_text = str(option or "")

        if self.config.backend == "sentence_transformers":
            self._ensure_sentence_transformer()
            prompt_vec = self._prompt_cache.get(prompt_text)
            if prompt_vec is None:
                prompt_vec = np.asarray(self._st_model.encode([prompt_text])[0], dtype=float)
                self._prompt_cache[prompt_text] = prompt_vec
            option_vec = self._option_cache.get(option_text)
            if option_vec is None:
                option_vec = np.asarray(self._st_model.encode([option_text])[0], dtype=float)
                self._option_cache[option_text] = option_vec
            return np.concatenate([prompt_vec, option_vec], axis=0)
        if self.config.backend == "scenario_encoder":
            self._ensure_scenario_encoder()
            knowledge_items = self._extract_knowledge_items(context)
            prompt_vec = self._scenario_encoder.encode_scenario(
                prompt=prompt,
                context=context,
                knowledge=knowledge_items,
            )
            option_vec = self._scenario_encoder.encode_text(option_text)
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
        if self.config.backend == "scenario_encoder":
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
        if config.backend == "scenario_encoder":
            extractor._ensure_scenario_encoder()
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

    def _ensure_scenario_encoder(self) -> None:
        if self._scenario_encoder is not None:
            return
        config = ScenarioEncoderConfig(
            backend="sentence_transformers",
            model_name=self.config.model_name or "all-MiniLM-L6-v2",
            local_files_only=bool(self.config.local_files_only),
        )
        self._scenario_encoder = ScenarioEncoder(config=config)

    def warm_cache(self, prompt_texts: List[str], option_texts: List[str]) -> None:
        if self.config.backend != "sentence_transformers":
            if self.config.backend != "scenario_encoder":
                return
        if self.config.backend == "scenario_encoder":
            self._ensure_scenario_encoder()
            prompt_missing = [text for text in prompt_texts if text not in self._prompt_cache]
            option_missing = [text for text in option_texts if text not in self._option_cache]
            if prompt_missing:
                self._scenario_encoder.warm_cache(prompt_missing)
                for text in prompt_missing:
                    self._prompt_cache[text] = self._scenario_encoder.encode_text(text)
            if option_missing:
                self._scenario_encoder.warm_cache(option_missing)
                for text in option_missing:
                    self._option_cache[text] = self._scenario_encoder.encode_text(text)
            return
        self._ensure_sentence_transformer()

        prompt_missing = [text for text in prompt_texts if text not in self._prompt_cache]
        if prompt_missing:
            prompt_vecs = self._st_model.encode(prompt_missing)
            for text, vec in zip(prompt_missing, prompt_vecs):
                self._prompt_cache[text] = np.asarray(vec, dtype=float)

        option_missing = [text for text in option_texts if text not in self._option_cache]
        if option_missing:
            option_vecs = self._st_model.encode(option_missing)
            for text, vec in zip(option_missing, option_vecs):
                self._option_cache[text] = np.asarray(vec, dtype=float)

    @staticmethod
    def _format_prompt(prompt: str, context: Dict[str, Any]) -> str:
        context_items = [f"{key}: {context[key]}" for key in sorted(context.keys())]
        context_text = "\n".join(context_items)
        return f"{prompt}\n{context_text}".strip()

    @staticmethod
    def _extract_knowledge_items(context: Dict[str, Any]) -> List[str]:
        candidates = []
        for key in ("knowledge_items", "knowledge", "synthesized_knowledge", "synthesized_items"):
            value = context.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                candidates.extend([str(item) for item in value])
            else:
                candidates.append(str(value))
        return [item for item in candidates if item.strip()]
