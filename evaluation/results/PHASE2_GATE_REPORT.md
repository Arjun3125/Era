# Phase 2 Gate Report

- Evaluated UTC: 2026-03-01T13:12:30Z
- Candidate Timestamp: 2026-03-01T13:00:40Z
- Decision: **PASS**

## Checks
- core_lift_absolute: PASS
  - threshold: 0.0792
  - actual: 0.13166666666666682
  - reason: Core lift must meet configured minimum.
- ood_negative_lift_eliminated: PASS
  - threshold: 0.02
  - actual: 0.03333333333333344
  - reason: OOD lift must meet configured minimum.
- core_effect_size: PASS
  - threshold: 0.7
  - actual: 1.1578898544961025
  - reason: Core effect size must meet configured minimum.
- no_calibration_collapse: PASS
  - threshold: candidate_ece <= baseline/raw(+tol)
  - actual: {'mode': 'self_sanity_vs_raw', 'candidate_ece': 0.22739239926739924, 'candidate_brier': 0.1394444088039555, 'raw_ece': 0.6325, 'raw_brier': 0.547134375, 'tolerance': 0.02}
  - reason: Calibrated reliability must not regress.
- no_minister_collapse: PASS
  - threshold: max_mean_weight < 0.85
  - actual: {'gating_enabled': False, 'max_mean_weight': None, 'note': 'check_skipped_gating_disabled'}
  - reason: No single minister should dominate average gating weights.
