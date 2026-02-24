# ERA v1.0 - Frozen Benchmark Report

- Freeze Timestamp (UTC): 2026-02-20T15:15:08Z
- Results Artifact: `evaluation/results/benchmark_results.json`
- Dataset Manifest: `evaluation/benchmark_dataset/dataset_manifest.json`
- Evaluation Mode: Isolation enabled
- Model: `qwen2.5:0.5b`
- Token Cap: `EVAL_NUM_PREDICT=64`

## Dataset Freeze
- Core scenarios (benchmark): 100
- Adversarial scenarios (separate): 5
- Hashes:
  - irreversible.json: `2292d3abd4a1f28d3f405ab026bf1ce8a05a0679ecdb6905cf243c505f6e84c4`
  - emotional.json: `1b468b968fe3b5843f43cc2e967738af44f68b1afa4ae3dad9ff3fd8e623bf12`
  - strategic.json: `82be874871eee270a3e0cf1a2223247b93ea75484eedb198d7d953108b3006b6`
  - long_horizon.json: `7dcca67242fdd27952147cedac45fd6d749af577ac67756709d916bf73ceae75`
  - adversarial.json: `61d1fd90d3873babe5e2be1bb254b7b52a5b5d50cea3b2f1d416358dce2d0194`

## Run Configuration
- Seeds: [42, 99, 123, 7, 314]
- Inferential unit: scenario-level paired comparison (baseline vs council)
- Metrics implementation: detached (`evaluation/metrics/evaluation_metrics.py`)

## Results
- Baseline mean: 0.388000
- Council mean: 0.395733
- Mean lift: 0.007733
- Paired scenarios: 100
- Paired t-statistic: 0.749385
- p-value: 0.455402
- Cohen's d: 0.075316
- Significant at 0.05: False

## Confidence Intervals (95% bootstrap)
- Baseline: [0.379733, 0.396800]
- Council: [0.388267, 0.404000]

## Calibration (Real Confidence Signals)
- Source: council_scenario_confidence_vs_binary_outcome
- Scenarios used: 100
- ECE: 0.551000
- Brier: 0.457200
- Quality: POOR - Significant miscalibration
- Overconfident: True
