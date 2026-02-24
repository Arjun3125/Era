# Phase 2 Gate Report

- Evaluated UTC: 2026-02-23T06:00:32Z
- Candidate Timestamp: 2026-02-23T04:55:00Z
- Decision: **REVERT**

## Checks
- core_lift_absolute: FAIL
  - threshold: 0.05
  - actual: 0.041066666666666696
  - reason: Core lift must improve by at least +5% absolute.
- ood_negative_lift_eliminated: FAIL
  - threshold: 0.0
  - actual: -0.03200000000000014
  - reason: OOD lift must be non-negative.
- core_effect_size: FAIL
  - threshold: 0.5
  - actual: 0.35010490251536486
  - reason: Core effect size must be at least 0.5.
- no_calibration_collapse: PASS
  - threshold: candidate <= baseline(+tol) or <= raw(+tol)
  - actual: {'mode': 'self_sanity_vs_raw', 'candidate_ece': 0.054322278627588344, 'candidate_brier': 0.0854207688319255, 'raw_ece': 0.7298, 'raw_brier': 0.6134679999999999, 'tolerance': 0.0}
  - reason: Calibrated reliability must not regress.

## Failed Checks
- core_lift_absolute
- ood_negative_lift_eliminated
- core_effect_size
