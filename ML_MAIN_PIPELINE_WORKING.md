# ML Module Contribution to Main Pipeline

## Short Answer
Yes. `ml` contributes directly to the main pipeline as the learning/feature/KIS orchestration layer. It is not just an offline experiment folder.

## What `ml` Provides

The `ml` package implements an end-to-end "wisdom learning" stack around decisions:
- Feature extraction from scenarios and constraints.
- KIS scoring and synthesis.
- Learned judgment priors that bias KIS outputs using historical outcomes.
- Outcome recording and feedback-driven training cycles.
- Pattern extraction and retraining utilities.

## Key Components

## 1) Orchestration Core
- File: `ml/ml_orchestrator.py`
- Main class: `MLWisdomOrchestrator`
- Responsibility:
  - Coordinate multiple ML steps in one decision pipeline.
  - Generate structured artifacts for training and post-hoc learning.
  - Record outcomes and run periodic training.

## 2) KIS Engine (ML-side)
- File: `ml/kis/knowledge_integration_system.py`
- Main class: `KnowledgeIntegrationSystem`
- Responsibility:
  - Rank knowledge entries via multi-factor weighting.
  - Produce `KISResult` with synthesized guidance and traces.

## 3) Feature System
- File: `ml/features/feature_extractor.py`
- Responsibility:
  - Build numeric feature vectors from situation/constraints/KIS/action state.
  - Provide canonical feature names (`get_feature_names`) used by evaluation and gating code.

## 4) Judgment Prior
- File: `ml/judgment/ml_judgment_prior.py`
- Main class: `MLJudgmentPrior`
- Responsibility:
  - Learn type-level weighting priors from outcomes.
  - Apply learned adjustments to KIS score distributions.

## 5) Outcome Feedback Data Loop
- File: `ml/outcomes/outcome_recorder.py`
- Main classes:
  - `OutcomeDatabase`
  - `TrainingDataGenerator`
  - `FeedbackIntegrator`
- Responsibility:
  - Persist decision?outcome records.
  - Convert outcomes to training datasets.
  - Execute training cycles and persist trained state.

## 6) Auxiliary Learning Utilities
- `ml/pattern_extraction.py` — extracts trends/signals from memory/outcomes.
- `ml/system_retraining.py` — system-level retraining hooks.
- `ml/minister_retraining.py`, `ml/doctrine_update.py`, `ml/reward_shaping.py`, `ml/vector_memory.py`, `ml/darbar.py` — support modules for advanced adaptation.

## Direct References in Main Code Paths (Non-Document)

## A) Evaluation pipeline
- `evaluation/run_phase2_robustness.py`
  - imports `get_feature_names` from `ml.features.feature_extractor`.
  - Uses ML feature schema to align evaluation/uncertainty/gating inputs.
- `evaluation/gating_support.py`
  - also uses ML feature naming/extraction alignment.

## B) Persona pipeline
- `persona/main.py`
  - imports `PatternExtractor` from `ml.pattern_extraction`.
- `persona/persona_minister_kis_bridge.py`
  - imports ML KIS, feature extractor, and `MLWisdomOrchestrator`.
  - bridges minister flow with ML KIS stack.

## C) Sovereign pipeline
- `sovereign/sovereign_main.py`
  - imports and instantiates `MLWisdomOrchestrator`.
- `sovereign/sovereign_main_integration_example.py`
  - imports `ml.sovereign_orchestrator.SovereignOrchestrator`.

## D) Test and verification ecosystem
Many tests import ML modules directly (`tests/test_step4_training_data.py`, `tests/test_kis_integration.py`, `tests/verify_ml_integration.py`, etc.), indicating active support and contract surface.

## Pipeline Role Assessment

Current role:
- Active support dependency for feature schema and orchestration bridges.
- Active runtime component in sovereign paths.
- Active adaptation layer for learning from outcomes.

Not currently the sole authority for Phase2 scoring:
- Phase2 runner centers around `persona` mode/council runtime.
- But it uses ML feature interfaces and can consume ML-driven signals.

## How `ml` Contributes Practically

1. Standardizes feature space used for evaluation and gating.
2. Supplies KIS + learned prior machinery that can improve decision ranking.
3. Enables persistent outcome-driven improvement loops.
4. Provides adapters to plug learning into persona/sovereign orchestration without rewriting core evaluators.

## Integration Guidance

To keep comparability and control:
1. Keep one evaluator/scorer path (`evaluation/*`) as the source of truth.
2. Use `ml` as a provider of features, priors, and training artifacts.
3. Feed ML outputs into existing control points (uncertainty, KIS weighting, orchestration bridge) rather than creating a parallel scoring pipeline.
4. Version ML artifacts (`models`, thresholds, feature schema) alongside evaluation artifacts for reproducibility.

## Bottom Line

`ml` can and does contribute to the main pipeline. It is a functional learning subsystem that supports feature extraction, KIS ranking, judgment priors, and feedback training, with concrete integration points in evaluation, persona, and sovereign code.
