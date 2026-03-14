"""Continuous training loop runner: simulate -> train -> evaluate -> promote."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from training_loop.checkpoint_manager import CheckpointManager
from training_loop.evaluation_step import EvaluationConfig, run_evaluation
from training_loop.simulation_runner import SimulationConfig, run_simulation
from training_loop.training_step import ModelArtifacts, TrainingConfig, train_models


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ERA continuous training loop.")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--episodes", type=int, default=10000, help="Simulation episodes per iteration.")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--alignment-weight", type=float, default=0.4)
    parser.add_argument("--category-weights", default=None)
    parser.add_argument("--train-mode", default="simulated", help="simulated|mixed")
    parser.add_argument("--benchmark-share", type=float, default=0.4, help="Only for mixed training.")
    parser.add_argument("--backend", default="tfidf", help="tfidf|sentence_transformers")
    parser.add_argument("--model-name", default="", help="SentenceTransformer model name.")
    parser.add_argument("--st-local-only", action="store_true")
    parser.add_argument("--policy-model-type", default="logistic")
    parser.add_argument("--value-model-type", default="ridge")
    parser.add_argument("--council-model-type", default="mlp")
    parser.add_argument("--skip-council", action="store_true")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--evaluation-dataset", default="benchmark_v1_test")
    parser.add_argument("--decision-policy", default="hybrid_all")
    parser.add_argument("--value-weight", type=float, default=0.4)
    parser.add_argument("--policy-weight", type=float, default=0.6)
    parser.add_argument("--policy-top-k", type=int, default=None)
    parser.add_argument("--routing-context", default=None, help="JSON string routing context overrides.")
    parser.add_argument("--min-improvement", type=float, default=0.005)
    parser.add_argument("--output-root", default="data/training_loop")
    parser.add_argument("--promote", action="store_true", help="Promote improved models to checkpoints.")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    checkpoint_manager = CheckpointManager(output_root / "checkpoints")

    base_seed = int(args.seed)
    routing_context: Dict[str, Any] | None = None
    if args.routing_context:
        routing_context = json.loads(args.routing_context)

    for iteration in range(1, args.iterations + 1):
        iteration_seed = base_seed + iteration - 1
        iteration_root = output_root / f"iter_{iteration:03d}"
        iteration_root.mkdir(parents=True, exist_ok=True)

        simulated_path = iteration_root / "simulated.jsonl"
        sim_config = SimulationConfig(
            scenarios_root=Path(args.scenarios_root),
            num_scenarios=int(args.episodes),
            seed=iteration_seed,
            alignment_weight=float(args.alignment_weight),
            output_path=simulated_path,
            category_weights=Path(args.category_weights) if args.category_weights else None,
        )
        run_simulation(sim_config)

        training_root = iteration_root / "models"
        train_config = TrainingConfig(
            train_mode=str(args.train_mode),
            simulated_path=simulated_path,
            scenarios_root=Path(args.scenarios_root),
            output_root=training_root,
            policy_model_type=args.policy_model_type,
            value_model_type=args.value_model_type,
            council_model_type=args.council_model_type,
            backend=args.backend,
            model_name=args.model_name,
            st_local_only=bool(args.st_local_only),
            test_size=float(args.test_size),
            seed=iteration_seed,
            benchmark_share=float(args.benchmark_share),
            skip_council=bool(args.skip_council),
        )
        artifacts: ModelArtifacts = train_models(train_config)

        eval_config = EvaluationConfig(
            dataset=args.evaluation_dataset,
            experiment_name=f"loop_iter_{iteration:03d}",
            decision_policy=args.decision_policy,
            policy_model_path=artifacts.policy_model_path,
            value_model_path=artifacts.value_model_path,
            value_weight=float(args.value_weight),
            policy_weight=float(args.policy_weight),
            policy_top_k=args.policy_top_k,
            runs=1,
            seeds=[iteration_seed],
            routing_context=_build_routing_context(
                base=routing_context,
                council_model_path=artifacts.council_model_path,
                enable_council=not args.skip_council,
            ),
        )
        metrics = run_evaluation(eval_config)

        summary = {
            "iteration": iteration,
            "seed": iteration_seed,
            "simulation": _stringify(asdict(sim_config)),
            "training": _stringify(asdict(train_config)),
            "evaluation": metrics,
        }
        (iteration_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        if args.promote and checkpoint_manager.should_promote(metrics, args.min_improvement):
            checkpoint_manager.promote(artifacts, metrics, iteration=iteration)

        print(
            f"Iteration {iteration}: accuracy={metrics.get('accuracy', 0.0):.4f} "
            f"promoted={args.promote}"
        )


def _build_routing_context(
    *,
    base: Dict[str, Any] | None,
    council_model_path: Path | None,
    enable_council: bool,
) -> Dict[str, Any] | None:
    if not base and not council_model_path:
        return None
    context = dict(base or {})
    if council_model_path and enable_council:
        context.update(
            {
                "council_weight_model_enabled": True,
                "council_weight_model_path": str(council_model_path),
            }
        )
    return context


def _stringify(payload: Dict[str, Any]) -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, Path):
            output[key] = str(value)
        else:
            output[key] = value
    return output


if __name__ == "__main__":
    main()
