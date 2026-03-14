# ERA Benchmark Schema

## File Layout
- `era_benchmark/benchmark_index.json` ? metadata and counts
- `era_benchmark/scenarios/<category>/<id>.json` ? one scenario per file

## Scenario JSON Fields
- `scenario_id` (string): unique ID per scenario (e.g., STRAT_001)
- `category` (enum): strategy | risk | ethics | resource_allocation | long_term_tradeoffs
- `difficulty` (enum): easy | medium | hard | expert
- `title` (string): short label for the scenario
- `prompt` (string): user-facing decision prompt
- `context` (object): structured attributes relevant to the decision
- `decision_options` (array[string]): candidate decisions ERA may take
- `expected_decision` (string): best option according to the rubric
- `reasoning_rubric` (array[string]): key reasoning checkpoints to look for
- `evaluation` (object): `{ decision_weight: float, reasoning_weight: float }`, weights sum to 1.0

## Difficulty Meaning
- easy: obvious best decision
- medium: requires tradeoff analysis
- hard: conflicting objectives
- expert: multi-step strategic reasoning with domain conflict (political/ethical/economic)

## Scoring Guidance
- Decision correctness: 1 if `decision` equals `expected_decision`, else 0
- Reasoning alignment: fraction of rubric items present in ERA reasoning text
- Final score: `decision_weight * decision_correct + reasoning_weight * reasoning_alignment`

## Category Guidance
- strategy: market entry, competitive response, product positioning, partnerships
- risk: supply chain, security, compliance, financial exposure
- ethics: bias, privacy, layoffs, transparency
- resource_allocation: budget, staffing, capacity, prioritization
- long_term_tradeoffs: growth vs stability, innovation vs reliability, reputation vs short-term gain

## Common Context Fields (examples)
- `company_size`: small | mid | large
- `cash_reserve_months`: integer
- `brand_strength`: low | medium | high
- `customer_loyalty`: low | moderate | high
- `regulatory_pressure`: low | medium | high
- `time_pressure_days`: integer
- `urgency_rank`: 1–3
- `growth_outlook`: low | moderate | high
- `stake_level`: low | medium | high
- `reversibility`: low | medium | high
- `decision_horizon_months`: integer
- `industry`: saas | fintech | health | retail | industrial | media
