# ERA v1.1 - Calibrated Benchmark Report

- Freeze Timestamp (UTC): 2026-02-20T23:52:07Z
- Results Artifact: `evaluation/results/benchmark_results.json`
- Dataset Manifest: `evaluation/benchmark_dataset/dataset_manifest.json`
- Evaluation Mode: Isolation enabled
- Model: `deepseek-r1:8b`
- Token Cap: `EVAL_NUM_PREDICT=256`
- Calibration Layer: Cross-fitted isotonic regression (5 folds)

## Dataset Freeze
- Core scenarios (benchmark): 100
- Adversarial scenarios (separate): 5
- Hashes:
  - irreversible.json: `2292d3abd4a1f28d3f405ab026bf1ce8a05a0679ecdb6905cf243c505f6e84c4`
  - emotional.json: `1b468b968fe3b5843f43cc2e967738af44f68b1afa4ae3dad9ff3fd8e623bf12`
  - strategic.json: `82be874871eee270a3e0cf1a2223247b93ea75484eedb198d7d953108b3006b6`
  - long_horizon.json: `7dcca67242fdd27952147cedac45fd6d749af577ac67756709d916bf73ceae75`
  - adversarial.json: `61d1fd90d3873babe5e2be1bb254b7b52a5b5d50cea3b2f1d416358dce2d0194`

## Decision Quality (Unchanged Protocol)
- Baseline mean: 0.729333
- Council mean: 0.880000
- Mean lift: 0.150667
- Paired scenarios: 100
- Paired t-statistic: 11.897234
- p-value: 8.5117e-21
- Cohen's d: 1.195717
- Significant at 0.05: True

## Confidence Intervals (95% bootstrap)
- Baseline: [0.720533, 0.738133]
- Council: [0.871193, 0.889333]

## Calibration (Before vs After)
- Raw ECE: 0.449300
- Raw Brier: 0.445939
- Isotonic ECE: 0.097537
- Isotonic Brier: 0.239806
- ECE improvement: 0.351763
- Brier improvement: 0.206133
- Raw quality: POOR - Significant miscalibration
- Isotonic quality: GOOD - Reasonably calibrated

## Notes
- Calibration layer changes confidence reliability only; decision outputs and scoring rubric remain unchanged.
- Isotonic model parameters are stored in `benchmark_results.json` under `calibration.isotonic_regression.model`.
