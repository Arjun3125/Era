"""Automatic experiment scheduler."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from experiments.experiment_runner import run_experiment
from experiments.utils import get_git_commit, utc_timestamp


def load_config(path: Path) -> Dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("PyYAML is required to parse YAML configs.") from exc
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Experiment config must be a mapping.")
    return payload


def run_all(config: Dict[str, Any], *, repo_root: Path, max_workers: int) -> List[Dict[str, Any]]:
    experiments = config.get("experiments", [])
    if not isinstance(experiments, list):
        raise ValueError("Config must contain an 'experiments' list.")

    results: List[Dict[str, Any]] = []
    if max_workers <= 1:
        for exp in experiments:
            result = run_experiment(exp, repo_root=repo_root)
            results.append(result.as_dict())
    else:
        def _run(exp: Dict[str, Any]) -> Dict[str, Any]:
            return run_experiment(exp, repo_root=repo_root).as_dict()

        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for result in pool.map(_run, experiments):
                results.append(result)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run experiment scheduler.")
    parser.add_argument(
        "--config",
        default="experiments/experiment_config.yaml",
        help="Path to experiment_config.yaml (or JSON).",
    )
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--output", default="experiments/results/latest_results.json")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    config = load_config(Path(args.config))
    results = run_all(config, repo_root=repo_root, max_workers=args.max_workers)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": utc_timestamp(),
        "git_commit": get_git_commit(),
        "config": str(args.config),
        "results": results,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote scheduler results to {output_path}")


if __name__ == "__main__":
    main()
