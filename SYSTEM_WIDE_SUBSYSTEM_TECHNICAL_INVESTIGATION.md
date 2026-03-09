# Repository-Wide Subsystem Technical Investigation (Source/Config Scope)

## Scope Constraints Applied
- Excluded: `documents/` and `documentation/` directories.
- Included: source and configuration artifacts (`.py`, selected config-like `.json`, `.yaml/.yml`, `.toml`, `.ini/.cfg`, `.sql`, model artifacts where directly referenced).
- Excluded generated/runtime artifacts and large data dumps (e.g., `evaluation/results/`, `ingestion/data/`, logs, caches).
- Analysis method: static code parsing (AST for Python), import graph reconstruction, reverse-reference indexing, entrypoint detection, and pipeline-caller tracing.

## Global Dependency Topology (Top-Level Folders)
- `evaluation` depends on -> `ml`, `persona`
- `hse` depends on -> `persona`
- `ingestion` depends on -> `llm`, `ml`, `utils`
- `llm` depends on -> `persona`
- `ml` depends on -> `analytics`, `hse`, `ingestion`, `persona`
- `multi_agent_sim` depends on -> `hse`, `llm`, `persona`
- `persona` depends on -> `hse`, `ml`, `sovereign`
- `scripts` depends on -> `hse`, `ingestion`, `persona`
- `sovereign` depends on -> `hse`, `ml`, `persona`
- `tests` depends on -> `hse`, `ingestion`, `llm`, `ml`, `multi_agent_sim`, `persona`, `sovereign`
- `utils` depends on -> `ml`

---
## Subsystem: `analytics`

### 1. Folder Overview
- Inferred architectural classification: **Monitoring/analytics subsystem**.
- Files in analysis scope: **4**.
- Direct top-level dependencies: none detected in top-level import graph.
- Referenced by other top-level folders: `ml`

### 2. File-by-File Explanation
- `analytics/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `analytics/dashboard.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: PerformanceDashboard
  - Defined functions: __init__, compute_rolling_metrics, generate_weak_feature_alert, suggest_retraining_actions
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `analytics/improvement_tracker.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `analytics/reporting.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **1** Python files.
- Referencing modules:
  - `ml/sovereign_orchestrator.py`
- Primary pipeline callers/controllers importing this subsystem:
  - `ml/sovereign_orchestrator.py`

### 4. Execution Flow Reconstruction
- No direct CLI entrypoint discovered; subsystem executes when imported/called by upstream modules.
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Monitoring/analytics subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented as library/support**
- Evidence: Primarily import-driven modules with limited direct entrypoints.
- Stub/TODO signal count (heuristic): 0

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: would break or degrade dependent subsystems: `ml`

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Connected** (direct imports in primary pipeline files).
- Pipeline position: imported by orchestrator/runner modules listed above; invoked during decision/evaluation flow according to caller logic.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> analytics module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `evaluation`

### 1. Folder Overview
- Inferred architectural classification: **Evaluation/validation subsystem**.
- Files in analysis scope: **51**.
- Direct top-level dependencies: `ml`, `persona`
- Referenced by other top-level folders: no cross-folder imports detected.

### 2. File-by-File Explanation
- `evaluation/MODEL_VERSION.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: __getattr__
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/adversarial_user_simulator.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: AdversarialGeneration, AdversarialUserSimulator
  - Defined functions: __init__, _build_instruction, _stable_index, generate, summarize_rounds
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/analyze_kis_failure_mode.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _domain_for_principle, _iter_council_rows, _load_benchmark_index, _to_float, _top_items, analyze, main, write_markdown
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.scoring.outcome_scorer
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/analyze_minister_similarity.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _collect_stance_vectors, _filter_dataset, _flatten_upper, _safe_pearson, _similarity_matrices, _top_pair_drift, _write_markdown, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.scoring.rubric_engine, persona.council
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/baselines/ERA_v2.0_diversity_baseline/baseline_lock.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/baselines/ERA_v2.0_diversity_baseline/split_manifest_seed42.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/benchmark_dataset/adversarial.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/benchmark_dataset/dataset_manifest.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/benchmark_dataset/emotional.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/benchmark_dataset/irreversible.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/benchmark_dataset/long_horizon.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/benchmark_dataset/ood.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/benchmark_dataset/split_manifest_seed42.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/benchmark_dataset/strategic.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/build_kis2_index.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.kis2_retrieval
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/build_phase2_gating_dataset.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _build_variants, _iter_scenarios, _minister_default_record, _union_ids, _variant_templates, build_dataset, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.gating_support, evaluation.run_phase2_robustness, evaluation.scoring.outcome_scorer, evaluation.scoring.rubric_engine
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/create_split_manifest.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _allocate_counts, _dataset_name_for_category, build_split_manifest, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.scoring.rubric_engine
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/distribution_shift.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ShiftedScenario
  - Defined functions: _sparse_info_transform, _stable_index, _time_pressure_transform, _value_conflict_transform, apply_shift_mode, parse_shift_modes
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/evaluate_phase2_gates.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _ge_with_tol, _get_float, _le_with_tol, _load_json, evaluate_gates, main, write_markdown
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/evaluation_runner.py`
  - Purpose: Control/orchestration module; likely coordinates flow between library modules.
  - Defined classes: EvaluationConfig, EvaluationRunner
  - Defined functions: __init__, _distribution_from_category, _extract_named_value, _extract_uncertainty_signals, _load_model_version, _run_seed, ablation_analysis, compare_runs, enable_isolation_mode, export_results, run_evaluation, to_dict, verify_dataset_integrity
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.gating_support, evaluation.scoring.outcome_scorer, evaluation.scoring.regret_scorer, evaluation.scoring.rubric_engine, evaluation.stats_engine
- `evaluation/freeze_diversity_baseline.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _read_json, _sha256, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/gate_milestone3.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _collect_council_records, _darbar_delta, _load_json, _safe_float, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/gating_model.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: GatingTrainingConfig, MinisterGatingMLP
  - Defined functions: __init__, _eval_stage2, _prior_tensor, _record_input, _stack_records, _stage2_loss_terms, _weight_collapse_stats, forward, load_gating_bundle, logits, save_gating_bundle, train_gating_model
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/gating_support.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: MinisterOutput
  - Defined functions: _clamp, _embed_cache_key, _empty_kis_output, _extract_float, _infer_constraint_state, _infer_situation_state, _normalize_path, apply_pca_reducer, build_gating_features, build_model_input_from_spec, compute_regret_adjusted_target, decision_difficulty_proxy, disagreement_entropy, escalation_pressure_indicator, fetch_ollama_embedding, fit_pca_reducer, irreversibility_score, minister_confidence_variance ...
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.features.feature_extractor
- `evaluation/kis2_retrieval.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: KIS2Config, KIS2Retrieval, _RerankerMLP
  - Defined functions: __init__, _category_code, _clamp01, _cosine_sim_matrix, _domain_match_score, _feature_row, _load_or_build_embeddings, _load_principles, _load_reranker, _rerank_score, build_prompt_block, ensure_default_principles_file, fetch_ollama_embedding, forward, metadata, retrieve, scenario_text_for_embedding
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/learned_uncertainty.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: LearnedUncertaintyPredictor, _UncertaintyMLP
  - Defined functions: __init__, _feature_value, _to_float_or_none, forward, from_json, metadata, predict, threshold_config
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/metrics/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/metrics/evaluation_metrics.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: EvaluationMetrics
  - Defined functions: _predict_isotonic, apply_isotonic_regression, apply_isotonic_regression_crossfit, compute_bootstrap_ci, compute_brier, compute_ece, compute_effect_size, compute_mean, compute_paired_ttest, compute_variance
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/models/phase2_gating_model.meta.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/models/phase2_gating_model_v2_aug4_embed.meta.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/models/phase2_gating_model_v2_aug6_embed.meta.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/models/uncertainty_predictor_compare_semantic.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/models/uncertainty_predictor_compare_semantic_q30.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/models/uncertainty_predictor_compare_strict.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/models/uncertainty_predictor_compare_strict_q30.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/models/uncertainty_predictor_semantic_control_q30.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/models/uncertainty_predictor_semantic_full_q30.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/models/uncertainty_predictor_v1.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `evaluation/red_team_governance.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _mean, inject_governance_attack_text, summarize_governance_metrics
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/reliability_analysis.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _apply_calibrator_to_records, _apply_isotonic_model, _apply_split_lookup, _apply_temperature, _compute_reliability_metrics, _fit_and_select_calibrator, _fit_temperature, _infer_distribution_from_scenario_id, _load_records_from_result, _load_split_lookup, _normalize_record, _plot_reliability, _plot_reliability_svg, _reconstruct_records_from_run_payload, _split_by_distribution, _xml_escape, load_records, main ...
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.metrics.evaluation_metrics
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/run_phase2_robustness.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: Phase2Runner
  - Defined functions: __init__, _ablation_delta, _acquire_run_lock, _apply_ablation, _build_council_prompt, _build_kis2_context, _build_principle_activation_block, _check_runtime, _choose_weighted_decision, _compare_runs, _completion_checks, _compute_percentile, _council_engine_with_governance_redteam, _council_engine_with_self_play, _council_engine_with_shift_mode, _curve_mean, _detect_principle_activation, _estimate_information_ambiguity ...
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.adversarial_user_simulator, evaluation.distribution_shift, evaluation.evaluation_runner, evaluation.gating_model, evaluation.gating_support, evaluation.kis2_retrieval, evaluation.learned_uncertainty, evaluation.metrics.evaluation_metrics, evaluation.red_team_governance, evaluation.scoring.outcome_scorer, ml.features.feature_extractor, persona.modes.mode_orchestrator ...
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/run_phase2_with_gates.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: assert_ollama_available, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.create_split_manifest, evaluation.evaluate_phase2_gates, evaluation.run_phase2_robustness
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/run_phase4_stress.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _build_phase2_cmd, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/scoring/outcome_scorer.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: OutcomeScorer, RubricEvaluation
  - Defined functions: __init__, _build_justification, _check_path_match, _extract_principles, _extract_principles_rule_based, _extract_principles_semantic, _match_failure_modes, _principle_name_token_match, evaluate_decision, get_results_summary
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/scoring/regret_scorer.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: RegretScore, RegretScorer
  - Defined functions: __init__, get_summary, score_regret
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/scoring/rubric_engine.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/stats_engine.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ConfidenceInterval, StatsEngine
  - Defined functions: __init__, _interpret_power_grid, ablation_effect_size, aggregate_seed_results, bootstrap_paired_test, calibration_curve, calibration_diagnostics, compute_confidence_intervals, compute_power_analysis, paired_t_test, power_grid_analysis
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `evaluation/train_kis2_reranker.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: Reranker
  - Defined functions: __init__, _to_matrix, forward, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/train_phase2_gating.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _attach, _hyper_grid, _load_rows, _prepare_model_inputs, _row_structured_input, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): evaluation.gating_model, evaluation.gating_support
  - Execution trigger: contains `__main__` guard and is directly executable.
- `evaluation/uncertainty_analysis.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: _UncertaintyMLP
  - Defined functions: __init__, _apply_derived_uncertainty_signals, _apply_split_lookup, _auc_quality_label, _binary_metrics, _bucket_metrics, _build_feature_matrix, _compute_high_error_labels, _compute_u, _control_thresholds, _default_embedding_dataset_paths, _extract_primitives, _extract_records_from_run_payload, _feature_value, _has_any_uncertainty_signal, _infer_distribution_from_scenario_id, _kmeans, _load_embedding_lookup ...
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **10** Python files.
- Referencing modules:
  - `evaluation/analyze_kis_failure_mode.py`
  - `evaluation/analyze_minister_similarity.py`
  - `evaluation/build_kis2_index.py`
  - `evaluation/build_phase2_gating_dataset.py`
  - `evaluation/create_split_manifest.py`
  - `evaluation/evaluation_runner.py`
  - `evaluation/reliability_analysis.py`
  - `evaluation/run_phase2_robustness.py`
  - `evaluation/run_phase2_with_gates.py`
  - `evaluation/train_phase2_gating.py`
- Primary pipeline callers/controllers importing this subsystem:
  - `evaluation/evaluation_runner.py`
  - `evaluation/run_phase2_robustness.py`
  - `evaluation/run_phase2_with_gates.py`
  - `run_benchmark.py`

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `evaluation/analyze_kis_failure_mode.py`
  - `evaluation/analyze_minister_similarity.py`
  - `evaluation/build_kis2_index.py`
  - `evaluation/build_phase2_gating_dataset.py`
  - `evaluation/create_split_manifest.py`
  - `evaluation/evaluate_phase2_gates.py`
  - `evaluation/freeze_diversity_baseline.py`
  - `evaluation/gate_milestone3.py`
  - `evaluation/reliability_analysis.py`
  - `evaluation/run_phase2_robustness.py`
  - `evaluation/run_phase2_with_gates.py`
  - `evaluation/run_phase4_stress.py`
  - `evaluation/train_kis2_reranker.py`
  - `evaluation/train_phase2_gating.py`
  - `evaluation/uncertainty_analysis.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Evaluation/validation subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented with active entrypoints**
- Evidence: Multiple executable entrypoints exist; subsystem appears operational.
- Stub/TODO signal count (heuristic): 6

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: limited direct breakage inferred at import layer; verify dynamic loading paths if any.

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Connected** (direct imports in primary pipeline files).
- Pipeline position: imported by orchestrator/runner modules listed above; invoked during decision/evaluation flow according to caller logic.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> evaluation module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `hse`

### 1. Folder Overview
- Inferred architectural classification: **Simulation and stress-testing subsystem**.
- Files in analysis scope: **11**.
- Direct top-level dependencies: `persona`
- Referenced by other top-level folders: `ml`, `multi_agent_sim`, `persona`, `scripts`, `sovereign`, `tests`

### 2. File-by-File Explanation
- `hse/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `hse/analytics_server.py`
  - Purpose: Control/orchestration module; likely coordinates flow between library modules.
  - Defined classes: none
  - Defined functions: event_stream, index, start_server, stream, stream_metrics
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `hse/crisis_injector.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: CrisisInjector
  - Defined functions: __init__, maybe_inject
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `hse/human_profile.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: SyntheticHuman
  - Defined functions: __getitem__, __init__, __setitem__, build_user_prompt, generate_context, get, profile
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `hse/personality_drift.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: PersonalityDrift
  - Defined functions: __init__, _create_bias, _mutate_trait, apply
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `hse/population_manager.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: PopulationManager, SyntheticHuman
  - Defined functions: __init__, apply_drift, create, generate_context, get, list_ids, profile, save_state, snapshot
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `hse/simulation/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `hse/simulation/bidirectional_simulation.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: BidirectionalSimulation
  - Defined functions: __init__, _build_human_profile, _generate_final_report, _generate_persona_response, _generate_user_input, _human_state_snapshot, _maybe_inject_crisis, _maybe_switch_mode, _print_final_summary, _print_turn_summary, _record_episode, _sync_human_object, _update_human_state, _update_metrics, run_conversation, save_report
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): hse.crisis_injector, hse.human_profile, hse.personality_drift, persona.context, persona.learning.episodic_memory, persona.state
- `hse/simulation/human_persona_adapter.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: HumanPersonaAdaptation
  - Defined functions: __init__, detect_challenge_behavior, measure_advice_adoption, measure_trust_trajectory
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `hse/simulation/stress_orchestrator.py`
  - Purpose: Control/orchestration module; likely coordinates flow between library modules.
  - Defined classes: StressScenarioOrchestrator
  - Defined functions: __init__, _inject_stage, measure_stress_response_quality, run_compounding_crisis
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `hse/simulation/synthetic_human_sim.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: SyntheticHumanSimulation
  - Defined functions: __init__, apply_consequences, call_llm, generate_next_input
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): hse.crisis_injector, hse.human_profile, hse.personality_drift

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **10** Python files.
- Referencing modules:
  - `hse/simulation/bidirectional_simulation.py`
  - `hse/simulation/synthetic_human_sim.py`
  - `ml/sovereign_orchestrator.py`
  - `multi_agent_sim/simulation_runner.py`
  - `persona/main.py`
  - `scripts/stream_persona_live.py`
  - `sovereign/sovereign_main.py`
  - `tests/test_features.py`
  - `tests/verification/test_ml_layer.py`
  - `tests/verification/verify_and_run.py`
- Primary pipeline callers/controllers importing this subsystem:
  - `ml/sovereign_orchestrator.py`
  - `persona/main.py`
  - `sovereign/sovereign_main.py`

### 4. Execution Flow Reconstruction
- No direct CLI entrypoint discovered; subsystem executes when imported/called by upstream modules.
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Simulation and stress-testing subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented as library/support**
- Evidence: Primarily import-driven modules with limited direct entrypoints.
- Stub/TODO signal count (heuristic): 3

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: would break or degrade dependent subsystems: `ml`, `multi_agent_sim`, `persona`, `scripts`, `sovereign`, `tests`

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Connected** (direct imports in primary pipeline files).
- Pipeline position: imported by orchestrator/runner modules listed above; invoked during decision/evaluation flow according to caller logic.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> hse module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `ingestion`

### 1. Folder Overview
- Inferred architectural classification: **Data/knowledge processing support subsystem**.
- Files in analysis scope: **38**.
- Direct top-level dependencies: `llm`, `ml`, `utils`
- Referenced by other top-level folders: `ml`, `scripts`, `tests`

### 2. File-by-File Explanation
- `ingestion/v1/ingest.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _ministers_progress_cb, chunk_text, classify_chapter, dedupe_list, doctrine_density, doctrine_to_nodes, extract_doctrine, extract_pdf_pages, extract_text_universal, extract_texts_from_doc, extract_with_ocr, extract_with_pdfminer, extract_with_pypdf, fallback_split_by_headings, flush_buffer, has_actionable_doctrine, infer_domains_from_text, ingest_folder ...
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): llm
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v1/llm.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: OllamaClient
  - Defined functions: __init__, _ministers_progress_cb, _run, build_minister_memories, call_json_llm_strict, classify_chapter, doctrine_density, doctrine_to_nodes, embed, embed_nodes, extract_doctrine, extract_text_universal, extract_with_ocr, generate, has_actionable_doctrine, infer_domains_from_text, ingest_folder, is_doctrine_structurally_valid ...
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/data/memory_db_stub.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `ingestion/v2/run_all_v2_ingest.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: validate_paths
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/scripts/generate_chapters_fallback.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.chapter_splitter, ingestion.v2.src.pdf_extraction
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/ASYNC_PIPELINE_GUIDE.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/adaptive_controller.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: AdaptiveConfig, AdaptiveController, PipelineMetrics, RateLimit, TokenBucket
  - Defined functions: __init__, __post_init__, _evaluate_feedback, _refill, current_tokens, get_metrics, record_processing, reset_metrics, set_rate_multiplier, to_dict, update_queue_depth
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/async_doctrine_workers.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _extract
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/async_ingest_config.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: Chunk
  - Defined functions: to_db_tuple
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/async_ingest_orchestrator.py`
  - Purpose: Control/orchestration module; likely coordinates flow between library modules.
  - Defined classes: AsyncIngestionPipeline
  - Defined functions: __init__
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/async_ingestion_orchestrator.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: AsyncIngestionOrchestrator, IngestionJob, IngestionMetrics, IngestionPhase
  - Defined functions: __init__, __post_init__, get_all_jobs, get_job_status, get_orchestrator_metrics, success_rate, throughput, to_dict
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/async_workers.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _call
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/benchmark_harness.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: BenchmarkHarness, BenchmarkPhase, BenchmarkResult, BenchmarkSuite
  - Defined functions: __init__, add_result, avg_processing_time, get_measurement_results, get_results_by_phase, max_processing_time, median_processing_time, min_processing_time, p95_processing_time, p99_processing_time, print_summary, save, save_results, success_rate, throughput_items_per_sec, to_dict, to_json
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/capital_allocation.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ScoreBundle
  - Defined functions: _cosine, commit_memory, decision_gate, doctrine_diff, ingest_post_phase3, optimize_retrieval_indices, reinforce_feedback, score_event, weighted_sum
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/chapter_splitter.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: fallback_split_by_headings, flush_buffer, split_chapters_with_ollama_streaming
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): .utils
- `ingestion/v2/src/config.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/demo_async_pipeline.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: stub_parse_func
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/distributed_queue.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: BaseQueue, InMemoryQueue, QueuedItem, RedisQueue
  - Defined functions: __init__, __post_init__, can_retry, create_queue, to_dict
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/doctrine_extractor.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _extract_chunk_doctrine, _has_actionable_doctrine, _is_doctrine_structurally_valid, extract_doctrine, extract_texts_from_doc, reject_verbatim_quotes_inline, validate_doctrine_inline
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): .utils
- `ingestion/v2/src/embeddings.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: doctrine_to_nodes, embed_nodes, normalize_doctrine
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): .utils
- `ingestion/v2/src/ingest_metrics.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: IngestMetrics
  - Defined functions: get_avg_db_latency, get_avg_embed_latency, get_avg_minister_latency, get_throughput, print_report, processed_chunks, record_db, record_dropped, record_embed, record_error, record_minister, record_processed, record_rate_limit, report
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/ingest_pipeline.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _enrich_doctrines, _is_ingest_completed, _ministers_progress_cb, _parse_chunks_from_file, _try_reconstruct_doctrine, build_minister_memories, classify_chapter, doctrine_density, ingest_folder, phase2_progress, phase_3_5_progress_cb, run_full_ingest_with_resume
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): .utils
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/ingest_workers.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: PipelineOrchestrator, PipelineWorker, WorkerMetrics, WorkerPool, WorkerStage
  - Defined functions: __init__, add_stage, get_all_metrics, get_metrics, record_item, to_dict
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/ingestion_config.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: AdaptiveControllerPresets, EnvironmentConfig, HighThroughput, Local, RateLimitPresets, Standard, WorkerPoolConfig
  - Defined functions: create_orchestrator_config, get_adaptive_config, get_environment_config, get_full_config
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/ingestion_kis_enhancer.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: IngestionKISContext, IngestionKISEnhancer
  - Defined functions: __init__, create_kis_enhanced_worker_wrapper, enhance_aggregation_stage, enhance_minister_doctrine, get_ingestion_statistics, record_ingestion_failure, record_ingestion_success, save_ingestion_logs, to_dict
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.kis.knowledge_integration_system, ml.ml_orchestrator
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/integration_examples.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: IngestionConfig
  - Defined functions: __init__, convert_existing_parser, dummy_parser, from_json, to_json, wrapper
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/memory_db.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: MemoryDB
  - Defined functions: __init__, _ensure_stub, _read, _write, adjust_attention_priors, adjust_entity_weights, create_doctrine_patch, get_recent_embeddings, init_schema, insert_embedding, insert_memory, recompute_cluster_centroids, retrieve_related_beliefs, store_doctrine_version, update_memory_salience, update_topk_cache
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/minister_converter.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: add_category_entry, convert_all_doctrines, ensure_minister_structure, process_chapter_doctrine, update_combined_vector_index
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/minister_vector_db.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: MinisterVectorDB
  - Defined functions: __init__, close, connect, init_schema, insert_combined_embedding, search_by_domain, search_combined
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/ollama_client.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: OllamaClient
  - Defined functions: __init__, call_json_llm_strict, embed, generate
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/pdf_extraction.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: extract_pdf_pages, looks_glyph_encoded, repair_glyph_text
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/progress_tracker.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: live_progress, update_progress
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/quickstart.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ingestion/v2/src/rate_controller.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: AdaptiveRateController
  - Defined functions: __init__, _update_semaphore, adjust, get_status, record_error, record_rate_limit, record_success, release
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/utils.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: chunk_text, dedupe_list, infer_domains_from_text, is_glyph_stream, looks_glyph_encoded, sha, text_quality_score
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/vector_db.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: VectorDBStub
  - Defined functions: __init__, _cosine, _read, _write, insert_combined, insert_combined_batch, insert_domain, insert_domain_batch, search_combined, search_domain, validate_domain
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ingestion/v2/src/verify_installation.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **14** Python files.
- Referencing modules:
  - `ingestion/v2/scripts/generate_chapters_fallback.py`
  - `ml/llm_handshakes/llm_interface.py`
  - `scripts/check_embed.py`
  - `scripts/run_embed_only.py`
  - `tests/debug_kis_ingestion.py`
  - `tests/run_kis_integration_test.py`
  - `tests/test_async_embed.py`
  - `tests/test_async_embed_debug.py`
  - `tests/test_direct_ingest.py`
  - `tests/test_kis_enhancement_direct.py`
  - `tests/test_kis_exact_scenario.py`
  - `tests/test_kis_integration.py`
  - `tests/verification/verify_improvements.py`
  - `tests/verify_kis_integration.py`
- Primary pipeline caller imports: no direct imports in selected primary pipeline files.

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `ingestion/v1/ingest.py`
  - `ingestion/v1/llm.py`
  - `ingestion/v2/run_all_v2_ingest.py`
  - `ingestion/v2/scripts/generate_chapters_fallback.py`
  - `ingestion/v2/src/ASYNC_PIPELINE_GUIDE.py`
  - `ingestion/v2/src/adaptive_controller.py`
  - `ingestion/v2/src/async_ingestion_orchestrator.py`
  - `ingestion/v2/src/benchmark_harness.py`
  - `ingestion/v2/src/demo_async_pipeline.py`
  - `ingestion/v2/src/distributed_queue.py`
  - `ingestion/v2/src/ingest_pipeline.py`
  - `ingestion/v2/src/ingest_workers.py`
  - `ingestion/v2/src/ingestion_config.py`
  - `ingestion/v2/src/ingestion_kis_enhancer.py`
  - `ingestion/v2/src/integration_examples.py`
  - `ingestion/v2/src/quickstart.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Data/knowledge processing support subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Partially implemented / experimental**
- Evidence: High stub/TODO signal density suggests active or incomplete areas.
- Stub/TODO signal count (heuristic): 115

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: would break or degrade dependent subsystems: `ml`, `scripts`, `tests`

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Not directly connected to primary pipeline imports** in selected core runner files.
- Likely role: support, optional tooling, or validation helper; may still be indirectly used through dependent modules.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> ingestion module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `llm`

### 1. Folder Overview
- Inferred architectural classification: **ML/Model support and inference subsystem**.
- Files in analysis scope: **5**.
- Direct top-level dependencies: `persona`
- Referenced by other top-level folders: `ingestion`, `multi_agent_sim`, `tests`

### 2. File-by-File Explanation
- `llm/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `llm/interactive_llm_conversation.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: LLMPersona, LLMUser
  - Defined functions: __init__, generate_next_input, main, print_header, print_turn, respond
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.context, persona.ollama_runtime, persona.state
  - Execution trigger: contains `__main__` guard and is directly executable.
- `llm/interactive_persona_chat.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: interactive_chat
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.state
  - Execution trigger: contains `__main__` guard and is directly executable.
- `llm/ollama.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: chat, list
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `llm/ollama_model_selector.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: list_models, select_models
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **6** Python files.
- Referencing modules:
  - `ingestion/v1/ingest.py`
  - `multi_agent_sim/run_terminal.py`
  - `tests/run_phase1_test.py`
  - `tests/sovereign_stress_test.py`
  - `tests/test_split.py`
  - `tests/test_split_qwen25.py`
- Primary pipeline caller imports: no direct imports in selected primary pipeline files.

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `llm/interactive_llm_conversation.py`
  - `llm/interactive_persona_chat.py`
  - `llm/ollama_model_selector.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **ML/Model support and inference subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented with active entrypoints**
- Evidence: Multiple executable entrypoints exist; subsystem appears operational.
- Stub/TODO signal count (heuristic): 0

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: would break or degrade dependent subsystems: `ingestion`, `multi_agent_sim`, `tests`

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Not directly connected to primary pipeline imports** in selected core runner files.
- Likely role: support, optional tooling, or validation helper; may still be indirectly used through dependent modules.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> llm module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `Memory`

### 1. Folder Overview
- Inferred architectural classification: **Data/knowledge processing support subsystem**.
- Files in analysis scope: **2**.
- Direct top-level dependencies: none detected in top-level import graph.
- Referenced by other top-level folders: no cross-folder imports detected.

### 2. File-by-File Explanation
- `Memory/pwm.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _call_llm, decide_commits, extract_signals, generate_hypotheses, render_template, score_confidence, session_summary, translate_to_db_changes
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `Memory/schema.sql`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **0** Python files.
- Primary pipeline caller imports: no direct imports in selected primary pipeline files.

### 4. Execution Flow Reconstruction
- No direct CLI entrypoint discovered; subsystem executes when imported/called by upstream modules.
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Data/knowledge processing support subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented as library/support**
- Evidence: Primarily import-driven modules with limited direct entrypoints.
- Stub/TODO signal count (heuristic): 0

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: limited direct breakage inferred at import layer; verify dynamic loading paths if any.

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Not directly connected to primary pipeline imports** in selected core runner files.
- Likely role: support, optional tooling, or validation helper; may still be indirectly used through dependent modules.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> Memory module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `ml`

### 1. Folder Overview
- Inferred architectural classification: **ML/Model support and inference subsystem**.
- Files in analysis scope: **30**.
- Direct top-level dependencies: `analytics`, `hse`, `ingestion`, `persona`
- Referenced by other top-level folders: `evaluation`, `ingestion`, `persona`, `sovereign`, `tests`, `utils`

### 2. File-by-File Explanation
- `ml/QUICKSTART.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: example_1_basic_kis, example_2_features_and_labels, example_3_ml_learning, example_4_orchestrator, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.features.feature_extractor, ml.judgment.ml_judgment_prior, ml.kis.knowledge_integration_system, ml.labels.label_generator, ml.ml_orchestrator
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ml/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/cache/ingestion_kis_logs.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `ml/cache/outcomes/outcome_index.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `ml/cache/training_datasets/training_dataset_20260215_041612.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `ml/darbar.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: darbar_debate
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/doctrine_update.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/features/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/features/feature_extractor.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ActionState, ActionType, Agency, ConstraintState, DecisionType, KISOutput, OutcomeState, RiskLevel, SituationState, TimeHorizon
  - Defined functions: build_feature_vector, clamp, extract_action_features, extract_constraint_features, extract_knowledge_features, extract_situation_features, feature_vector_to_list, get_feature_names, safe_divide
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/judgment/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/judgment/ml_judgment_prior.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: MLJudgmentPrior, MLModelState
  - Defined functions: __init__, add_training_sample, apply_ml_bias, compute_situation_hash, load, predict_prior, reset, save, train
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/kis/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/kis/knowledge_integration_system.py`
  - Purpose: Integration adapter module bridging subsystems.
  - Defined classes: KISRequest, KISResult, KnowledgeEntry, KnowledgeIntegrationSystem, KnowledgeType
  - Defined functions: __init__, _empty_result, compute_context_weight, compute_domain_weight, compute_goal_weight, compute_memory_weight, compute_type_weight, extract_keywords, load_builtin_entries, load_knowledge_entries, synthesize_knowledge, to_dict
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/labels/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/labels/label_generator.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: TypeWeights
  - Defined functions: assess_severity, build_training_row, clamp, compute_label_certainty, generate_type_weights, interpret_outcome, log_label_decision, summarize_knowledge_usage, to_dict, to_list
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/llm_handshakes/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/llm_handshakes/llm_interface.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ConstraintExtractionOutput, CounterfactualOption, CounterfactualSketchOutput, IntentDetectionOutput, LLMInterface, SituationFrameOutput
  - Defined functions: __init__, call_1_situation_framing, call_2_constraint_extraction, call_3_counterfactual_sketch, call_4_intent_detection, call_llm, run_handshake_sequence
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.config, ingestion.v2.src.ollama_client
- `ml/minister_retraining.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/ml_orchestrator.py`
  - Purpose: Control/orchestration module; likely coordinates flow between library modules.
  - Defined classes: MLWisdomOrchestrator
  - Defined functions: __init__, _assess_quality, _avg_kis_by_type, _extract_features_from_llm, _extract_kis_features, load_session, process_decision, process_interaction, record_outcome, run_training_cycle, save_session
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/outcomes/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/outcomes/outcome_recorder.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: FeedbackIntegrator, OutcomeDatabase, TrainingDataGenerator
  - Defined functions: __init__, _generate_decision_key, _load_index, _save_index, _save_trained_model, apply_learned_weights, generate_training_dataset, get_all_decisions_with_outcomes, get_decision, get_statistics, record_decision, record_outcome, run_training_cycle, save_training_dataset
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/pattern_extraction.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: PatternExtractor
  - Defined functions: __init__, _avg_strength, _compute_pattern_stats, _extract_confidence_patterns, _extract_domain_patterns, _extract_outcome_patterns, _extract_sequential_patterns, extract_patterns, generate_learning_signals, identify_weak_patterns, save_patterns
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/quick_test_ml.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.domain_detector, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.ollama_runtime, persona.session_manager
- `ml/reward_shaping.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: reward_function
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/sovereign_orchestrator.py`
  - Purpose: Control/orchestration module; likely coordinates flow between library modules.
  - Defined classes: SovereignOrchestrator
  - Defined functions: __init__, _correct_mode_violation, _force_correction_with_acknowledgment, _generate_report, apply_ablation_config, attach_pwm, enable_evaluation_mode, get_state_snapshot, initialize_synthetic_human, run_turn
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): analytics.dashboard, hse.simulation.human_persona_adapter, hse.simulation.stress_orchestrator, hse.simulation.synthetic_human_sim, ml.system_retraining, persona.learning.confidence_model, persona.learning.consequence_engine, persona.learning.episodic_memory, persona.learning.failure_analysis, persona.learning.outcome_feedback_loop, persona.learning.performance_metrics, persona.modes.mode_orchestrator ...
- `ml/system_retraining.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: SystemRetraining
  - Defined functions: __init__, encode_learned_doctrine, extract_success_patterns, rebalance_kis_weights, retrain_llm_if_local, update_minister_confidence_formulas
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/test_ml_learning_loop.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: demonstrate_pattern_query, test_learning_processor
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ml/tests/__init__.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `ml/tests/test_ml_wisdom.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: TestEndToEnd, TestFeatureExtraction, TestKISWeights, TestLabelGeneration, TestMLJudgmentPrior
  - Defined functions: setUp, test_advice_led_failure_penalizes_advice, test_build_feature_vector_bounds, test_context_weight_keyword_matching, test_domain_weight_active, test_domain_weight_inactive, test_execution_success_boosts_rules, test_extract_constraint_features, test_extract_situation_features, test_kis_respects_max_items, test_kis_synthesis_nonempty, test_learning_from_successes, test_memory_weight_logarithmic, test_model_persistence, test_neutral_before_training, test_severe_failure_boosts_warnings, test_type_weight_ranges, test_weights_stay_bounded
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `ml/vector_memory.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: VectorMemory
  - Defined functions: __init__, add, search
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **24** Python files.
- Referencing modules:
  - `evaluation/gating_support.py`
  - `evaluation/run_phase2_robustness.py`
  - `ingestion/v2/src/ingestion_kis_enhancer.py`
  - `ml/QUICKSTART.py`
  - `ml/sovereign_orchestrator.py`
  - `persona/main.py`
  - `persona/persona_minister_kis_bridge.py`
  - `sovereign/sovereign_main.py`
  - `sovereign/sovereign_main_integration_example.py`
  - `tests/run_adapter_test.py`
  - `tests/run_kis_integration_test.py`
  - `tests/sovereign_stress_test.py`
  - `tests/test_features.py`
  - `tests/test_kis_enhancement_direct.py`
  - `tests/test_kis_integration.py`
  - `tests/test_llm_client.py`
  - `tests/test_llm_kis_integration.py`
  - `tests/test_step3_simple.py`
  - `tests/test_step4_training_data.py`
  - `tests/verification/test_ml_layer.py`
  - `tests/verification/verify_and_run.py`
  - `tests/verify_llm_implementation.py`
  - `tests/verify_ml_integration.py`
  - `utils/ML_WISDOM_INTEGRATION_GUIDE.py`
- Primary pipeline callers/controllers importing this subsystem:
  - `evaluation/run_phase2_robustness.py`
  - `ml/sovereign_orchestrator.py`
  - `persona/main.py`
  - `sovereign/sovereign_main.py`

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `ml/QUICKSTART.py`
  - `ml/test_ml_learning_loop.py`
  - `ml/tests/test_ml_wisdom.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **ML/Model support and inference subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented with active entrypoints**
- Evidence: Multiple executable entrypoints exist; subsystem appears operational.
- Stub/TODO signal count (heuristic): 4

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: would break or degrade dependent subsystems: `evaluation`, `ingestion`, `persona`, `sovereign`, `tests`, `utils`

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Connected** (direct imports in primary pipeline files).
- Pipeline position: imported by orchestrator/runner modules listed above; invoked during decision/evaluation flow according to caller logic.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> ml module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `multi_agent_sim`

### 1. Folder Overview
- Inferred architectural classification: **Simulation and stress-testing subsystem**.
- Files in analysis scope: **10**.
- Direct top-level dependencies: `hse`, `llm`, `persona`
- Referenced by other top-level folders: `tests`

### 2. File-by-File Explanation
- `multi_agent_sim/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `multi_agent_sim/__main__.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `multi_agent_sim/agents.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: BaseAgent, MockAgent, OllamaAgent
  - Defined functions: __init__, _call_ollama, respond
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `multi_agent_sim/archetypes.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `multi_agent_sim/demo.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: demo_with_mocks
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `multi_agent_sim/logger.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ConversationLogger
  - Defined functions: __init__, append, clear, get_transcript
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `multi_agent_sim/orchestrator.py`
  - Purpose: Control/orchestration module; likely coordinates flow between library modules.
  - Defined classes: Orchestrator
  - Defined functions: __init__, _build_program_prompt, _build_user_prompt, run
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `multi_agent_sim/run_terminal.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): llm.ollama_model_selector
  - Execution trigger: contains `__main__` guard and is directly executable.
- `multi_agent_sim/simulation_runner.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: DryRunLLM
  - Defined functions: __init__, _load_dotenv_fallback, _load_env, main, speak
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): hse.human_profile, hse.simulation, persona.council, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.ollama_runtime
  - Execution trigger: contains `__main__` guard and is directly executable.
- `multi_agent_sim/terminal.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: call_model, check_ollama_available, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **4** Python files.
- Referencing modules:
  - `tests/advanced_persona_test_suite.py`
  - `tests/comprehensive_feature_test.py`
  - `tests/comprehensive_persona_test_suite.py`
  - `tests/master_test_orchestrator.py`
- Primary pipeline caller imports: no direct imports in selected primary pipeline files.

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `multi_agent_sim/__main__.py`
  - `multi_agent_sim/demo.py`
  - `multi_agent_sim/run_terminal.py`
  - `multi_agent_sim/simulation_runner.py`
  - `multi_agent_sim/terminal.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Simulation and stress-testing subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented with active entrypoints**
- Evidence: Multiple executable entrypoints exist; subsystem appears operational.
- Stub/TODO signal count (heuristic): 11

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: would break or degrade dependent subsystems: `tests`

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Not directly connected to primary pipeline imports** in selected core runner files.
- Likely role: support, optional tooling, or validation helper; may still be indirectly used through dependent modules.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> multi_agent_sim module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `persona`

### 1. Folder Overview
- Inferred architectural classification: **Core engine (primary runtime decision system)**.
- Files in analysis scope: **43**.
- Direct top-level dependencies: `hse`, `ml`, `sovereign`
- Referenced by other top-level folders: `evaluation`, `hse`, `llm`, `ml`, `multi_agent_sim`, `scripts`, `sovereign`, `tests`

### 2. File-by-File Explanation
- `persona/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/analysis.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _heuristic_domain_guess, _normalize_float, _safe_parse_json, assess_coherence, assess_emotional_metrics, assess_mode_fitness, assess_situation, assess_situation_heuristic, classify_domains, generate_clarifying_questions
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/brain.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ControlDirective, PersonaBrain
  - Defined functions: decide
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/cache_manager.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: CacheManager
  - Defined functions: __init__, cleanup_by_size, cleanup_old_files, get_cache_report, get_cache_size, main, print_report, run_cleanup, validate_cache_dirs
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `persona/clarify.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _trace_event, build_clarifying_question, format_question_for_user
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/context.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: build_system_context, enforce_frequency, estimate_user_frequency, trim_response
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/council.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: CouncilAggregator, CouncilRecommendation
  - Defined functions: __init__, convene
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/council/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _load_legacy_council
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/council/dynamic_council.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: DynamicCouncil
  - Defined functions: __init__, _convene_mode_council, _determine_recommendation, convene_for_mode, get_current_mode, get_mode_description, list_available_modes, set_mode
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/doctrine_loader.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: DoctrinalCanon, DoctrineLoader
  - Defined functions: extract_warnings, extract_worldview_keywords, load, should_speak_based_on_doctrine
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/domain_detector.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: analyze_situation, analyze_with_llm, detect_domains_by_keywords, detect_reversibility, detect_stakes, domain_similarity, extract_key_entities, extract_keywords_from_text
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/knowledge_engine.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _clean_book_name, _detect_contradictions, _semantic_label_similarity, applies_applicability, apply_ml_judgment_prior, compute_kis, context_weight, domain_weight, extract_keywords, generate_diagnosis_counterfactual_synthesis, goal_weight, load_domain_knowledge, load_json_safe, memory_weight, synthesize_knowledge
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/learning/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/learning/confidence_model.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: BayesianConfidence
  - Defined functions: __init__, get_confidence, get_uncertainty, summary, update
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/learning/consequence_engine.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ConsequenceEngine
  - Defined functions: __init__, _estimate_severity, register_decision, tick
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/learning/episodic_memory.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: Episode, EpisodicMemory
  - Defined functions: __init__, __post_init__, _persist, detect_failure_clusters, detect_pattern_repetition, find_similar_episodes, get_recent_episodes, get_success_rate, load_from_disk, record_consequence, store_episode
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/learning/failure_analysis.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: FailureAnalysis
  - Defined functions: __init__, _analyze_kis_error, _analyze_minister_error, _consensus_was_flawed, analyze_failure
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/learning/outcome_feedback.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: OutcomeFeedbackLoop
  - Defined functions: __init__, detect_repeated_mistake, record_decision_outcome, retrain_ministers, update_kis_weights
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/learning/outcome_feedback_loop.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: OutcomeFeedbackLoop
  - Defined functions: __init__, _adjust_ministers, _update_doctrine_effectiveness, doctrine_report, record_decision_outcome, retrain_ministers, update_kis_weights
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/learning/performance_metrics.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: PerformanceMetrics
  - Defined functions: __init__, _persist, detect_weak_domains, get_feature_coverage, get_success_rate, load_from_disk, measure_stability, record_decision, show_improvement_trajectory
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/main.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _background_analysis, _mca_decision, main, validate_mode_coherence
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): hse.human_profile, hse.simulation.synthetic_human_sim, ml.pattern_extraction, sovereign.llm_adapter, sovereign.prime_confident
  - Execution trigger: contains `__main__` guard and is directly executable.
- `persona/ministers.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: Minister, MinisterOfAdaptation, MinisterOfConflict, MinisterOfData, MinisterOfDiplomacy, MinisterOfDiscipline, MinisterOfGrandStrategy, MinisterOfIntelligence, MinisterOfLegitimacy, MinisterOfNarrative, MinisterOfOptionality, MinisterOfPower, MinisterOfPsychology, MinisterOfRisk, MinisterOfRiskResources, MinisterOfSovereign, MinisterOfTechnology, MinisterOfTiming, MinisterOfTribunal, MinisterOfTruth, MinisterOfWarMode, MinisterPosition
  - Defined functions: __init__, _apply_prohibitions, _extract_stance_confidence, _score_worldview_match, analyze
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/modes/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/modes/mode_metrics.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ModeMetrics
  - Defined functions: __init__, compare_modes, get_all_modes, get_best_mode, get_mode_performance, get_mode_summary, get_worst_mode, has_data_for_mode, record_mode_decision, reset_all, reset_mode
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/modes/mode_orchestrator.py`
  - Purpose: Control/orchestration module; likely coordinates flow between library modules.
  - Defined classes: DarbarModeStrategy, ExecutionConfig, MeetingModeStrategy, ModeOrchestrator, ModeResponse, ModeStrategy, QuickModeStrategy, UncertaintyPolicyConfig, WarModeStrategy
  - Defined functions: __init__, _clamp01, aggregate_for_mode, aggregate_minister_inputs, apply_uncertainty_control, compute_composite_uncertainty, decide_ministers_to_invoke, frame_decision, frame_for_mode, get_current_mode, get_execution_plan, get_ministers_for_mode, get_mode_description, get_strategy, is_baseline_mode, list_modes, set_ablation_config, set_mode ...
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/ollama_runtime.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: OllamaRuntime
  - Defined functions: __init__, _extract_text, analyze, analyze_async, speak, speak_async
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/persistence/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/persistence/conversation_arc.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ConversationArc
  - Defined functions: __init__, _is_conflicting, detect_decision_contradiction, detect_unresolved_loop, get_long_horizon_impact, record_decision, register_crisis, register_issue_reference, resolve_crisis, set_original_problem, track_decision_consequences
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/persistence/memory_store.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/persona_learning_processor.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: ConversationLearningProcessor
  - Defined functions: __init__, _analyze_conversation_quality, _analyze_domain_effectiveness, _extract_metrics, _extract_question_patterns, _generate_next_session_recommendations, _identify_weak_domains, _persist_learning, _print_learning_summary, _suggest_pattern, get_learned_patterns_for_domain, process_conversation, process_conversation_for_learning
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `persona/persona_minister_kis_bridge.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: MinisterKISBridge
  - Defined functions: __init__, export_minister_logs, get_learning_summary, get_minister_context, get_minister_knowledge, minister_usage_example, record_minister_decision, record_outcome
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.features.feature_extractor, ml.kis.knowledge_integration_system, ml.ml_orchestrator
  - Execution trigger: contains `__main__` guard and is directly executable.
- `persona/pwm_integration/__init__.py`
  - Purpose: Integration adapter module bridging subsystems.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/pwm_integration/pwm_bridge.py`
  - Purpose: Integration adapter module bridging subsystems.
  - Defined classes: PWMIntegrationBridge
  - Defined functions: __init__, _commit_fact_to_pwm, _group_by_entity, _validate_entity_observations, _validate_single_observation, generate_validation_insights, get_pwm_facts_for_entity, get_validation_history, periodic_pwm_sync, queue_entity_observation, summary
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/run_persona.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _load_dotenv_fallback
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.main
  - Execution trigger: contains `__main__` guard and is directly executable.
- `persona/run_persona_conversation.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.main
- `persona/session_manager.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: Session, SessionManager, SessionTurn
  - Defined functions: __init__, _generate_session_id, _load_history, _save_session, add_turn, create_followup_session, end_session, find_related_sessions, get_session_context_for_continuity, get_session_statistics, load_consequences_for_session, record_consequence, record_satisfaction, should_escalate_mode, start_session, to_dict
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.domain_detector
- `persona/state.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: CognitiveState
  - Defined functions: add_turn, get_recent_context, reset_for_new_conversation, update_domains
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/test_session_workflow.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: test_consequence_tracking, test_domain_detection, test_session_continuity, test_session_management, test_statistics
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.domain_detector, persona.session_manager
  - Execution trigger: contains `__main__` guard and is directly executable.
- `persona/trace.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: _append_trace, print_trace, trace
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/validation/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/validation/contradiction_detector.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/validation/identity_validator.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: IdentityValidator
  - Defined functions: __init__, _extract_claims, _find_contradiction, check_self_contradiction, log_contradiction, record_teaching, validate_voice_consistency
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `persona/validation/mode_validator.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ModeValidator
  - Defined functions: __init__, detect_mode_drift, inconsistency_score, mode_stability_score, record_mode, validate_response_mode_match
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **54** Python files.
- Referencing modules:
  - `evaluation/analyze_minister_similarity.py`
  - `evaluation/run_phase2_robustness.py`
  - `hse/simulation/bidirectional_simulation.py`
  - `llm/interactive_llm_conversation.py`
  - `llm/interactive_persona_chat.py`
  - `ml/quick_test_ml.py`
  - `ml/sovereign_orchestrator.py`
  - `multi_agent_sim/simulation_runner.py`
  - `persona/run_persona.py`
  - `persona/run_persona_conversation.py`
  - `persona/session_manager.py`
  - `persona/test_session_workflow.py`
  - `scripts/stream_persona_live.py`
  - `sovereign/llm_adapter.py`
  - `sovereign/ministers/__init__.py`
  - `sovereign/ministers/adaptation.py`
  - `sovereign/ministers/conflict.py`
  - `sovereign/ministers/data.py`
  - `sovereign/ministers/diplomacy.py`
  - `sovereign/ministers/discipline.py`
  - `sovereign/ministers/grand_strategist.py`
  - `sovereign/ministers/intelligence.py`
  - `sovereign/ministers/legitimacy.py`
  - `sovereign/ministers/meeting_flow.py`
  - `sovereign/ministers/narrative.py`
  - `sovereign/ministers/optionality.py`
  - `sovereign/ministers/orchestrator.py`
  - `sovereign/ministers/power.py`
  - `sovereign/ministers/psychology.py`
  - `sovereign/ministers/risk.py`
  - `sovereign/ministers/risk_minister.py`
  - `sovereign/ministers/risk_resources.py`
  - `sovereign/ministers/sovereign.py`
  - `sovereign/ministers/technology.py`
  - `sovereign/ministers/timing.py`
  - `sovereign/ministers/tribunal.py`
  - `sovereign/ministers/truth.py`
  - `sovereign/ministers/war_mode.py`
  - `sovereign/prime_confident.py`
  - `tests/advanced_persona_test_suite.py`
  - `tests/comprehensive_feature_test.py`
  - `tests/comprehensive_persona_test_suite.py`
  - `tests/master_test_orchestrator.py`
  - `tests/test_features.py`
  - `tests/verification/quick_verify.py`
  - `tests/verification/test_ml_layer.py`
  - `tests/verification/test_persona_simple.py`
  - `tests/verification/test_startup.py`
  - `tests/verification/verify_all_features.py`
  - `tests/verification/verify_and_run.py`
  - `tests/verification/verify_improvements.py`
  - `tests/verification/verify_llm_integration.py`
  - `tests/verify_api_fixes.py`
  - `tests/verify_ml_integration.py`
- Primary pipeline callers/controllers importing this subsystem:
  - `evaluation/run_phase2_robustness.py`
  - `ml/sovereign_orchestrator.py`
  - `run_benchmark.py`

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `persona/cache_manager.py`
  - `persona/main.py`
  - `persona/persona_learning_processor.py`
  - `persona/persona_minister_kis_bridge.py`
  - `persona/run_persona.py`
  - `persona/test_session_workflow.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Core engine (primary runtime decision system)**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented with active entrypoints**
- Evidence: Multiple executable entrypoints exist; subsystem appears operational.
- Stub/TODO signal count (heuristic): 24

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: would break or degrade dependent subsystems: `evaluation`, `hse`, `llm`, `ml`, `multi_agent_sim`, `scripts`, `sovereign`, `tests`

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Connected** (direct imports in primary pipeline files).
- Pipeline position: imported by orchestrator/runner modules listed above; invoked during decision/evaluation flow according to caller logic.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> persona module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `scripts`

### 1. Folder Overview
- Inferred architectural classification: **Operational tooling/support module**.
- Files in analysis scope: **12**.
- Direct top-level dependencies: `hse`, `ingestion`, `persona`
- Referenced by other top-level folders: no cross-folder imports detected.

### 2. File-by-File Explanation
- `scripts/STARTUP_GUIDE.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `scripts/VISUAL_SUMMARY.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: print_banner, print_files_created, print_improvement_example, print_quick_start, print_result, print_storage, print_verification, print_what_happens
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `scripts/check_embed.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.ollama_client
- `scripts/check_ingestion_status.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `scripts/check_models.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `scripts/check_ollama_api.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `scripts/check_requirements.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `scripts/convert_markdown_to_docx.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _add_code_paragraph, _write_markdown_block, convert_markdown_files_to_docx, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `scripts/ingest_status.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `scripts/run_embed_only.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.async_ingest_orchestrator, ingestion.v2.src.config, ingestion.v2.src.ingest_pipeline, ingestion.v2.src.ollama_client
  - Execution trigger: contains `__main__` guard and is directly executable.
- `scripts/scan_rag_storage.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: summarize_doctrine
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `scripts/stream_persona_live.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: append_log, call_user_model, main, safe_print
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): hse.human_profile, persona.context, persona.ollama_runtime, persona.state
  - Execution trigger: contains `__main__` guard and is directly executable.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **0** Python files.
- Primary pipeline caller imports: no direct imports in selected primary pipeline files.

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `scripts/STARTUP_GUIDE.py`
  - `scripts/VISUAL_SUMMARY.py`
  - `scripts/convert_markdown_to_docx.py`
  - `scripts/run_embed_only.py`
  - `scripts/stream_persona_live.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Operational tooling/support module**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented with active entrypoints**
- Evidence: Multiple executable entrypoints exist; subsystem appears operational.
- Stub/TODO signal count (heuristic): 1

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: limited direct breakage inferred at import layer; verify dynamic loading paths if any.

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Not directly connected to primary pipeline imports** in selected core runner files.
- Likely role: support, optional tooling, or validation helper; may still be indirectly used through dependent modules.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> scripts module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `sovereign`

### 1. Folder Overview
- Inferred architectural classification: **Orchestration/integration application layer**.
- Files in analysis scope: **33**.
- Direct top-level dependencies: `hse`, `ml`, `persona`
- Referenced by other top-level folders: `persona`, `tests`

### 2. File-by-File Explanation
- `sovereign/council/aggregator.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: CouncilAggregator
  - Defined functions: __init__, evaluate
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `sovereign/llm_adapter.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: OllamaAdapter
  - Defined functions: __init__, analyze, analyze_async, evaluate_viability, generate, speak, speak_async, summarize
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ollama_runtime, persona.trace
- `sovereign/ministers/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: MinisterModule, MinisterModuleOutput
  - Defined functions: __init__, analyze, create_minister_module, generate_kis, invoke_with_prime
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.knowledge_engine, persona.ministers, persona.trace
- `sovereign/ministers/adaptation.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: AdaptationModule
  - Defined functions: __init__, generate_kis, get_adaptation_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/base_minister.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: BaseMinister
  - Defined functions: __init__, produce_advice
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `sovereign/ministers/conflict.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: ConflictModule
  - Defined functions: __init__, generate_kis, get_conflict_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/data.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: DataModule
  - Defined functions: __init__, generate_kis, get_data_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/diplomacy.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: DiplomacyModule
  - Defined functions: __init__, generate_kis, get_diplomacy_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/discipline.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: DisciplineModule
  - Defined functions: __init__, generate_kis, get_discipline_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/examples.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: example_individual_minister, example_judge_observation, example_kis_analysis, example_orchestrator_all_ministers, example_with_prime_confident
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): sovereign.ministers.adaptation, sovereign.ministers.data, sovereign.ministers.orchestrator, sovereign.ministers.tribunal, sovereign.prime_confident
  - Execution trigger: contains `__main__` guard and is directly executable.
- `sovereign/ministers/grand_strategist.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: GrandStrategyModule
  - Defined functions: __init__, generate_kis, get_grand_strategy_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/intelligence.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: IntelligenceModule
  - Defined functions: __init__, generate_kis, get_intelligence_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/legitimacy.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: LegitimacyModule
  - Defined functions: __init__, generate_kis, get_legitimacy_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/meeting_flow.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: DebateOutput, MeetingSynthesis, MinisterSelection, TopicCategory
  - Defined functions: execute_minister_analysis, meeting_mode_flow, select_ministers_for_topic, synthesize_meeting_debate
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.knowledge_engine, persona.trace
- `sovereign/ministers/narrative.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: NarrativeModule
  - Defined functions: __init__, generate_kis, get_narrative_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/optionality.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: OptionalityModule
  - Defined functions: __init__, generate_kis, get_optionality_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/orchestrator.py`
  - Purpose: Control/orchestration module; likely coordinates flow between library modules.
  - Defined classes: MinisterFlowOrchestrator, MinisterFlowResult
  - Defined functions: __init__, _execute_darbar_mode, _execute_meeting_mode, _get_attr, execute_ministers, get_orchestrator, invoke_prime_confident
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.council, persona.trace
- `sovereign/ministers/power.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: PowerModule
  - Defined functions: __init__, generate_kis, get_power_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/psychology.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: PsychologyModule
  - Defined functions: __init__, generate_kis, get_psychology_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/risk.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: RiskModule
  - Defined functions: __init__, generate_kis, get_risk_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/risk_minister.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: RiskMinister
  - Defined functions: __init__, produce_advice
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.knowledge_engine
- `sovereign/ministers/risk_resources.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: RiskResourcesModule
  - Defined functions: __init__, generate_kis, get_risk_resources_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/sovereign.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: SovereignModule
  - Defined functions: __init__, generate_kis, get_sovereign_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/technology.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: TechnologyModule
  - Defined functions: __init__, generate_kis, get_technology_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/timing.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: TimingModule
  - Defined functions: __init__, generate_kis, get_timing_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/tribunal.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: TribunalModule
  - Defined functions: __init__, generate_kis, get_tribunal_module, invoke_with_prime
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/truth.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: TruthModule
  - Defined functions: __init__, generate_kis, get_truth_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/ministers/war_mode.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: WarModeModule
  - Defined functions: __init__, generate_kis, get_war_mode_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.ministers
- `sovereign/prime_confident.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: PrimeConfident
  - Defined functions: __init__, _analyze_emotional_distortion, _apply_doctrine_constraints, _detect_pattern_recurrence, decide
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.doctrine_loader, persona.trace
- `sovereign/runtime/council_runtime.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: CouncilRuntime, MockMinister
  - Defined functions: __init__, advice, run
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): sovereign.council.aggregator, sovereign.prime_confident
  - Execution trigger: contains `__main__` guard and is directly executable.
- `sovereign/runtime/minister_runtime.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: MinisterRuntime
  - Defined functions: __init__, activate_ministers, register_minister
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `sovereign/sovereign_main.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: call_model, run_instance
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): hse.analytics_server, hse.crisis_injector, hse.human_profile, hse.personality_drift, hse.population_manager, ml.ml_orchestrator
  - Execution trigger: contains `__main__` guard and is directly executable.
- `sovereign/sovereign_main_integration_example.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: generate_persona_response, main_simulation_loop
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.sovereign_orchestrator
  - Execution trigger: contains `__main__` guard and is directly executable.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **5** Python files.
- Referencing modules:
  - `persona/main.py`
  - `sovereign/ministers/examples.py`
  - `sovereign/runtime/council_runtime.py`
  - `tests/test_features.py`
  - `tests/verify_api_fixes.py`
- Primary pipeline callers/controllers importing this subsystem:
  - `persona/main.py`

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `sovereign/ministers/examples.py`
  - `sovereign/runtime/council_runtime.py`
  - `sovereign/sovereign_main.py`
  - `sovereign/sovereign_main_integration_example.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Orchestration/integration application layer**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented with active entrypoints**
- Evidence: Multiple executable entrypoints exist; subsystem appears operational.
- Stub/TODO signal count (heuristic): 1

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: would break or degrade dependent subsystems: `persona`, `tests`

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Connected** (direct imports in primary pipeline files).
- Pipeline position: imported by orchestrator/runner modules listed above; invoked during decision/evaluation flow according to caller logic.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> sovereign module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `tests`

### 1. Folder Overview
- Inferred architectural classification: **Evaluation/validation subsystem**.
- Files in analysis scope: **62**.
- Direct top-level dependencies: `hse`, `ingestion`, `llm`, `ml`, `multi_agent_sim`, `persona`, `sovereign`
- Referenced by other top-level folders: no cross-folder imports detected.

### 2. File-by-File Explanation
- `tests/advanced_persona_test_suite.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: AdvancedPersonaAgent, AdvancedTestSuite, TestMetrics
  - Defined functions: __init__, print_results, respond, run_all, test, test_domain, test_domain_accumulation, test_edge, test_emotion, test_orchestration, test_response, test_state_persistence, test_strategy, test_telemetry, user_behavior
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): multi_agent_sim.agents, multi_agent_sim.logger, multi_agent_sim.orchestrator, persona.brain, persona.state
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/check_extraction.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/check_kis_in_doctrine.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/comprehensive_feature_test.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: FeatureTestAgent, QuickPersonaAgent
  - Defined functions: __init__, main, print_section, respond, test_feature_1_state_management, test_feature_2_domain_detection, test_feature_3_emotional_intelligence, test_feature_4_persona_brain, test_feature_5_system_context, test_feature_6_conversation_logging, test_feature_7_orchestration, test_feature_8_trace_observability, test_feature_9_combined_suite, user_behavior
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): multi_agent_sim.agents, multi_agent_sim.logger, multi_agent_sim.orchestrator, persona.brain, persona.context, persona.ollama_runtime, persona.state, persona.trace
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/comprehensive_persona_test_suite.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: ComprehensivePersonaAgent, DynamicTestCaseGenerator, RigorousTestSuite, SuiteResult, TestResult
  - Defined functions: __init__, _aggregate_results, add_result, generate_decision_scenarios, generate_domain_scenarios, generate_edge_cases, generate_emotional_scenarios, generate_learning_scenarios, generate_report, pass_rate, print_detailed_report, respond, run_all_tests, summary, test_decision_directives, test_domain_classification, test_edge_cases, test_emotional_intelligence ...
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): multi_agent_sim.agents, multi_agent_sim.logger, multi_agent_sim.orchestrator, persona.brain, persona.context, persona.knowledge_engine, persona.state
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/conftest.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: era_root, ingestion_dir, pytest_collection_modifyitems, pytest_configure, rag_storage_dir, temp_test_dir, test_data_dir
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/debug_kis_ingestion.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.ingestion_kis_enhancer
- `tests/master_test_orchestrator.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: MasterTestOrchestrator, TestPersonaAgent
  - Defined functions: __init__, _create_persona_agent, _extract_domains, _generate_report, _get_emotional_intensity, _print_summary, _save_reports, _test_agent_creation, _test_basic_functionality, _test_basic_response, _test_domain_classification, _test_edge_cases, _test_emotional_intelligence, _test_kis_features, _test_multi_agent_integration, _test_persona_modes, _test_response_generation, _test_state_init ...
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): multi_agent_sim.agents, multi_agent_sim.logger, multi_agent_sim.orchestrator, persona.brain, persona.state
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/pytest.ini`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `tests/run_adapter_test.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.ml_orchestrator
- `tests/run_kis_integration_test.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: check_doctrine_kis_guidance, check_kis_logs, check_ml_learning, cleanup_phase3, main, run_ingestion
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.ingest_pipeline, ml.ml_orchestrator
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/run_phase1_test.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): llm
- `tests/run_tests.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: TestRunner
  - Defined functions: __init__, _execute_command, generate_report, main, run_all_tests, run_by_marker, run_unit_tests_only, run_verification_only, run_with_coverage
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/run_v2_ingest_test.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/sovereign_stress_test.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _detect_failure, _log_turn, call_model, main, run_sync_instance, signal_handler
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): llm.ollama_model_selector, ml.darbar, ml.ml_orchestrator, ml.reward_shaping, ml.vector_memory
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/test_async_embed.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _parse_chunks_from_file
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.async_ingest_config, ingestion.v2.src.async_ingest_orchestrator, ingestion.v2.src.config, ingestion.v2.src.ollama_client
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/test_async_embed_debug.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: _parse_chunks_from_file
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.async_ingest_config, ingestion.v2.src.async_ingest_orchestrator, ingestion.v2.src.config, ingestion.v2.src.ollama_client
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/test_async_ingest.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: stub_parse_func, test_imports
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/test_async_ingestion.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: TestAdaptiveController, TestAsyncIngestionOrchestrator, TestBenchmarkHarness, TestDistributedQueue, TestIntegrationPipeline, TestPipelineWorkers
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/test_deepseek_doctrine.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/test_direct_ingest.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.ingest_pipeline
- `tests/test_e2e_ingestion.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: create_test_book, parse_test_book_module
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/test_embed.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/test_embed_model.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/test_features.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): hse.simulation.synthetic_human_sim, ml.ml_orchestrator, persona.brain, persona.council.dynamic_council, persona.knowledge_engine, persona.modes.mode_orchestrator, persona.state, sovereign.prime_confident
- `tests/test_generate.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/test_improved_doctrine.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: test_extraction
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/test_kis_enhancement_direct.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.ingestion_kis_enhancer, ml.kis.knowledge_integration_system
- `tests/test_kis_exact_scenario.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.ingestion_kis_enhancer
- `tests/test_kis_integration.py`
  - Purpose: Integration adapter module bridging subsystems.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.ingestion_kis_enhancer, ml.kis.knowledge_integration_system
- `tests/test_llm_client.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.llm_handshakes.llm_interface
- `tests/test_llm_kis_integration.py`
  - Purpose: Integration adapter module bridging subsystems.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.judgment.ml_judgment_prior, ml.kis.knowledge_integration_system, ml.llm_handshakes.llm_interface
- `tests/test_minister_converter.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: main, test_basic_structure, test_chapter_conversion, test_combined_index_update, test_entry_creation, test_multiple_chapters
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/test_nodes.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `tests/test_single.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `tests/test_split.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): llm
- `tests/test_split_direct.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/test_split_qwen25.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): llm
- `tests/test_step3_simple.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.llm_handshakes.llm_interface
- `tests/test_step4_training_data.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: main, test_feedback_loop_integration, test_ml_model_training, test_outcome_recording, test_outcome_recording_with_feedback, test_outcomes_directory_structure, test_training_data_generation
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.judgment.ml_judgment_prior, ml.kis.knowledge_integration_system, ml.llm_handshakes.llm_interface, ml.ml_orchestrator, ml.outcomes.outcome_recorder
  - Execution trigger: contains `__main__` guard and is directly executable.
- `tests/vector_db_smoke.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/verification/advanced_test_report.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `tests/verification/check_chapter_text.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/verification/check_doctrine.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/verification/check_extraction.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/verification/check_ingestion_status.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/verification/check_v2_status.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/verification/master_test_report.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `tests/verification/quick_verify.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.analysis, persona.brain, persona.clarify, persona.context, persona.knowledge_engine, persona.main, persona.ollama_runtime, persona.state, persona.trace
- `tests/verification/test_ml_layer.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): hse.human_profile, hse.simulation.synthetic_human_sim, ml.pattern_extraction, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.modes.mode_metrics, persona.ollama_runtime
- `tests/verification/test_persona_simple.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: run_main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.main
- `tests/verification/test_report.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `tests/verification/test_startup.py`
  - Purpose: Test/verification module used in validation flows.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.main
- `tests/verification/verify_all_features.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: test_feature
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.analysis, persona.brain, persona.clarify, persona.knowledge_engine, persona.main, persona.ollama_runtime, persona.state
- `tests/verification/verify_and_run.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): hse.human_profile, hse.simulation.synthetic_human_sim, ml.pattern_extraction, persona.council.dynamic_council, persona.learning.episodic_memory, persona.learning.outcome_feedback, persona.learning.performance_metrics, persona.main, persona.modes.mode_metrics, persona.modes.mode_orchestrator, persona.ollama_runtime, persona.state
- `tests/verification/verify_improvements.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.config, persona, persona.state
- `tests/verification/verify_llm_integration.py`
  - Purpose: Integration adapter module bridging subsystems.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.brain, persona.ollama_runtime
- `tests/verify_api_fixes.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): persona.council.dynamic_council, persona.domain_detector, persona.knowledge_engine, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.ollama_runtime, persona.session_manager, sovereign.prime_confident
- `tests/verify_kis_integration.py`
  - Purpose: Integration adapter module bridging subsystems.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ingestion.v2.src.ingest_pipeline
- `tests/verify_kis_saved.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `tests/verify_llm_implementation.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.llm_handshakes.llm_interface
- `tests/verify_ml_integration.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: main, print_summary, test_domain_detection, test_learning_components, test_llm_connection, test_session_manager, verify_directories, verify_imports
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.ml_orchestrator, persona.domain_detector, persona.knowledge_engine, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.modes.mode_orchestrator, persona.ollama_runtime, persona.session_manager
  - Execution trigger: contains `__main__` guard and is directly executable.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **0** Python files.
- Primary pipeline caller imports: no direct imports in selected primary pipeline files.

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `tests/advanced_persona_test_suite.py`
  - `tests/comprehensive_feature_test.py`
  - `tests/comprehensive_persona_test_suite.py`
  - `tests/master_test_orchestrator.py`
  - `tests/run_kis_integration_test.py`
  - `tests/run_tests.py`
  - `tests/sovereign_stress_test.py`
  - `tests/test_async_embed.py`
  - `tests/test_async_embed_debug.py`
  - `tests/test_async_ingest.py`
  - `tests/test_async_ingestion.py`
  - `tests/test_e2e_ingestion.py`
  - `tests/test_improved_doctrine.py`
  - `tests/test_minister_converter.py`
  - `tests/test_step4_training_data.py`
  - `tests/verify_ml_integration.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Evaluation/validation subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented with active entrypoints**
- Evidence: Multiple executable entrypoints exist; subsystem appears operational.
- Stub/TODO signal count (heuristic): 4

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: limited direct breakage inferred at import layer; verify dynamic loading paths if any.

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Not directly connected to primary pipeline imports** in selected core runner files.
- Likely role: support, optional tooling, or validation helper; may still be indirectly used through dependent modules.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> tests module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `utils`

### 1. Folder Overview
- Inferred architectural classification: **Operational tooling/support module**.
- Files in analysis scope: **5**.
- Direct top-level dependencies: `ml`
- Referenced by other top-level folders: `ingestion`

### 2. File-by-File Explanation
- `utils/ML_WISDOM_INTEGRATION_GUIDE.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: check_system_status, complete_decision_cycle_example, get_learning_metrics, make_decision_with_tracking, record_batch_outcomes, record_decision_outcome, run_decision_batch, setup_ml_wisdom_system, train_on_accumulated_outcomes, troubleshoot_system
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): ml.judgment.ml_judgment_prior, ml.kis.knowledge_integration_system, ml.llm_handshakes.llm_interface, ml.ml_orchestrator
  - Execution trigger: contains `__main__` guard and is directly executable.
- `utils/__init__.py`
  - Purpose: Module purpose inferred from filename and symbol surface; verify against runtime call sites listed below.
  - Defined classes: none
  - Defined functions: none
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
- `utils/batch_convert_rag_storage.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: batch_convert_rag_storage, progress_callback
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `utils/cleanup_atomic_dirs.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: cleanup_domain, main
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.
- `utils/migrate_to_consolidated.py`
  - Purpose: Executable module / entrypoint script; participates directly when invoked by CLI or python module execution.
  - Defined classes: none
  - Defined functions: main, migrate_domain
  - Inputs/Outputs: function signatures and return contracts are module-defined; inspect the listed symbols for exact I/O contracts.
  - Internal dependencies (repo-level): no top-level repo imports detected.
  - Execution trigger: contains `__main__` guard and is directly executable.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **4** Python files.
- Referencing modules:
  - `ingestion/v2/src/chapter_splitter.py`
  - `ingestion/v2/src/doctrine_extractor.py`
  - `ingestion/v2/src/embeddings.py`
  - `ingestion/v2/src/ingest_pipeline.py`
- Primary pipeline caller imports: no direct imports in selected primary pipeline files.

### 4. Execution Flow Reconstruction
- Entrypoints discovered (`__main__`):
  - `utils/ML_WISDOM_INTEGRATION_GUIDE.py`
  - `utils/batch_convert_rag_storage.py`
  - `utils/cleanup_atomic_dirs.py`
  - `utils/migrate_to_consolidated.py`
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Operational tooling/support module**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Implemented with active entrypoints**
- Evidence: Multiple executable entrypoints exist; subsystem appears operational.
- Stub/TODO signal count (heuristic): 0

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: would break or degrade dependent subsystems: `ingestion`

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Not directly connected to primary pipeline imports** in selected core runner files.
- Likely role: support, optional tooling, or validation helper; may still be indirectly used through dependent modules.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> utils module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---

## Subsystem: `knowledge`

### 1. Folder Overview
- Inferred architectural classification: **Data/knowledge processing support subsystem**.
- Files in analysis scope: **2**.
- Direct top-level dependencies: none detected in top-level import graph.
- Referenced by other top-level folders: no cross-folder imports detected.

### 2. File-by-File Explanation
- `knowledge/embeddings.npy`
  - Purpose: Binary model/index artifact used by retrieval or embedding-related components.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.
- `knowledge/principles.json`
  - Purpose: Configuration/schema/model artifact used to parameterize runtime or evaluation behavior.
  - Defined classes: none
  - Defined functions: none
  - Internal logic: non-executable artifact; consumed by importing/loader modules.

### 3. Cross-Reference Dependency Map
- Import reference count across repository: **0** Python files.
- Primary pipeline caller imports: no direct imports in selected primary pipeline files.

### 4. Execution Flow Reconstruction
- No direct CLI entrypoint discovered; subsystem executes when imported/called by upstream modules.
- Trigger model:
  - Import-time wiring through controllers/orchestrators.
  - Runtime invocation via class instantiation and function calls from referencing modules.
  - Data flows through function arguments and returned dict/object payloads; downstream consumers reside in referencing modules listed above.

### 5. Architectural Role in System
- Classification: **Data/knowledge processing support subsystem**
- Reasoning: derived from filename patterns, symbol types (orchestrator/runner/adapter/server), dependency directionality, and caller locations in runtime/evaluation stacks.

### 6. Implementation Maturity Assessment
- Status: **Config/data support**
- Evidence: Mostly non-executable configuration artifacts in selected scope.
- Stub/TODO signal count (heuristic): 0

### 7. Strategic Importance of the Module
- Strategic function: contributes specialized capability in its architectural band (core runtime, evaluation, simulation, ML, ingestion, or tooling).
- System-level dependency impact: inferred from reverse imports and topological position in the dependency graph.
- Removal impact: limited direct breakage inferred at import layer; verify dynamic loading paths if any.

### 8. Risks and Improvement Opportunities
- Architectural risks:
  - Potential tight coupling where orchestrator modules import deep internals across folders.
  - Interface drift risk where method signatures evolve without synchronized callers.
  - Mixed runtime/config/data concerns in some folders can reduce maintainability.
- Improvement opportunities:
  - Introduce explicit interface contracts (typed dataclasses/protocols) between folder boundaries.
  - Add contract tests for cross-folder integration points.
  - Separate generated artifacts from source/config trees to keep audits deterministic.

### 10. Contribution to Main Pipeline
- Current connection status: **Not directly connected to primary pipeline imports** in selected core runner files.
- Likely role: support, optional tooling, or validation helper; may still be indirectly used through dependent modules.
- Integration points: imports, class instantiation, and function calls in referencing modules.
- Data dependencies: argument payloads from caller context; outputs consumed as decisions, metrics, transformations, or side effects depending on module purpose.
- Execution triggers: CLI entrypoint invocation and/or upstream orchestrator calls.

### 11. Integration Feasibility
- Feasible integration patterns if not fully wired:
  - Pre-processing stage: normalize/enrich inputs before core decision engine.
  - Validation layer: quality/safety checks before output commit.
  - Decision support: auxiliary scoring/routing signals consumed by orchestrator.
  - Monitoring/analytics: emit telemetry to dashboards and gate reports.
  - Simulation/evaluation: generate stress/OOD/adversarial cases for robustness loops.
- Required changes: expose stable interfaces, define schema contracts, add orchestrator hooks, and register metrics/report outputs in evaluation artifacts.

### 12. Operational Workflow Documentation
- Overview: subsystem responsibilities and boundaries are defined by module families in this folder.
- Purpose in larger system: supply focused capability consumed by higher-order orchestrators and evaluation pipelines.
- Internal architecture: file/module decomposition listed in section 2 plus import topology in section 3.
- Execution workflow (text diagram):
  ```text
  Upstream Controller/Runner
      -> knowledge module entry function/class
      -> internal helper modules/classes
      -> output payload / side effect
      -> downstream consumer (metrics, decision, storage, API, or report)
  ```
- Inputs/outputs: discovered via function/class symbols; concrete schemas are defined in callable signatures and structured dicts/dataclasses in code.
- External dependencies: represented by non-repo imports in each Python module.
- Error handling: inferred from try/except in executable modules and caller-level fallback logic.
- Limitations: static analysis cannot prove all dynamic dispatch/runtime environment branches; validate with integration tests and controlled runs.

### 13. System-Level Impact
- Added capability: this subsystem extends system breadth in its domain (runtime cognition, evaluation, data prep, simulation, or ops).
- Problem solved: decouples specialized concerns from the core engine and enables composable architecture.
- If absent: dependent modules lose functionality or degrade behavior; exact blast radius correlates with reverse-import set and runtime caller criticality.

---
