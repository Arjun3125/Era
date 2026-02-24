#!/usr/bin/env python
"""
Create reproducible train/val/test split manifest for benchmark scenarios.

Policy:
- Stratified by scenario category
- Fixed random seed for reproducibility
- Includes OOD in train while preserving strict val/test holdouts
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.scoring.rubric_engine import RubricEngine


CORE_CATEGORIES = {"irreversible", "emotional", "strategic", "long_horizon"}
ADVERSARIAL_CATEGORY = "adversarial"
OOD_CATEGORY = "out_of_distribution"


def _allocate_counts(n: int, ratios: Tuple[float, float, float]) -> Tuple[int, int, int]:
    """
    Deterministic apportionment that sums exactly to n.
    """
    raw = [n * r for r in ratios]
    base = [int(math.floor(v)) for v in raw]
    remainder = n - sum(base)

    fractional = [raw[i] - base[i] for i in range(3)]
    order = sorted(range(3), key=lambda i: (fractional[i], ratios[i]), reverse=True)
    for i in range(remainder):
        base[order[i % len(order)]] += 1

    # Keep strict holdouts for categories with enough data.
    if n >= 3:
        if base[1] == 0:
            donor = 0 if base[0] > 1 else 2
            base[donor] -= 1
            base[1] += 1
        if base[2] == 0:
            donor = 0 if base[0] > 1 else 1
            base[donor] -= 1
            base[2] += 1

    return base[0], base[1], base[2]


def _dataset_name_for_category(category: str) -> str:
    if category in CORE_CATEGORIES:
        return "core"
    if category == ADVERSARIAL_CATEGORY:
        return "adversarial"
    if category == OOD_CATEGORY:
        return "ood"
    return "all"


def build_split_manifest(
    *,
    seed: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    benchmark_dir: str,
) -> Dict:
    if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-9:
        raise ValueError("Ratios must sum to 1.0")

    rubric = RubricEngine(benchmark_dir=benchmark_dir)
    if not rubric.verify_dataset_integrity():
        raise RuntimeError("Dataset integrity verification failed.")
    scenarios = rubric.load_all_scenarios()

    by_category: Dict[str, List[str]] = {}
    for scenario_id, scenario in scenarios.items():
        category = scenario.get("category", "unknown")
        by_category.setdefault(category, []).append(scenario_id)

    rng = random.Random(seed)

    split_ids: Dict[str, Dict[str, List[str]]] = {
        "train": {"all": [], "core": [], "adversarial": [], "ood": []},
        "val": {"all": [], "core": [], "adversarial": [], "ood": []},
        "test": {"all": [], "core": [], "adversarial": [], "ood": []},
    }
    per_category_counts: Dict[str, Dict[str, int]] = {}

    ratios = (train_ratio, val_ratio, test_ratio)
    for category in sorted(by_category.keys()):
        ids = sorted(by_category[category])
        rng.shuffle(ids)
        n = len(ids)
        n_train, n_val, n_test = _allocate_counts(n, ratios)

        train_ids = ids[:n_train]
        val_ids = ids[n_train : n_train + n_val]
        test_ids = ids[n_train + n_val : n_train + n_val + n_test]

        if len(train_ids) + len(val_ids) + len(test_ids) != n:
            raise RuntimeError(f"Split allocation mismatch in category '{category}'.")

        dataset_name = _dataset_name_for_category(category)
        for split_name, chosen in (
            ("train", train_ids),
            ("val", val_ids),
            ("test", test_ids),
        ):
            split_ids[split_name]["all"].extend(chosen)
            if dataset_name in split_ids[split_name]:
                split_ids[split_name][dataset_name].extend(chosen)

        per_category_counts[category] = {
            "total": n,
            "train": len(train_ids),
            "val": len(val_ids),
            "test": len(test_ids),
        }

    # Deterministic ordering for stored artifacts.
    for split_name in split_ids:
        for dataset_name in split_ids[split_name]:
            split_ids[split_name][dataset_name] = sorted(split_ids[split_name][dataset_name])

    # Strict checks: no overlap between splits and full coverage.
    train_set = set(split_ids["train"]["all"])
    val_set = set(split_ids["val"]["all"])
    test_set = set(split_ids["test"]["all"])
    if train_set & val_set or train_set & test_set or val_set & test_set:
        raise RuntimeError("Split overlap detected; holdouts are not strict.")
    if len(train_set | val_set | test_set) != len(scenarios):
        raise RuntimeError("Split coverage mismatch; some scenarios are missing.")

    counts = {
        split_name: {
            dataset_name: len(ids)
            for dataset_name, ids in dataset_map.items()
        }
        for split_name, dataset_map in split_ids.items()
    }

    manifest = {
        "metadata": {
            "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_manifest": str(Path(benchmark_dir) / "dataset_manifest.json"),
            "seed": seed,
            "ratios": {
                "train": train_ratio,
                "val": val_ratio,
                "test": test_ratio,
            },
            "total_scenarios": len(scenarios),
            "policy": "stratified_by_category_with_strict_holdouts",
        },
        "category_counts": per_category_counts,
        "counts": counts,
        "splits": split_ids,
    }
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Create benchmark split manifest")
    parser.add_argument("--seed", type=int, default=42, help="Split random seed")
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Train ratio")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Validation ratio")
    parser.add_argument("--test-ratio", type=float, default=0.15, help="Test ratio")
    parser.add_argument(
        "--benchmark-dir",
        default=str(ROOT / "evaluation" / "benchmark_dataset"),
        help="Benchmark dataset directory",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "evaluation" / "benchmark_dataset" / "split_manifest_seed42.json"),
        help="Output manifest path",
    )
    args = parser.parse_args()

    manifest = build_split_manifest(
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        benchmark_dir=args.benchmark_dir,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved split manifest: {out}")
    print("Counts:")
    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
