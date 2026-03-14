"""Build a scenario similarity index from ERA-Bench scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from .embedding_model import ScenarioEmbedder, ScenarioEmbeddingConfig
from .scenario_index import ScenarioIndex, ScenarioRecord


def _load_scenarios(root: Path, *, limit: int | None = None) -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = []
    for category_dir in sorted((root / "scenarios").iterdir()):
        if not category_dir.is_dir():
            continue
        for path in sorted(category_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            scenarios.append(data)
            if limit and len(scenarios) >= limit:
                return scenarios
    return scenarios


def _scenario_text(scenario: Dict[str, Any]) -> str:
    prompt = str(scenario.get("prompt", "")).strip()
    context = scenario.get("context", {}) or {}
    if isinstance(context, dict):
        context_text = json.dumps(context, ensure_ascii=True, sort_keys=True)
    else:
        context_text = str(context)
    return f"{prompt}\n{context_text}".strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build scenario similarity index.")
    parser.add_argument("--benchmark", default="era_benchmark", help="Benchmark root directory.")
    parser.add_argument("--output", default="data/scenario_memory/scenario_index", help="Index base path.")
    parser.add_argument("--backend", default="sentence_transformers", help="Embedding backend.")
    parser.add_argument("--model-name", default="all-MiniLM-L6-v2", help="Embedding model name.")
    parser.add_argument("--local-files-only", action="store_true", help="Use local embedding weights only.")
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on scenarios.")
    args = parser.parse_args()

    benchmark_root = Path(args.benchmark)
    scenarios = _load_scenarios(benchmark_root, limit=args.limit)
    if not scenarios:
        raise RuntimeError(f"No scenarios found under {benchmark_root}.")

    config = ScenarioEmbeddingConfig(
        backend=str(args.backend),
        model_name=str(args.model_name),
        local_files_only=bool(args.local_files_only),
    )
    embedder = ScenarioEmbedder(config)

    texts = [_scenario_text(item) for item in scenarios]
    if config.backend != "sentence_transformers":
        embedder.fit(texts)

    vectors = embedder.embed_many(texts)
    index = ScenarioIndex(int(vectors.shape[1]))
    records: List[ScenarioRecord] = []
    for scenario in scenarios:
        records.append(
            ScenarioRecord(
                scenario_id=str(scenario.get("scenario_id", "")),
                prompt=str(scenario.get("prompt", "")),
                expected_decision=str(scenario.get("expected_decision", "")),
                category=str(scenario.get("category", "")),
                difficulty=str(scenario.get("difficulty", "")),
                context=scenario.get("context") or {},
            )
        )
    index.add_many(vectors, records)
    index.save(
        Path(args.output),
        metadata={
            "embedding_backend": config.backend,
            "model_name": config.model_name,
            "local_files_only": config.local_files_only,
            "scenario_count": len(records),
        },
    )
    print(f"Scenario index built at {args.output} ({len(records)} records).")


if __name__ == "__main__":
    main()
