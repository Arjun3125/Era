"""Generate frozen train/test/hard splits for ERA-Bench."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


DEFAULT_HARD_LEVELS = ("hard", "expert")


def _stable_score(value: str, seed: int) -> float:
    digest = hashlib.sha1(f"{seed}:{value}".encode("utf-8")).hexdigest()
    return int(digest, 16) / float(2**160)


def _version_dir(version: str) -> str:
    cleaned = version.strip().lower().replace(".", "_")
    return f"v{cleaned}" if not cleaned.startswith("v") else cleaned


def _load_scenarios(root: Path) -> List[Dict[str, str]]:
    scenarios: List[Dict[str, str]] = []
    for category_dir in sorted((root / "scenarios").iterdir()):
        if not category_dir.is_dir():
            continue
        for path in sorted(category_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            scenarios.append(
                {
                    "scenario_id": str(payload.get("scenario_id", "")).strip(),
                    "category": str(payload.get("category", "")).strip(),
                    "difficulty": str(payload.get("difficulty", "")).strip().lower(),
                }
            )
    return scenarios


def _split_ids(
    scenarios: Iterable[Dict[str, str]],
    *,
    test_ratio: float,
    seed: int,
    hard_levels: Tuple[str, ...],
) -> Tuple[List[str], List[str], List[str], Dict[str, Dict[str, int]]]:
    train_ids: List[str] = []
    test_ids: List[str] = []
    hard_ids: List[str] = []
    category_counts: Dict[str, Dict[str, int]] = {}

    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", "")
        if not scenario_id:
            continue
        score = _stable_score(scenario_id, seed)
        if score < test_ratio:
            test_ids.append(scenario_id)
            split = "test"
        else:
            train_ids.append(scenario_id)
            split = "train"
        category = scenario.get("category", "unknown")
        category_counts.setdefault(category, {"train": 0, "test": 0, "hard": 0})
        category_counts[category][split] += 1
        if scenario.get("difficulty") in hard_levels:
            hard_ids.append(scenario_id)
            category_counts[category]["hard"] += 1

    return train_ids, test_ids, hard_ids, category_counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate frozen ERA-Bench splits.")
    parser.add_argument("--root", default="era_benchmark", help="Benchmark root directory.")
    parser.add_argument("--seed", type=int, default=20260311, help="Seed for deterministic split hashing.")
    parser.add_argument("--test-ratio", type=float, default=0.2, help="Test split ratio.")
    parser.add_argument(
        "--hard-levels",
        default=",".join(DEFAULT_HARD_LEVELS),
        help="Comma-separated difficulty labels to include in hard split.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output directory (defaults to root/splits/v<version>).",
    )
    args = parser.parse_args()

    root = Path(args.root)
    index = json.loads((root / "benchmark_index.json").read_text(encoding="utf-8"))
    version = str(index.get("version", "1")).strip()
    output_dir = Path(args.output) if args.output else root / "splits" / _version_dir(version)
    hard_levels = tuple(
        level.strip().lower() for level in str(args.hard_levels).split(",") if level.strip()
    )

    scenarios = _load_scenarios(root)
    train_ids, test_ids, hard_ids, category_counts = _split_ids(
        scenarios,
        test_ratio=float(args.test_ratio),
        seed=int(args.seed),
        hard_levels=hard_levels,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "train.json").write_text(json.dumps(sorted(train_ids), indent=2), encoding="utf-8")
    (output_dir / "test.json").write_text(json.dumps(sorted(test_ids), indent=2), encoding="utf-8")
    (output_dir / "hard.json").write_text(json.dumps(sorted(hard_ids), indent=2), encoding="utf-8")

    metadata = {
        "version": version,
        "seed": int(args.seed),
        "test_ratio": float(args.test_ratio),
        "hard_levels": list(hard_levels),
        "scenario_count": len(scenarios),
        "train_count": len(train_ids),
        "test_count": len(test_ids),
        "hard_count": len(hard_ids),
        "category_counts": category_counts,
    }
    (output_dir / "splits_index.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Wrote splits to {output_dir}")


if __name__ == "__main__":
    main()
