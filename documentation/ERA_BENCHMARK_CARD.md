# ERA-Bench Dataset Card

## Dataset Summary

ERA-Bench is a structured benchmark of decision scenarios for evaluating decision-making systems. Each scenario includes a prompt, context, options, an expected decision, and a reasoning rubric. The dataset supports evaluation, regression testing, and model training.

## Dataset Structure

```
era_benchmark/
  scenarios/<category>/*.json
  benchmark_index.json
  schema.md
  splits/v1_2/{train.json,test.json,hard.json}
```

## Categories

- strategy
- risk
- ethics
- resource_allocation
- long_term_tradeoffs

## Scenario Schema (fields)

- scenario_id
- category
- difficulty
- prompt
- context
- decision_options
- expected_decision
- reasoning_rubric
- evaluation

See `era_benchmark/schema.md` for the full schema.

## Splits

Frozen split files (v1.2):
- `era_benchmark/splits/v1_2/train.json`
- `era_benchmark/splits/v1_2/test.json`
- `era_benchmark/splits/v1_2/hard.json`

Integrity file:
- `era_benchmark/checksums.json` (SHA-256 for dataset artifacts)

## Intended Use

- Evaluate decision pipelines (accuracy, rubric score, calibration).
- Train policy/value models with structured supervision.
- Regression tests for system changes.

## Out-of-Scope Uses

- Real-world deployment without human review.
- Decisions in regulated or safety-critical domains without validation.

## Known Limitations

- Synthetic scenarios; may not reflect full real-world complexity.
- Reasoning rubric is lexical and may undercount semantic matches.
- Scenario difficulty is heuristic.

## Licensing

Specify a dataset license before public release. Suggested defaults:
- CC BY 4.0 for data + schema
- MIT for code

Update this section once a final license is chosen.

## Citation

See `CITATION.cff` for citation metadata.
