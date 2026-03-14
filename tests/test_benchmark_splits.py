from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_split_ids(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [str(item) for item in payload]
    raise AssertionError(f"Unsupported split format: {path}")


def _load_scenarios(root: Path) -> dict[str, dict]:
    scenarios: dict[str, dict] = {}
    for category_dir in (root / "scenarios").iterdir():
        if not category_dir.is_dir():
            continue
        for path in category_dir.glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            scenario_id = str(payload.get("scenario_id"))
            scenarios[scenario_id] = payload
    return scenarios


def test_benchmark_splits_cover_all_scenarios() -> None:
    benchmark_root = ROOT / "era_benchmark"
    index = json.loads((benchmark_root / "benchmark_index.json").read_text(encoding="utf-8"))
    version = str(index.get("version", "1.0")).replace(".", "_")
    split_root = benchmark_root / "splits" / f"v{version}"

    train_ids = _load_split_ids(split_root / "train.json")
    test_ids = _load_split_ids(split_root / "test.json")
    hard_ids = _load_split_ids(split_root / "hard.json")

    train_set = set(train_ids)
    test_set = set(test_ids)
    hard_set = set(hard_ids)

    assert train_set.isdisjoint(test_set)
    scenarios = _load_scenarios(benchmark_root)
    all_ids = set(scenarios.keys())
    assert train_set | test_set == all_ids
    assert hard_set.issubset(all_ids)

    hard_levels = {"hard", "expert"}
    for scenario_id in hard_set:
        difficulty = str(scenarios[scenario_id].get("difficulty", "")).lower()
        assert difficulty in hard_levels
