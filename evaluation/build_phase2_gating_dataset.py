#!/usr/bin/env python
"""
Build offline minister-level gating datasets from a split.

Supports controlled synthetic perturbations to increase routing samples.
No model training is performed here.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from evaluation.gating_support import (
    FEATURE_VERSION,
    MINISTER_ORDER,
    build_gating_features,
    compute_regret_adjusted_target,
    fetch_ollama_embedding,
    parse_minister_outputs,
    scenario_text_for_embedding,
)
from evaluation.run_phase2_robustness import (
    Phase2Runner,
    configure_phase2_env,
    load_split_selection,
)
from evaluation.scoring.outcome_scorer import OutcomeScorer
from evaluation.scoring.rubric_engine import RubricEngine


def _union_ids(split_ids: Dict[str, set[str]], include_ood: bool) -> set[str]:
    target = set()
    for key in ("core", "adversarial"):
        target.update(split_ids.get(key, set()))
    if include_ood:
        target.update(split_ids.get("ood", set()))
    return target


def _minister_default_record() -> Dict[str, Any]:
    return {
        "path": "",
        "confidence": 0.5,
        "reason": "",
        "score": 0.0,
        "path_matched": False,
    }


def _variant_templates() -> List[Tuple[str, str]]:
    return [
        (
            "rephrase_contextual",
            "Reframe this scenario with explicit constraints and unknowns:\n{input}",
        ),
        (
            "rephrase_structured",
            "Decision brief:\nSituation: {input}\nNeed: a robust path under uncertainty.",
        ),
        (
            "rephrase_counterfactual",
            "Counterfactual framing: if first instincts are wrong, what path remains safest?\n{input}",
        ),
        (
            "adversarial_pressure",
            "Assume strategic manipulation and hidden incentives are present.\n{input}",
        ),
        (
            "adversarial_urgency",
            "An external actor is forcing urgency and incomplete information.\n{input}",
        ),
        (
            "ood_domain_shift",
            "Treat this as a domain-shifted problem where past patterns may fail.\n{input}",
        ),
        (
            "ood_sparse_signal",
            "Signals are sparse, noisy, and potentially non-stationary.\n{input}",
        ),
    ]


def _build_variants(
    scenario: Dict[str, Any],
    *,
    augmentations_per_scenario: int,
    include_adversarial_augmentations: bool,
    include_ood_style_augmentations: bool,
) -> List[Tuple[str, str, Dict[str, Any]]]:
    variants: List[Tuple[str, str, Dict[str, Any]]] = [("orig", "none", scenario)]
    if augmentations_per_scenario <= 0:
        return variants

    templates = _variant_templates()
    filtered: List[Tuple[str, str]] = []
    for name, tpl in templates:
        if name.startswith("adversarial_") and not include_adversarial_augmentations:
            continue
        if name.startswith("ood_") and not include_ood_style_augmentations:
            continue
        filtered.append((name, tpl))
    if not filtered:
        filtered = [("rephrase_contextual", "Reframe this scenario:\n{input}")]

    original_input = str(scenario.get("input", "")).strip()
    original_context = str(scenario.get("context", "")).strip()
    for i in range(augmentations_per_scenario):
        name, tpl = filtered[i % len(filtered)]
        scenario_aug = copy.deepcopy(scenario)
        scenario_aug["input"] = tpl.format(input=original_input)
        scenario_aug["context"] = (original_context + " | synthetic_augmentation=" + name).strip()
        variants.append((f"aug{i+1:02d}", name, scenario_aug))
    return variants


def _iter_scenarios(
    scenarios: Iterable[Dict[str, Any]],
    *,
    augmentations_per_scenario: int,
    include_adversarial_augmentations: bool,
    include_ood_style_augmentations: bool,
) -> Iterable[Tuple[str, str, Dict[str, Any], Dict[str, Any]]]:
    for scenario in scenarios:
        scenario_id = str(scenario.get("id", ""))
        for variant_id, variant_type, variant in _build_variants(
            scenario,
            augmentations_per_scenario=augmentations_per_scenario,
            include_adversarial_augmentations=include_adversarial_augmentations,
            include_ood_style_augmentations=include_ood_style_augmentations,
        ):
            yield scenario_id, variant_id, variant_type, variant


def build_dataset(
    *,
    split_manifest: str,
    split_name: str,
    include_ood: bool,
    diversity_prompts: bool,
    augmentations_per_scenario: int,
    include_adversarial_augmentations: bool,
    include_ood_style_augmentations: bool,
    use_embeddings: bool,
    embedding_model: str,
    embedding_timeout_sec: float,
) -> Dict[str, Any]:
    configure_phase2_env()
    split_ids = load_split_selection(split_manifest, split_name)
    selected_ids = _union_ids(split_ids, include_ood=include_ood)

    rubric = RubricEngine(benchmark_dir="evaluation/benchmark_dataset")
    if not rubric.verify_dataset_integrity():
        raise RuntimeError("Dataset integrity verification failed.")
    scenarios_all = rubric.load_all_scenarios()
    scenarios = [scenarios_all[sid] for sid in sorted(selected_ids) if sid in scenarios_all]

    runner = Phase2Runner(
        split_dataset_ids=split_ids,
        split_name=split_name,
        diversity_prompts=diversity_prompts,
    )
    scorer = OutcomeScorer()

    rows: List[Dict[str, Any]] = []
    total_variants = len(scenarios) * (1 + max(0, int(augmentations_per_scenario)))
    processed = 0
    for scenario_id, variant_id, variant_type, scenario in _iter_scenarios(
        scenarios,
        augmentations_per_scenario=augmentations_per_scenario,
        include_adversarial_augmentations=include_adversarial_augmentations,
        include_ood_style_augmentations=include_ood_style_augmentations,
    ):
        processed += 1
        category = scenario.get("category", "")
        rubric_gt = scenario.get("ground_truth_rubric", {}) or {}
        acceptable = rubric_gt.get("acceptable_paths", []) or []

        council_output = runner.council_engine(scenario, ablation=None)
        if len(council_output) == 4:
            final_decision, response, final_conf, _ = council_output
        else:
            final_decision, response, final_conf = council_output
        minister_outputs = parse_minister_outputs(response)

        minister_rows: Dict[str, Dict[str, Any]] = {
            key: _minister_default_record() for key in MINISTER_ORDER
        }
        minister_score_vector: List[float] = []

        for key in MINISTER_ORDER:
            out = minister_outputs.get(key)
            if out is None:
                minister_score_vector.append(0.0)
                continue
            ev = scorer.evaluate_decision(
                scenario_id=scenario_id,
                category=category,
                decision_path=out.path,
                decision_rationale=out.reason or response,
                ground_truth_rubric=rubric_gt,
            )
            minister_rows[key] = {
                "path": out.path,
                "confidence": out.confidence,
                "reason": out.reason,
                "score": float(ev.score),
                "path_matched": bool(ev.path_matched),
            }
            minister_score_vector.append(float(ev.score))

        final_eval = scorer.evaluate_decision(
            scenario_id=scenario_id,
            category=category,
            decision_path=final_decision,
            decision_rationale=response,
            ground_truth_rubric=rubric_gt,
        )

        base_41, structured_input, diagnostics = build_gating_features(
            scenario,
            minister_outputs,
            include_extended_features=True,
            target_dim=None,
        )
        _, gating_50_compat, _ = build_gating_features(
            scenario,
            minister_outputs,
            include_extended_features=False,
            target_dim=50,
        )
        target = compute_regret_adjusted_target(
            final_score=float(final_eval.score),
            path_matched=bool(final_eval.path_matched),
            failure_modes_matched_count=len(final_eval.failure_modes_matched),
            scenario=scenario,
        )

        scenario_embed_text = scenario_text_for_embedding(scenario)
        scenario_embedding_raw: List[float] = []
        if use_embeddings:
            scenario_embedding_raw = fetch_ollama_embedding(
                scenario_embed_text,
                model=embedding_model,
                timeout_sec=embedding_timeout_sec,
            )

        rows.append(
            {
                "row_id": f"{scenario_id}__{variant_id}",
                "scenario_id": scenario_id,
                "variant_id": variant_id,
                "variant_type": variant_type,
                "category": category,
                "split_name": split_name,
                "feature_version": FEATURE_VERSION,
                "acceptable_paths": acceptable,
                "minister_order": MINISTER_ORDER,
                "minister_outputs": minister_rows,
                "minister_score_vector": minister_score_vector,
                "final_decision_path": final_decision,
                "final_confidence": float(final_conf),
                "final_score": float(final_eval.score),
                "final_path_matched": bool(final_eval.path_matched),
                "target_regret_adjusted_outcome": float(target),
                "base_feature_vector_41": base_41,
                "gating_input_structured": structured_input,
                "gating_input_50": gating_50_compat,
                "scenario_text_for_embedding": scenario_embed_text,
                "scenario_embedding_raw": scenario_embedding_raw,
                "diagnostics": diagnostics,
            }
        )
        if processed % 25 == 0 or processed == total_variants:
            print(f"[DATASET] processed {processed}/{total_variants}")

    return {
        "metadata": {
            "split_name": split_name,
            "split_manifest": split_manifest,
            "include_ood": include_ood,
            "diversity_prompts": diversity_prompts,
            "augmentations_per_scenario": augmentations_per_scenario,
            "include_adversarial_augmentations": include_adversarial_augmentations,
            "include_ood_style_augmentations": include_ood_style_augmentations,
            "use_embeddings": use_embeddings,
            "embedding_model": embedding_model if use_embeddings else None,
            "n_rows": len(rows),
            "minister_order": MINISTER_ORDER,
            "feature_version": FEATURE_VERSION,
        },
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase2 gating dataset")
    parser.add_argument(
        "--split-manifest",
        default="evaluation/benchmark_dataset/split_manifest_seed42.json",
    )
    parser.add_argument("--split-name", choices=["train", "val", "test"], required=True)
    parser.add_argument("--include-ood", action="store_true", help="Include OOD IDs in dataset")
    parser.add_argument(
        "--diversity-prompts",
        action="store_true",
        default=True,
        help="Use diversity prompt council output for minister lines",
    )
    parser.add_argument(
        "--augmentations-per-scenario",
        type=int,
        default=0,
        help="Number of synthetic variants per scenario (in addition to original).",
    )
    parser.add_argument(
        "--no-adversarial-augmentations",
        action="store_true",
        help="Disable adversarial-style perturbation templates.",
    )
    parser.add_argument(
        "--no-ood-style-augmentations",
        action="store_true",
        help="Disable OOD-style perturbation templates.",
    )
    parser.add_argument(
        "--use-embeddings",
        action="store_true",
        help="Attach frozen scenario embeddings for downstream PCA reduction.",
    )
    parser.add_argument(
        "--embedding-model",
        default="nomic-embed-text:latest",
        help="Ollama embedding model name.",
    )
    parser.add_argument(
        "--embedding-timeout-sec",
        type=float,
        default=20.0,
        help="Timeout for each embedding request.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Output JSON path (default: evaluation/results/gating_dataset_<split>.json)",
    )
    args = parser.parse_args()

    data = build_dataset(
        split_manifest=args.split_manifest,
        split_name=args.split_name,
        include_ood=args.include_ood,
        diversity_prompts=args.diversity_prompts,
        augmentations_per_scenario=max(0, int(args.augmentations_per_scenario)),
        include_adversarial_augmentations=not args.no_adversarial_augmentations,
        include_ood_style_augmentations=not args.no_ood_style_augmentations,
        use_embeddings=bool(args.use_embeddings),
        embedding_model=str(args.embedding_model),
        embedding_timeout_sec=float(args.embedding_timeout_sec),
    )
    out = Path(
        args.output_json
        if args.output_json
        else f"evaluation/results/gating_dataset_{args.split_name}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved dataset: {out}")
    print(f"Rows: {data['metadata']['n_rows']}")


if __name__ == "__main__":
    main()
