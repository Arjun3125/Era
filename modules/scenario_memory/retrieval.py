"""Scenario retrieval utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from .embedding_model import ScenarioEmbedder, ScenarioEmbeddingConfig
from .scenario_index import ScenarioIndex, ScenarioMatch


@dataclass
class RetrievalConfig:
    top_k: int = 5
    min_similarity: float = 0.75
    include_context: bool = True


class ScenarioRetriever:
    def __init__(
        self,
        index: ScenarioIndex,
        *,
        embedder: ScenarioEmbedder | None = None,
        embedder_config: ScenarioEmbeddingConfig | None = None,
    ) -> None:
        self.index = index
        self.embedder = embedder or ScenarioEmbedder(embedder_config)

    def retrieve(
        self,
        *,
        prompt: str,
        context: Dict[str, Any] | None = None,
        top_k: int = 5,
        min_similarity: float | None = None,
    ) -> List[ScenarioMatch]:
        query = self._build_query(prompt, context or {})
        vector = self.embedder.embed(query)
        return self.index.search(vector, k=top_k, min_similarity=min_similarity)

    @staticmethod
    def format_matches(matches: Iterable[ScenarioMatch]) -> List[str]:
        formatted: List[str] = []
        for match in matches:
            record = match.record
            formatted.append(
                " | ".join(
                    [
                        f"Scenario: {record.prompt}",
                        f"Expected: {record.expected_decision}",
                        f"Category: {record.category}",
                        f"Difficulty: {record.difficulty}",
                        f"Similarity: {match.similarity:.2f}",
                    ]
                )
            )
        return formatted

    @staticmethod
    def _build_query(prompt: str, context: Dict[str, Any]) -> str:
        context_items = [f"{key}: {context[key]}" for key in sorted(context.keys())]
        context_text = "\n".join(context_items)
        return f"{prompt}\n{context_text}".strip()
