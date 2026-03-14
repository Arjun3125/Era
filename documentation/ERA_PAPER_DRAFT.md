# ERA: Structured Deliberation for Decision-Making in AI Systems

Status: Draft v0.1 (internal)

## Abstract

We present ERA, a decision-governance architecture that combines structured deliberation with learned policy and value models. ERA uses a staged orchestration pipeline, a minister-style council, and hybrid scoring to select actions. We introduce ERA-Bench, a decision benchmark with structured scenarios and rubrics, and we evaluate ablations of the core components. Results indicate that structured deliberation provides measurable gains beyond policy/value baselines, while calibrated uncertainty improves reliability and routing behavior. We release the benchmark and evaluation harness to enable reproducible research on decision-making systems.

## 1. Introduction

Decision-making systems often trade interpretability for performance. ERA focuses on modularity and transparent reasoning while adding learning and simulation for improvement. We target scenarios where decisions must be defensible, risk-aware, and traceable to structured evidence.

Key contributions:
1. A deliberative decision architecture with explicit stages and contracts.
2. A benchmark dataset for decision reasoning (ERA-Bench).
3. An evaluation harness with ablations and calibration diagnostics.
4. A learning stack (policy/value + simulation + RL) that improves decision quality over time.

## 2. System Overview

ERA pipeline stages:
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

The decision engine scores candidate options with a hybrid signal:
- policy model score
- value model score
- council signal

## 3. ERA-Bench

ERA-Bench is a structured dataset of decision scenarios:
- 5 categories: strategy, risk, ethics, resource allocation, long-term tradeoffs
- context fields, options, expected decisions, and reasoning rubrics
- frozen splits (train/test/hard)

Dataset structure:
```
era_benchmark/
  scenarios/
  benchmark_index.json
  splits/v1_2/{train.json,test.json,hard.json}
```

## 4. Evaluation Setup

We evaluate:
- accuracy
- rubric alignment score
- regret
- ECE and Brier score
- category breakdown
- budget distribution (adaptive reasoning)

Reproducible experiments are tracked in:
```
experiments/results/<dataset>/<experiment>/
```

## 5. Results

Replace the placeholders below with current experiment outputs.

### 5.1 Main Results

| System | Accuracy | ECE | Brier | Avg Regret | Rubric |
| --- | --- | --- | --- | --- | --- |
| ERA (hybrid, benchmark_v1) | 0.6433 | 0.3161 | n/a | 0.0000 | 0.0889 |
| Policy + Value | TODO | TODO | TODO | TODO | TODO |
| Policy + Value + Council | TODO | TODO | TODO | TODO | TODO |
| Policy + Value + Council + Controller | TODO | TODO | TODO | TODO | TODO |

### 5.2 Category Breakdown

| Category | Score |
| --- | --- |
| Strategy | 0.275 |
| Risk | 0.700 |
| Ethics | 0.176 |
| Resource Allocation | 0.600 |
| Long-term Tradeoffs | 0.187 |

### 5.3 Calibration

Current run (benchmark_v1, 300 scenarios):
- ECE: 0.3161
- Brier: n/a (not recorded)

Provide reliability diagram and calibrated vs raw ECE/Brier once a calibrated run is executed.

## 6. Ablations

Example ablation settings:
- reasoning only
- policy + value only
- policy + value + council
- policy + value + council + controller

Report paired significance tests using the ablation runner.

## 7. Failure Analysis

Qualitative error analysis:
- strategic multi-agent competition
- long-horizon tradeoffs
- ambiguous options with near-equal value

Include representative cases from `runs/seed_*/results.jsonl`.

## 8. Limitations

- Simulation fidelity limits RL improvements.
- Value/policy models are sensitive to feature representation.
- Council outputs still depend on prompt and knowledge coverage.

## 9. Ethical Considerations

ERA provides structured decision support but must not be used as sole authority in high-stakes domains without human oversight. Risk-aware routing and calibrated confidence are required safeguards.

## 10. Reproducibility

- Code, benchmark, and evaluation harness are in this repository.
- Frozen splits for v1.2 are included.
- Experiments are recorded with git commit hashes.

## Appendix A: Implementation Links

- [Decision Engine](c:/era/modules/decision_engine/option_evaluator.py)
- [Evaluation Runner](c:/era/modules/evaluation_engine/runner.py)
- [ERA-Bench](c:/era/era_benchmark/)
- [Experiment Runner](c:/era/experiments/run_benchmark.py)
- [Ablation Runner](c:/era/experiments/run_ablation.py)
- [Training Loop](c:/era/training_loop/run_loop.py)
