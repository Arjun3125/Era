"""Pipeline module for scenario similarity retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from core.contracts import (
    ExecutionContext,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
)

from .embedding_model import ScenarioEmbedder, ScenarioEmbeddingConfig
from .retrieval import ScenarioRetriever
from .scenario_index import ScenarioIndex


def _coerce_mapping(value: Any) -> Dict[str, Any] | None:
    if isinstance(value, Mapping):
        try:
            items = value.items()
        except Exception:
            return {}
        return {str(key): item for key, item in items}
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        try:
            items = list(value)
        except Exception:
            return None
        mapping: Dict[str, Any] = {}
        for raw_item in items:
            try:
                key, item_value = raw_item
            except Exception:
                return None
            mapping[str(key)] = item_value
        return mapping
    return None


@dataclass
class ScenarioMemoryModule(ModulePlugin):
    """Retrieve similar scenarios and append to routing context."""

    default_index_path: Path = Path("data/scenario_memory/scenario_index")
    _index_cache: Dict[str, ScenarioIndex] = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def create(cls) -> "ScenarioMemoryModule":
        return cls()

    def name(self) -> str:
        return "scenario_memory"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "retrieves_similar_scenarios": True,
            "augments_routing_context": True,
            "supports_embedding_index": True,
        }

    def validate(self, context: ExecutionContext) -> None:
        if not isinstance(context.state, dict):
            raise TypeError("ExecutionContext.state must be a dictionary.")

    def execute(self, context: ExecutionContext) -> ModuleResult:
        routing_context = _coerce_mapping(context.state.get("routing_context", {})) or {}
        enabled = self._parse_bool(
            routing_context.get("scenario_memory_enabled"),
            default=bool(routing_context.get("scenario_index_path")),
        )
        if not enabled:
            return ModuleResult(
                status=ModuleStatus.SUCCESS,
                outputs={
                    "scenario_memory_matches": [],
                    "scenario_memory_context": [],
                    "scenario_memory_warnings": [],
                },
                metrics={"scenario_memory_hits": 0},
            )

        index_path = self._resolve_index_path(routing_context)
        warnings = []
        try:
            index = self._load_index(index_path)
        except Exception as exc:
            warnings.append(f"scenario_memory_index_load_failed:{type(exc).__name__}:{exc}")
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "scenario_memory_matches": [],
                    "scenario_memory_context": [],
                    "scenario_memory_warnings": warnings,
                },
                metrics={"scenario_memory_hits": 0},
                errors=warnings,
            )

        top_k = self._safe_int(routing_context.get("scenario_memory_k"), default=5, minimum=1)
        min_similarity = self._safe_float(
            routing_context.get("scenario_memory_min_similarity"),
            default=0.75,
        )
        query_context = self._extract_query_context(routing_context)
        backend = routing_context.get("scenario_memory_backend")
        model_name = routing_context.get("scenario_memory_model")
        local_only = routing_context.get("scenario_memory_local_only")
        if index.metadata:
            backend = backend or index.metadata.get("embedding_backend")
            model_name = model_name or index.metadata.get("model_name")
            if local_only is None:
                local_only = index.metadata.get("local_files_only")
        embedder_config = ScenarioEmbeddingConfig(
            backend=str(backend or "sentence_transformers"),
            model_name=str(model_name or "all-MiniLM-L6-v2"),
            local_files_only=self._parse_bool(local_only, default=False),
        )
        retriever = ScenarioRetriever(index, embedder=ScenarioEmbedder(embedder_config))
        matches = retriever.retrieve(
            prompt=context.input_contract.user_input,
            context=query_context,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        formatted = retriever.format_matches(matches)

        updated_context = dict(routing_context)
        extra_context = self._to_string_list(updated_context.get("extra_context"))
        extra_context.extend(formatted)
        updated_context["extra_context"] = extra_context

        outputs = {
            "scenario_memory_matches": [
                {
                    "scenario_id": match.record.scenario_id,
                    "category": match.record.category,
                    "difficulty": match.record.difficulty,
                    "expected_decision": match.record.expected_decision,
                    "similarity": match.similarity,
                    "prompt": match.record.prompt,
                }
                for match in matches
            ],
            "scenario_memory_context": formatted,
            "scenario_memory_warnings": warnings,
            "scenario_memory_index": str(index_path),
            "routing_context": updated_context,
        }
        return ModuleResult(
            status=ModuleStatus.SUCCESS if not warnings else ModuleStatus.DEGRADED,
            outputs=outputs,
            metrics={"scenario_memory_hits": len(formatted)},
            errors=warnings,
        )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True, details={})

    def _load_index(self, path: Path) -> ScenarioIndex:
        if self._index_cache is None:
            self._index_cache = {}
        key = str(path)
        if key in self._index_cache:
            return self._index_cache[key]
        index = ScenarioIndex.load(path)
        self._index_cache[key] = index
        return index

    def _resolve_index_path(self, routing_context: Mapping[str, Any]) -> Path:
        raw = (
            routing_context.get("scenario_index_path")
            or routing_context.get("scenario_memory_index_path")
            or routing_context.get("scenario_memory_path")
        )
        if raw:
            return Path(str(raw))
        return self.default_index_path

    @staticmethod
    def _extract_query_context(routing_context: Mapping[str, Any]) -> Dict[str, Any]:
        keys = [
            "domains",
            "stakes",
            "reversibility",
            "key_entities",
            "domain_scores",
            "context",
        ]
        context: Dict[str, Any] = {}
        for key in keys:
            if key in routing_context:
                context[key] = routing_context.get(key)
        return context

    @staticmethod
    def _parse_bool(value: Any, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return default
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return default

    @staticmethod
    def _safe_int(value: Any, *, default: int, minimum: int) -> int:
        try:
            numeric = int(value)
        except Exception:
            return default
        return numeric if numeric >= minimum else default

    @staticmethod
    def _safe_float(value: Any, *, default: float) -> float:
        try:
            numeric = float(value)
        except Exception:
            return default
        if numeric != numeric or numeric in (float("inf"), float("-inf")):
            return default
        return numeric

    @staticmethod
    def _to_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            return [bytes(value).decode("utf-8", errors="replace").strip()]
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            items = []
            for item in value:
                text = str(item).strip()
                if text:
                    items.append(text)
            return items
        if isinstance(value, Mapping):
            return []
        try:
            return [str(value).strip()] if str(value).strip() else []
        except Exception:
            return []
