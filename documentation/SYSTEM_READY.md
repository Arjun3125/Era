# ERA System Overview

Status: operational (refactored pipeline only)

This repository is the refactored ERA decision-governance system. The legacy Persona N / synthetic conversation stack is not part of the active runtime path.

## What ERA Does

ERA takes a user prompt plus optional routing context and returns a structured decision with rationale, confidence, and council outputs.

Core stages:
1. Input normalization
2. Runtime config
3. Domain analysis
4. Mode routing (adaptive compute)
5. Knowledge synthesis
6. Council execution
7. Council normalization
8. Prime decision
9. Decision packaging
10. Contract validation + telemetry

## Active Entry Points

- `run_refactored.py` (primary CLI)
- `system_main.py` (compatibility shim)

## Adaptive Compute (Layer 4)

Adaptive mode selection is enabled through a mode controller that maps difficulty signals to a reasoning budget:

budget 0 -> quick
budget 1 -> meeting
budget 2 -> war
budget 3 -> darbar

The controller is wired into `modules/council_router/module.py` and sets `reasoning_budget` in routing context. The reasoning controller converts this budget into actual council depth.

## Learning Layer

ERA uses learned models for hybrid scoring:
- Policy model: `data/policy_model/...`
- Value model: `data/value_model/...`
- Mode controller: `data/mode_controller/...`

Models can be trained using TF-IDF or semantic embeddings (sentence-transformers).

## Decision Environment

One-step simulation:
```
python run_refactored.py --simulate-episodes 3 --scenario-domain startup --seed 7
```

Multi-step simulation (stateful environment):
```
python run_refactored.py --simulate-episodes 2 --simulate-steps 3 --scenario-domain startup --seed 7
```

Long-horizon simulation (persistent world state + shocks):
```
python run_refactored.py --simulate-episodes 2 --simulate-steps 24 --long-horizon --scenario-domain startup --seed 7
```

Long-horizon environment includes persistent slow variables (reputation, product quality, competitor strength),
exogenous shocks, and delayed rewards.

## Benchmarks

ERA-Bench is stored in `era_benchmark/` with 3000 scenarios.

Frozen splits (v1.2):
- `era_benchmark/splits/v1_2/train.json`
- `era_benchmark/splits/v1_2/test.json`
- `era_benchmark/splits/v1_2/hard.json`

Benchmark CLI:
```
python scripts/run_benchmark.py --benchmark era_benchmark
```

Split-aware run:
```
python scripts/run_benchmark.py \
  --benchmark era_benchmark \
  --split-file era_benchmark/splits/v1_2/test.json \
  --split test
```

Hybrid (policy + value + council):
```
python scripts/run_benchmark.py \
  --benchmark era_benchmark \
  --decision-policy hybrid_all \
  --policy-model data/policy_model/model_st_v1 \
  --value-model data/value_model/model_st_v1
```

Adaptive mode controller:
```
python scripts/run_benchmark.py \
  --benchmark era_benchmark \
  --decision-policy hybrid_all \
  --policy-model data/policy_model/model_st_v1 \
  --value-model data/value_model/model_st_v1 \
  --routing-context-file data/mode_controller/routing_context_st_v1.json
```

## Evaluation Infrastructure (Layer 5)

Experiment runner (multi-seed + plots + tracking):
```
python experiments/run_benchmark.py \
  --experiment era_baseline \
  --dataset benchmark_v1_test \
  --runs 3 \
  --seeds 41,42,43
```

Scheduler (batch experiments):
```
python experiments/scheduler.py --config experiments/experiment_config.yaml --max-workers 2
```

Ablation runner:
```
python experiments/run_ablation.py \
  --experiments era_baseline,era_no_council,era_darbar \
  --baseline era_baseline
```

Artifacts are written to `experiments/results/<dataset>/<experiment>/` with:
- `metrics.json`
- `confidence_intervals.json`
- `experiment.json` (config + git hash)
- `runs/seed_<n>/summary.json`
- `runs/seed_<n>/results.jsonl`

## Uncertainty & Calibration (Phase 7)

Fit temperature scaling from a benchmark run:
```
python scripts/calibrate_confidence.py \
  --results experiments/results/benchmark_v1_test/era_baseline/runs/seed_42/results.jsonl \
  --output data/calibration/temperature.json
```

Use calibrated confidence in evaluations:
```
python scripts/run_benchmark.py \
  --benchmark era_benchmark \
  --decision-policy hybrid_all \
  --policy-model data/policy_model/model_st_v1 \
  --value-model data/value_model/model_st_v1 \
  --routing-context '{"calibration_path":"data/calibration/temperature.json"}'
```

Risk score signals are computed from:
- `policy_entropy`
- `value_variance`
- `dissent_level`

These are emitted per decision as `risk_score` and aggregated as `avg_risk_score` in reports.

## Research Paper & Benchmark Release (Phase 8)

- Paper draft: `documentation/ERA_PAPER_DRAFT.md`
- Dataset card: `documentation/ERA_BENCHMARK_CARD.md`
- Release checklist: `documentation/ERA_BENCHMARK_RELEASE.md`

## Continuous Training Loop (Layer 6)

Run a single iterate loop (simulate → train → evaluate):
```
python training_loop/run_loop.py \
  --iterations 1 \
  --episodes 10000 \
  --train-mode simulated \
  --evaluation-dataset benchmark_v1_test \
  --decision-policy hybrid_all \
  --promote
```

Artifacts are written under `data/training_loop/iter_*` and checkpoints under `data/training_loop/checkpoints/`.

## Reinforcement Learning Layer (Phase 6)

On-policy RL training over the stateful decision environment:
```
python training_loop/run_rl.py \
  --episodes 1000 \
  --max-steps 3 \
  --gamma 0.95 \
  --lr-policy 0.05 \
  --lr-value 0.1 \
  --entropy-coef 0.01
```

RL artifacts are written under `data/rl/` (policy/value JSON + metrics).

## PPO Training (Policy Gradient → PPO)

Minimal PPO loop over the long-horizon environment:
```
python training_loop/run_ppo.py \
  --episodes 1000 \
  --max-steps 24 \
  --gamma 0.99 \
  --lam 0.95 \
  --clip 0.2
```

## Notes

- The refactor path is the source of truth. Older Persona N and synthetic conversation docs are archived and not used by ERA.
- Metrics vary by model and dataset version; use the benchmark runner for current numbers.
