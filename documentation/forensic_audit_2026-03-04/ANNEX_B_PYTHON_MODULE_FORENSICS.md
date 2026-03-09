# Annex B - Python Module Forensic Cards

- Total python modules: **289**

## `Memory/pwm.py`

- Size bytes: 5244
- Lines: 124
- Classes (0): 
- Functions (8): _call_llm, decide_commits, extract_signals, generate_hypotheses, render_template, score_confidence, session_summary, translate_to_db_changes
- Imports (3): json, os, typing
- Module docstring preview: PWM runtime helpers: provides stubs for the extract -> score -> commit pipeline using the templates created from the Personal World Model document. This module is intentionally lightweight and defensive: it does not require a running DB or LLM to import. It provides: - render_template(template_path,

## `analytics/__init__.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `analytics/dashboard.py`

- Size bytes: 1705
- Lines: 61
- Classes (1): PerformanceDashboard
- Functions (4): __init__, compute_rolling_metrics, generate_weak_feature_alert, suggest_retraining_actions
- Imports (0): 

## `analytics/improvement_tracker.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `analytics/reporting.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `analyze_conversation_learning.py`

- Size bytes: 8377
- Lines: 219
- Classes (0): 
- Functions (0): 
- Imports (2): json, pathlib
- Module docstring preview: Analyze Learning from LLM Conversation: Stress Management File: data/conversations/llm_conversation_20260219_192944.json

## `archive/integrations_old/__init__.py`

- Size bytes: 219
- Lines: 6
- Classes (0): 
- Functions (0): 
- Imports (0): 
- Module docstring preview: Integration bridges between major subsystems. - persona_mas_integration.py: Full integration of Persona with Multi-Agent System - persona_mas_integration_simple.py: Simplified variant for quick experiments

## `archive/integrations_old/persona_mas_integration.py`

- Size bytes: 9757
- Lines: 264
- Classes (1): PersonaAgent
- Functions (5): __init__, demo_with_mocks, demo_with_ollama, respond, user_behavior
- Imports (12): multi_agent_sim.agents, multi_agent_sim.archetypes, multi_agent_sim.logger, multi_agent_sim.orchestrator, os, persona.analysis, persona.brain, persona.clarify, persona.context, persona.ollama_runtime, persona.state, sys
- Module docstring preview: Integration demo: Multi-Agent Simulator + Persona Subsystem Shows a conversation between: - User Agent (MockAgent simulating user input) - Persona Agent (using persona logic with PersonaBrain control) Run: python -m era_mas_persona_demo or: python persona_mas_integration.py

## `archive/integrations_old/persona_mas_integration_simple.py`

- Size bytes: 6576
- Lines: 185
- Classes (1): LLMPersonaAgent
- Functions (5): __init__, demo_simple, respond, show_transcript, user_behavior
- Imports (12): multi_agent_sim.agents, multi_agent_sim.archetypes, multi_agent_sim.logger, multi_agent_sim.orchestrator, os, persona.brain, persona.context, persona.ollama_runtime, persona.state, persona_mas_integration, sys, traceback
- Module docstring preview: Simple Integration Demo: Multi-Agent Simulator + Persona Subsystem (Using REAL LLM - requires Ollama running) Shows a conversation between: - User Agent (MockAgent simulating user input) - Persona Agent (using real LLM with deepseek + llama3.1) Run: python persona_mas_integration_simple.py

## `archive/runtime_old/__init__.py`

- Size bytes: 559
- Lines: 19
- Classes (0): 
- Functions (0): 
- Imports (6): action_spiral, consciousness, diagnostics, dopamine, memory, predictive
- Module docstring preview: Runtime architecture simulation package. Provides lightweight simulation stubs inspired by the 'Runtime Architecture Bug' document.

## `archive/runtime_old/action_spiral.py`

- Size bytes: 1764
- Lines: 47
- Classes (1): ActionSelection
- Functions (3): __init__, reinforce_habit, select_action
- Imports (1): typing
- Module docstring preview: action_spiral.py Simple ActionSelection simulating valuation -> goal-directed -> habitual handoff.

## `archive/runtime_old/consciousness.py`

- Size bytes: 859
- Lines: 27
- Classes (1): ConsciousnessThreshold
- Functions (3): __init__, adjust_threshold, is_conscious
- Imports (1): typing
- Module docstring preview: consciousness.py Model for a broadcasting threshold: decides whether a signal reaches conscious access.

## `archive/runtime_old/diagnostics.py`

- Size bytes: 2005
- Lines: 51
- Classes (1): RuntimeObserver
- Functions (6): __init__, detect_missing_brake, detect_runaway_habit, record_habit, summary, trace_event
- Imports (1): typing
- Module docstring preview: diagnostics.py Runtime observer utilities to detect common runtime architecture bugs.

## `archive/runtime_old/dopamine.py`

- Size bytes: 870
- Lines: 29
- Classes (1): LearningSignal
- Functions (3): __init__, apply_update, compute_delta
- Imports (1): typing
- Module docstring preview: dopamine.py Simple learning signal utilities implementing temporal-difference style update.

## `archive/runtime_old/memory.py`

- Size bytes: 1028
- Lines: 32
- Classes (1): MemoryReplay
- Functions (2): consolidate, reconsolidate
- Imports (1): typing
- Module docstring preview: memory.py Simple MemoryReplay and Reconsolidation helpers.

## `archive/runtime_old/predictive.py`

- Size bytes: 2181
- Lines: 64
- Classes (1): PredictionEngine
- Functions (5): __init__, add_listener, clear_listeners, predict, update
- Imports (1): typing
- Module docstring preview: predictive.py Simple PredictionEngine to compute predictions and prediction errors.

## `archive/runtime_old/run_sim.py`

- Size bytes: 1690
- Lines: 48
- Classes (0): 
- Functions (1): demo
- Imports (6): action_spiral, consciousness, diagnostics, dopamine, memory, predictive
- Module docstring preview: Small CLI runner to demonstrate runtime components.

## `evaluation/__init__.py`

- Size bytes: 1101
- Lines: 38
- Classes (0): 
- Functions (1): __getattr__
- Imports (3): __future__, importlib, typing
- Module docstring preview: Evaluation package exports (lazy-loaded to avoid heavy import side effects).

## `evaluation/adversarial_user_simulator.py`

- Size bytes: 7162
- Lines: 180
- Classes (2): AdversarialGeneration, AdversarialUserSimulator
- Functions (5): __init__, _build_instruction, _stable_index, generate, summarize_rounds
- Imports (4): __future__, dataclasses, hashlib, typing
- Module docstring preview: Adversarial user simulator for Phase 4 self-play stress testing. Design goals: - Deterministic and seed-reproducible (no extra LLM dependency required). - Plausible scenario perturbations that target regret/contradiction/blind spots. - Compatible with the existing evaluation runner interface.

## `evaluation/analyze_kis_failure_mode.py`

- Size bytes: 15305
- Lines: 372
- Classes (0): 
- Functions (8): _domain_for_principle, _iter_council_rows, _load_benchmark_index, _to_float, _top_items, analyze, main, write_markdown
- Imports (8): __future__, argparse, collections, evaluation.scoring.outcome_scorer, json, pathlib, sys, typing
- Module docstring preview: Step-0 KIS failure-mode diagnosis. Pull hardest high-U failures from Phase2 results and summarize: - required vs matched principles - triggered failure modes - inferred underweighted domains (from missing principles) - retrieval/evaluator bottleneck indicators

## `evaluation/analyze_minister_similarity.py`

- Size bytes: 7889
- Lines: 228
- Classes (0): 
- Functions (8): _collect_stance_vectors, _filter_dataset, _flatten_upper, _safe_pearson, _similarity_matrices, _top_pair_drift, _write_markdown, main
- Imports (10): __future__, datetime, evaluation.scoring.rubric_engine, json, math, numpy, pathlib, persona.council, sys, typing
- Module docstring preview: Build minister similarity matrices and compare core vs OOD structure. Outputs: - evaluation/results/minister_similarity_report.json - evaluation/results/MINISTER_SIMILARITY_REPORT.md

## `evaluation/build_kis2_index.py`

- Size bytes: 1902
- Lines: 67
- Classes (0): 
- Functions (1): main
- Imports (7): __future__, argparse, evaluation.kis2_retrieval, json, numpy, pathlib, sys
- Module docstring preview: Build KIS 2.0 principle embedding index.

## `evaluation/build_phase2_gating_dataset.py`

- Size bytes: 13604
- Lines: 377
- Classes (0): 
- Functions (7): _build_variants, _iter_scenarios, _minister_default_record, _union_ids, _variant_templates, build_dataset, main
- Imports (10): __future__, argparse, copy, evaluation.gating_support, evaluation.run_phase2_robustness, evaluation.scoring.outcome_scorer, evaluation.scoring.rubric_engine, json, pathlib, typing
- Module docstring preview: Build offline minister-level gating datasets from a split. Supports controlled synthetic perturbations to increase routing samples. No model training is performed here.

## `evaluation/create_split_manifest.py`

- Size bytes: 6974
- Lines: 210
- Classes (0): 
- Functions (4): _allocate_counts, _dataset_name_for_category, build_split_manifest, main
- Imports (10): __future__, argparse, datetime, evaluation.scoring.rubric_engine, json, math, pathlib, random, sys, typing
- Module docstring preview: Create reproducible train/val/test split manifest for benchmark scenarios. Policy: - Stratified by scenario category - Fixed random seed for reproducibility - Includes OOD in train while preserving strict val/test holdouts

## `evaluation/distribution_shift.py`

- Size bytes: 3994
- Lines: 121
- Classes (1): ShiftedScenario
- Functions (6): _sparse_info_transform, _stable_index, _time_pressure_transform, _value_conflict_transform, apply_shift_mode, parse_shift_modes
- Imports (4): __future__, dataclasses, hashlib, typing
- Module docstring preview: Distribution-shift scenario transformations for Milestone 4.2. All transformations are deterministic and seed-reproducible.

## `evaluation/evaluate_phase2_gates.py`

- Size bytes: 9650
- Lines: 293
- Classes (0): 
- Functions (7): _ge_with_tol, _get_float, _le_with_tol, _load_json, evaluate_gates, main, write_markdown
- Imports (6): __future__, argparse, datetime, json, pathlib, typing
- Module docstring preview: Evaluate Phase 2 gating success criteria and emit pass/fail report. Default criteria: - Core lift >= +0.05 absolute - OOD lift >= 0.0 - Core effect size >= 0.5 - No calibration collapse - No minister collapse (when gating is enabled)

## `evaluation/evaluation_runner.py`

- Size bytes: 27172
- Lines: 640
- Classes (2): EvaluationConfig, EvaluationRunner
- Functions (14): __init__, __init__, _distribution_from_category, _extract_named_value, _extract_uncertainty_signals, _load_model_version, _run_seed, ablation_analysis, compare_runs, enable_isolation_mode, export_results, run_evaluation, to_dict, verify_dataset_integrity
- Imports (14): evaluation.gating_support, evaluation.scoring.outcome_scorer, evaluation.scoring.regret_scorer, evaluation.scoring.rubric_engine, evaluation.stats_engine, json, logging, numpy, os, pathlib, random, re, time, typing
- Module docstring preview: Evaluation Runner - Main orchestration for research-grade benchmarking 5 seed runs, ablation matrix, isolation mode, statistical validation.

## `evaluation/freeze_diversity_baseline.py`

- Size bytes: 4520
- Lines: 142
- Classes (0): 
- Functions (3): _read_json, _sha256, main
- Imports (7): __future__, argparse, datetime, hashlib, json, pathlib, typing
- Module docstring preview: Freeze and tag the diversity baseline configuration/state.

## `evaluation/gate_milestone3.py`

- Size bytes: 16533
- Lines: 412
- Classes (0): 
- Functions (5): _collect_council_records, _darbar_delta, _load_json, _safe_float, main
- Imports (5): __future__, argparse, json, pathlib, typing
- Module docstring preview: Gate Milestone 3 completion from saved artifacts. Checks: 1) ECE < 0.05 (calibrated) 2) Overconfidence bias < 0.03 3) U predicts error with AUC >= threshold 4) Top-decile error concentration ratio >= target 5) (control stage only) DARBAR-triggered decisions reduce error under high-U cases 6) (contro

## `evaluation/gating_model.py`

- Size bytes: 11248
- Lines: 319
- Classes (2): GatingTrainingConfig, MinisterGatingMLP
- Functions (12): __init__, _eval_stage2, _prior_tensor, _record_input, _stack_records, _stage2_loss_terms, _weight_collapse_stats, forward, load_gating_bundle, logits, save_gating_bundle, train_gating_model
- Imports (8): __future__, dataclasses, json, pathlib, torch, torch.nn, torch.nn.functional, typing
- Module docstring preview: PyTorch gating network for minister weighting.

## `evaluation/gating_support.py`

- Size bytes: 19227
- Lines: 549
- Classes (1): MinisterOutput
- Functions (23): _clamp, _embed_cache_key, _empty_kis_output, _extract_float, _infer_constraint_state, _infer_situation_state, _normalize_path, apply_pca_reducer, build_gating_features, build_model_input_from_spec, compute_regret_adjusted_target, decision_difficulty_proxy, disagreement_entropy, escalation_pressure_indicator, fetch_ollama_embedding, fit_pca_reducer, irreversibility_score, minister_confidence_variance, minister_confidence_vector, pairwise_confidence_gaps, parse_minister_outputs, scenario_text_for_embedding, vote_margin
- Imports (10): __future__, dataclasses, hashlib, math, ml.features.feature_extractor, os, re, requests, torch, typing
- Module docstring preview: Utilities for Phase2 minister-level logging and gating features.

## `evaluation/kis2_retrieval.py`

- Size bytes: 15486
- Lines: 417
- Classes (4): KIS2Config, KIS2Retrieval, _RerankerMLP, _RerankerMLP
- Functions (18): __init__, __init__, _category_code, _clamp01, _cosine_sim_matrix, _domain_match_score, _feature_row, _load_or_build_embeddings, _load_principles, _load_reranker, _rerank_score, build_prompt_block, ensure_default_principles_file, fetch_ollama_embedding, forward, metadata, retrieve, scenario_text_for_embedding
- Imports (10): __future__, dataclasses, json, numpy, os, pathlib, requests, torch, torch.nn, typing
- Module docstring preview: KIS 2.0 retrieval path (parallel to KIS 1.0). Design goals: - Opt-in only; never replaces KIS 1.0 by default. - Deterministic embedding retrieval over a fixed principle catalog. - Optional lightweight reranker loaded from JSON artifact.

## `evaluation/learned_uncertainty.py`

- Size bytes: 7110
- Lines: 184
- Classes (2): LearnedUncertaintyPredictor, _UncertaintyMLP
- Functions (9): __init__, __init__, _feature_value, _to_float_or_none, forward, from_json, metadata, predict, threshold_config
- Imports (7): __future__, json, numpy, pathlib, torch, torch.nn, typing
- Module docstring preview: Runtime loader/inference for frozen learned uncertainty predictor artifacts.

## `evaluation/metrics/__init__.py`

- Size bytes: 126
- Lines: 7
- Classes (0): 
- Functions (0): 
- Imports (1): evaluation_metrics
- Module docstring preview: Evaluation-only metrics utilities.

## `evaluation/metrics/evaluation_metrics.py`

- Size bytes: 9792
- Lines: 269
- Classes (1): EvaluationMetrics
- Functions (10): _predict_isotonic, apply_isotonic_regression, apply_isotonic_regression_crossfit, compute_bootstrap_ci, compute_brier, compute_ece, compute_effect_size, compute_mean, compute_paired_ttest, compute_variance
- Imports (5): __future__, dataclasses, numpy, scipy, typing
- Module docstring preview: Detached evaluation metrics for frozen benchmark analysis.

## `evaluation/red_team_governance.py`

- Size bytes: 4165
- Lines: 119
- Classes (0): 
- Functions (3): _mean, inject_governance_attack_text, summarize_governance_metrics
- Imports (4): __future__, collections, re, typing
- Module docstring preview: Governance red-team helpers for Milestone 4.3.

## `evaluation/reliability_analysis.py`

- Size bytes: 23963
- Lines: 605
- Classes (0): 
- Functions (20): _apply_calibrator_to_records, _apply_isotonic_model, _apply_split_lookup, _apply_temperature, _compute_reliability_metrics, _fit_and_select_calibrator, _fit_temperature, _infer_distribution_from_scenario_id, _load_records_from_result, _load_split_lookup, _normalize_record, _plot_reliability, _plot_reliability_svg, _reconstruct_records_from_run_payload, _split_by_distribution, _xml_escape, load_records, main, map_point, panel_xy
- Imports (9): __future__, argparse, evaluation.metrics.evaluation_metrics, json, math, matplotlib.pyplot, numpy, pathlib, typing
- Module docstring preview: Reliability analysis and split-safe calibration workflow. Implements: - Reliability bins (10) - ECE, MCE, Brier, overconfidence bias - Per-distribution analysis: core, ood, adv, combined - Train/val/test calibration with no leakage: - cross-fitted isotonic regression (fit on train, select on val) - 

## `evaluation/run_phase2_robustness.py`

- Size bytes: 120106
- Lines: 2739
- Classes (1): Phase2Runner
- Functions (50): __init__, _ablation_delta, _acquire_run_lock, _apply_ablation, _build_council_prompt, _build_kis2_context, _build_principle_activation_block, _check_runtime, _choose_weighted_decision, _compare_runs, _completion_checks, _compute_percentile, _council_engine_with_governance_redteam, _council_engine_with_self_play, _council_engine_with_shift_mode, _curve_mean, _detect_principle_activation, _estimate_information_ambiguity, _extract_named_value, _kis2_should_activate, _load_uncertainty_thresholds_from_analysis, _parse, _parse_with_single_repair, _pid_is_alive, _probe_runtime_uncertainty_thresholds, _release_run_lock, _run_ablations, _run_adversarial_self_play, _run_core, _run_distribution_shift_suite, _run_governance_red_team, _run_stress, _safe_load_json, _save, _scenario_ids_for_dataset, _speak_with_num_predict, _summarize_adversarial_self_play, _summarize_distribution_shift_run, _summarize_gating_weights, _summarize_kis2_usage
- Imports (28): argparse, copy, datetime, evaluation.adversarial_user_simulator, evaluation.distribution_shift, evaluation.evaluation_runner, evaluation.gating_model, evaluation.gating_support, evaluation.kis2_retrieval, evaluation.learned_uncertainty, evaluation.metrics.evaluation_metrics, evaluation.red_team_governance, evaluation.scoring.outcome_scorer, json, logging, ml.features.feature_extractor, os, pathlib, persona.modes.mode_orchestrator, persona.ollama_runtime, re, requests, run_benchmark, subprocess, sys, time, torch, typing
- Module docstring preview: Phase 2 - Robustness & Attribution Runs: - Core benchmark (baseline vs council) - Stress benchmarks (adversarial, out_of_distribution) - Full ablation matrix (core dataset) Outputs: - evaluation/results/phase2_robustness_results.json - evaluation/results/PHASE2_ROBUSTNESS_REPORT.md

## `evaluation/run_phase2_with_gates.py`

- Size bytes: 16089
- Lines: 410
- Classes (0): 
- Functions (2): assert_ollama_available, main
- Imports (10): __future__, argparse, evaluation.create_split_manifest, evaluation.evaluate_phase2_gates, evaluation.run_phase2_robustness, json, os, pathlib, requests, sys
- Module docstring preview: One-shot runner for split-scoped Phase2 evaluation + gate checks. Flow: 1) Ensure split manifest exists (optional auto-create) 2) Run Phase2 robustness on selected split 3) Evaluate gate criteria and write reports

## `evaluation/run_phase4_stress.py`

- Size bytes: 4238
- Lines: 114
- Classes (0): 
- Functions (2): _build_phase2_cmd, main
- Imports (5): __future__, argparse, pathlib, subprocess, sys
- Module docstring preview: Unified Milestone 4 stress runner. This is a thin orchestrator that executes all stress layers through `evaluation/run_phase2_robustness.py` to preserve a single evaluation harness.

## `evaluation/scoring/outcome_scorer.py`

- Size bytes: 16040
- Lines: 408
- Classes (2): OutcomeScorer, RubricEvaluation
- Functions (10): __init__, _build_justification, _check_path_match, _extract_principles, _extract_principles_rule_based, _extract_principles_semantic, _match_failure_modes, _principle_name_token_match, evaluate_decision, get_results_summary
- Imports (6): dataclasses, json, logging, os, re, typing
- Module docstring preview: Outcome Scorer - Evaluates decision quality against rubrics CRITICAL: Rule-based, deterministic scoring with ZERO LLM calls. Scoring uses keyword matching and structural pattern matching only. No LLM evaluation → No circular reasoning. 100% reproducible across runs.

## `evaluation/scoring/regret_scorer.py`

- Size bytes: 4179
- Lines: 121
- Classes (2): RegretScore, RegretScorer
- Functions (3): __init__, get_summary, score_regret
- Imports (2): dataclasses, typing
- Module docstring preview: Regret Scorer - Quantifies decision regret on calibrated scale Implements regret scoring aligned with rubric severity levels. No side effects on live system.

## `evaluation/scoring/rubric_engine.py`

- Size bytes: 4676
- Lines: 151
- Classes (1): RubricEngine
- Functions (7): __init__, _compute_file_hash, get_rubric, load_all_scenarios, load_manifest, load_scenario, verify_dataset_integrity
- Imports (4): hashlib, json, pathlib, typing
- Module docstring preview: Rubric Engine - Loads and validates ground truth rubrics Manages scenario rubrics, validates data integrity via hashing.

## `evaluation/stats_engine.py`

- Size bytes: 16854
- Lines: 452
- Classes (2): ConfidenceInterval, StatsEngine
- Functions (11): __init__, _interpret_power_grid, ablation_effect_size, aggregate_seed_results, bootstrap_paired_test, calibration_curve, calibration_diagnostics, compute_confidence_intervals, compute_power_analysis, paired_t_test, power_grid_analysis
- Imports (5): dataclasses, numpy, scipy, scipy.stats, typing
- Module docstring preview: Statistics Engine - Computes statistical validation metrics Five seed runs, bootstrap resampling, paired t-tests, effect sizes, calibration curves. Research-grade statistical rigor.

## `evaluation/train_kis2_reranker.py`

- Size bytes: 4079
- Lines: 138
- Classes (1): Reranker
- Functions (4): __init__, _to_matrix, forward, main
- Imports (8): __future__, argparse, json, numpy, pathlib, torch, torch.nn, typing
- Module docstring preview: Train a lightweight KIS2 principle reranker. Expected input JSON rows (list): { "similarity_score": float, "irreversibility_score": float, "disagreement_entropy": float, "domain_match": float, "historical_success_rate": float, "scenario_category": float, "label": 0 or 1 }

## `evaluation/train_phase2_gating.py`

- Size bytes: 9392
- Lines: 237
- Classes (0): 
- Functions (6): _attach, _hyper_grid, _load_rows, _prepare_model_inputs, _row_structured_input, main
- Imports (8): __future__, argparse, datetime, evaluation.gating_model, evaluation.gating_support, json, pathlib, typing
- Module docstring preview: Train minister-weight gating network offline.

## `evaluation/uncertainty_analysis.py`

- Size bytes: 61102
- Lines: 1593
- Classes (1): _UncertaintyMLP
- Functions (35): __init__, _apply_derived_uncertainty_signals, _apply_split_lookup, _auc_quality_label, _binary_metrics, _bucket_metrics, _build_feature_matrix, _compute_high_error_labels, _compute_u, _control_thresholds, _default_embedding_dataset_paths, _extract_primitives, _extract_records_from_run_payload, _feature_value, _has_any_uncertainty_signal, _infer_distribution_from_scenario_id, _kmeans, _load_embedding_lookup, _load_records_from_result, _load_rows, _load_split_lookup, _normalize_component, _normalize_record, _pearson, _rankdata, _record_error, _roc_auc_from_scores, _spearman, _split_indices, _subset, _train_learned_uncertainty_predictor, _validate, forward, load_records, main
- Imports (8): __future__, argparse, json, numpy, pathlib, torch, torch.nn, typing
- Module docstring preview: Composite uncertainty analysis. Stage 2: U = weighted linear combination of normalized primitives: entropy, confidence_variance, inverse_margin, kis_variance (+ optional ml_prior_variance) Stage 3: Empirical validation that higher U predicts higher error probability: - correlation(U, error) - ROC AU

## `hse/__init__.py`

- Size bytes: 674
- Lines: 16
- Classes (0): 
- Functions (0): 
- Imports (4): crisis_injector, human_profile, personality_drift, population_manager
- Module docstring preview: Human Simulation Engine (HSE) modules. Provides synthetic human population simulation with: - SyntheticHuman: persona with traits, wealth, decisions - PopulationManager: manages cohorts of humans - CrisisInjector: injects random life events - PersonalityDrift: tracks evolving traits - AnalyticsServe

## `hse/analytics_server.py`

- Size bytes: 1839
- Lines: 64
- Classes (0): 
- Functions (5): event_stream, index, start_server, stream, stream_metrics
- Imports (4): flask, flask_cors, json, time

## `hse/crisis_injector.py`

- Size bytes: 1938
- Lines: 41
- Classes (1): CrisisInjector
- Functions (2): __init__, maybe_inject
- Imports (2): datetime, random

## `hse/human_profile.py`

- Size bytes: 2221
- Lines: 78
- Classes (1): SyntheticHuman
- Functions (7): __getitem__, __init__, __setitem__, build_user_prompt, generate_context, get, profile
- Imports (2): copy, random

## `hse/personality_drift.py`

- Size bytes: 2705
- Lines: 71
- Classes (1): PersonalityDrift
- Functions (4): __init__, _create_bias, _mutate_trait, apply
- Imports (2): datetime, random

## `hse/population_manager.py`

- Size bytes: 2499
- Lines: 87
- Classes (2): PopulationManager, SyntheticHuman
- Functions (10): __init__, __init__, apply_drift, create, generate_context, get, list_ids, profile, save_state, snapshot
- Imports (6): copy, datetime, json, personality_drift, threading, uuid

## `hse/simulation/__init__.py`

- Size bytes: 187
- Lines: 5
- Classes (0): 
- Functions (0): 
- Imports (2): bidirectional_simulation, synthetic_human_sim

## `hse/simulation/bidirectional_simulation.py`

- Size bytes: 19764
- Lines: 457
- Classes (1): BidirectionalSimulation
- Functions (16): __init__, _build_human_profile, _generate_final_report, _generate_persona_response, _generate_user_input, _human_state_snapshot, _maybe_inject_crisis, _maybe_switch_mode, _print_final_summary, _print_turn_summary, _record_episode, _sync_human_object, _update_human_state, _update_metrics, run_conversation, save_report
- Imports (12): __future__, datetime, hse.crisis_injector, hse.human_profile, hse.personality_drift, json, pathlib, persona.context, persona.learning.episodic_memory, persona.state, time, typing
- Module docstring preview: Bidirectional LLM simulation: User LLM talks to Persona LLM. Both sides are autonomous for stress testing and long-horizon evaluation.

## `hse/simulation/human_persona_adapter.py`

- Size bytes: 1557
- Lines: 52
- Classes (1): HumanPersonaAdaptation
- Functions (4): __init__, detect_challenge_behavior, measure_advice_adoption, measure_trust_trajectory
- Imports (0): 

## `hse/simulation/stress_orchestrator.py`

- Size bytes: 2434
- Lines: 75
- Classes (1): StressScenarioOrchestrator
- Functions (4): __init__, _inject_stage, measure_stress_response_quality, run_compounding_crisis
- Imports (0): 

## `hse/simulation/synthetic_human_sim.py`

- Size bytes: 6793
- Lines: 162
- Classes (1): SyntheticHumanSimulation
- Functions (4): __init__, apply_consequences, call_llm, generate_next_input
- Imports (7): hse.crisis_injector, hse.human_profile, hse.personality_drift, queue, sys, threading, typing
- Module docstring preview: Synthetic Human Simulation: Generates realistic human responses to Persona advice. Creates bidirectional conversation loop for stress testing.

## `ingestion/v1/ingest.py`

- Size bytes: 59600
- Lines: 1654
- Classes (0): 
- Functions (32): _ministers_progress_cb, chunk_text, classify_chapter, dedupe_list, doctrine_density, doctrine_to_nodes, extract_doctrine, extract_pdf_pages, extract_text_universal, extract_texts_from_doc, extract_with_ocr, extract_with_pdfminer, extract_with_pypdf, fallback_split_by_headings, flush_buffer, has_actionable_doctrine, infer_domains_from_text, ingest_folder, is_doctrine_structurally_valid, is_glyph_stream, live_progress, looks_glyph_encoded, normalize_doctrine, phase2_progress, reject_verbatim_quotes_inline, repair_glyph_text, run_full_ingest_with_resume, sha, split_chapters_with_ollama_streaming, text_quality_score, update_progress, validate_doctrine_inline
- Imports (16): argparse, concurrent.futures, hashlib, json, llm, os, pdfminer.high_level, pypdf, re, shutil, subprocess, sys, tempfile, time, typing, unicodedata

## `ingestion/v1/llm.py`

- Size bytes: 51731
- Lines: 1355
- Classes (1): OllamaClient
- Functions (24): __init__, _ministers_progress_cb, _run, build_minister_memories, call_json_llm_strict, classify_chapter, doctrine_density, doctrine_to_nodes, embed, embed_nodes, extract_doctrine, extract_text_universal, extract_with_ocr, generate, has_actionable_doctrine, infer_domains_from_text, ingest_folder, is_doctrine_structurally_valid, live_progress, normalize_doctrine, phase2_progress, repair_glyph_text, run_full_ingest_with_resume, update_progress
- Imports (6): __future__, argparse, json, os, subprocess, typing
- Module docstring preview: LLM & helper utilities used by the ingestion runner. This file intentionally provides the following exported symbols used by `ingest.py`: - `OllamaClient` — a thin wrapper around the `ollama` CLI - `call_json_llm_strict(prompt, system, client)` — calls LLM and parses JSON - `embed_nodes(nodes, clien

## `ingestion/v2/run_all_v2_ingest.py`

- Size bytes: 1612
- Lines: 49
- Classes (0): 
- Functions (1): validate_paths
- Imports (3): os, src.ingest_pipeline, sys

## `ingestion/v2/scripts/generate_chapters_fallback.py`

- Size bytes: 968
- Lines: 22
- Classes (0): 
- Functions (0): 
- Imports (5): ingestion.v2.src.chapter_splitter, ingestion.v2.src.pdf_extraction, json, os, sys

## `ingestion/v2/src/ASYNC_PIPELINE_GUIDE.py`

- Size bytes: 17753
- Lines: 406
- Classes (0): 
- Functions (0): 
- Imports (0): 
- Module docstring preview: ═══════════════════════════════════════════════════════════════════════════════ ASYNC INGESTION PIPELINE - COMPREHENSIVE ARCHITECTURE GUIDE ═══════════════════════════════════════════════════════════════════════════════ This document describes the complete async ingestion pipeline implementation at 

## `ingestion/v2/src/__init__.py`

- Size bytes: 2164
- Lines: 86
- Classes (0): 
- Functions (0): 
- Imports (5): async_ingest_config, async_ingest_orchestrator, async_workers, ingest_metrics, rate_controller
- Module docstring preview: RAG Ingestion Pipeline v2 - Async Multi-Stage Architecture This package provides a production-ready async ingestion system with: - Adaptive rate limiting - Multi-stage pipeline (reader → embed → DB → aggregation) - Comprehensive metrics - 10-20x throughput improvement over sync Main Entry Point: fro

## `ingestion/v2/src/adaptive_controller.py`

- Size bytes: 10217
- Lines: 277
- Classes (5): AdaptiveConfig, AdaptiveController, PipelineMetrics, RateLimit, TokenBucket
- Functions (16): __init__, __init__, __post_init__, _evaluate_feedback, _refill, acquire, acquire_permit, current_tokens, example_controller, feedback_loop, get_metrics, record_processing, reset_metrics, set_rate_multiplier, to_dict, update_queue_depth
- Imports (6): asyncio, collections, dataclasses, datetime, time, typing
- Module docstring preview: Adaptive Rate Controller - Token Bucket with Feedback Loop

## `ingestion/v2/src/async_doctrine_workers.py`

- Size bytes: 8710
- Lines: 235
- Classes (0): 
- Functions (3): _extract, doctrine_worker, run_async_doctrine_extraction
- Imports (7): async_ingest_config, asyncio, doctrine_extractor, ingest_metrics, logging, rate_controller, typing
- Module docstring preview: Async workers for parallel Phase 2 doctrine extraction.

## `ingestion/v2/src/async_ingest_config.py`

- Size bytes: 2126
- Lines: 78
- Classes (1): Chunk
- Functions (1): to_db_tuple
- Imports (3): dataclasses, typing, uuid
- Module docstring preview: Configuration and data models for async ingestion pipeline.

## `ingestion/v2/src/async_ingest_orchestrator.py`

- Size bytes: 8219
- Lines: 220
- Classes (1): AsyncIngestionPipeline
- Functions (5): __init__, close_db, initialize_db, main_ingest, run
- Imports (10): aiohttp, async_ingest_config, async_workers, asyncio, asyncpg, concurrent.futures, ingest_metrics, logging, rate_controller, typing
- Module docstring preview: Main orchestrator for async multi-stage ingestion pipeline.

## `ingestion/v2/src/async_ingestion_orchestrator.py`

- Size bytes: 13200
- Lines: 385
- Classes (4): AsyncIngestionOrchestrator, IngestionJob, IngestionMetrics, IngestionPhase
- Functions (16): __init__, __post_init__, __post_init__, _ingestion_loop, example_orchestrator, get_all_jobs, get_job_status, get_orchestrator_metrics, start, stop, submit_job, success_rate, throughput, to_dict, to_dict, wait_for_completion
- Imports (11): adaptive_controller, asyncio, dataclasses, datetime, distributed_queue, enum, ingest_workers, json, time, typing, uuid
- Module docstring preview: Async Ingestion Orchestrator - Production Pipeline Orchestration

## `ingestion/v2/src/async_workers.py`

- Size bytes: 20345
- Lines: 570
- Classes (0): 
- Functions (10): _bulk_insert_postgres, _bulk_insert_stub, _call, _flush_all_domains, _flush_domain, db_bulk_writer, embed_batch, embed_worker, minister_aggregator, reader_worker
- Imports (14): aiohttp, async_ingest_config, asyncio, asyncpg, concurrent.futures, config, ingest_metrics, json, logging, os, rate_controller, time, typing, vector_db
- Module docstring preview: Async worker implementations for multi-stage ingestion pipeline.

## `ingestion/v2/src/benchmark_harness.py`

- Size bytes: 14850
- Lines: 411
- Classes (4): BenchmarkHarness, BenchmarkPhase, BenchmarkResult, BenchmarkSuite
- Functions (22): __init__, add_result, avg_processing_time, example_benchmarks, get_measurement_results, get_results_by_phase, max_processing_time, median_processing_time, min_processing_time, p95_processing_time, p99_processing_time, print_summary, run_load_profile_benchmark, run_scaling_benchmark, run_test, save, save_results, success_rate, throughput_items_per_sec, to_dict, to_dict, to_json
- Imports (9): async_ingestion_orchestrator, asyncio, dataclasses, datetime, enum, json, statistics, time, typing
- Module docstring preview: Production Benchmarking Framework for Ingestion Pipeline

## `ingestion/v2/src/capital_allocation.py`

- Size bytes: 10545
- Lines: 297
- Classes (1): ScoreBundle
- Functions (9): _cosine, commit_memory, decision_gate, doctrine_diff, ingest_post_phase3, optimize_retrieval_indices, reinforce_feedback, score_event, weighted_sum
- Imports (8): dataclasses, json, math, memory_db, numpy, os, typing, vector_db
- Module docstring preview: Capital allocation layer (Phase 4-8) implementation. Implements the pseudocode provided for scoring, decision gate, memory commit, doctrine diff, reinforcement, and retrieval optimization. This module uses `memory_db.MemoryDB` as a backend. If Postgres isn't configured the MemoryDB will fall back to

## `ingestion/v2/src/chapter_splitter.py`

- Size bytes: 6169
- Lines: 215
- Classes (0): 
- Functions (3): fallback_split_by_headings, flush_buffer, split_chapters_with_ollama_streaming
- Imports (7): config, json, ollama_client, os, re, typing, utils
- Module docstring preview: Chapter boundary detection and text segmentation.

## `ingestion/v2/src/config.py`

- Size bytes: 6875
- Lines: 167
- Classes (0): 
- Functions (0): 
- Imports (1): os
- Module docstring preview: Configuration and constants for the ingestion pipeline.

## `ingestion/v2/src/demo_async_pipeline.py`

- Size bytes: 2430
- Lines: 74
- Classes (0): 
- Functions (2): main, stub_parse_func
- Imports (6): async_ingest_config, async_ingest_orchestrator, asyncio, os, sys, traceback
- Module docstring preview: Demo/test runner for async ingestion pipeline.

## `ingestion/v2/src/distributed_queue.py`

- Size bytes: 11406
- Lines: 351
- Classes (4): BaseQueue, InMemoryQueue, QueuedItem, RedisQueue
- Functions (32): __init__, __init__, __post_init__, can_retry, clear, clear, clear, create_queue, dequeue, dequeue, dequeue, enqueue, enqueue, enqueue, example_queue, init, mark_complete, mark_complete, mark_complete, mark_processing, mark_processing, mark_processing, peek, peek, peek, requeue_failed, requeue_failed, requeue_failed, size, size, size, to_dict
- Imports (7): abc, aioredis, asyncio, dataclasses, datetime, json, typing
- Module docstring preview: Distributed Queue Abstraction - Redis or In-Memory Implementation

## `ingestion/v2/src/doctrine_extractor.py`

- Size bytes: 17721
- Lines: 471
- Classes (0): 
- Functions (7): _extract_chunk_doctrine, _has_actionable_doctrine, _is_doctrine_structurally_valid, extract_doctrine, extract_texts_from_doc, reject_verbatim_quotes_inline, validate_doctrine_inline
- Imports (7): config, json, ollama_client, os, re, typing, utils
- Module docstring preview: Doctrine extraction and validation logic.

## `ingestion/v2/src/embeddings.py`

- Size bytes: 6789
- Lines: 218
- Classes (0): 
- Functions (3): doctrine_to_nodes, embed_nodes, normalize_doctrine
- Imports (8): concurrent.futures, config, json, ollama_client, os, re, typing, utils
- Module docstring preview: Embedding generation and node construction.

## `ingestion/v2/src/ingest_metrics.py`

- Size bytes: 3871
- Lines: 114
- Classes (1): IngestMetrics
- Functions (14): get_avg_db_latency, get_avg_embed_latency, get_avg_minister_latency, get_throughput, print_report, processed_chunks, record_db, record_dropped, record_embed, record_error, record_minister, record_processed, record_rate_limit, report
- Imports (4): collections, dataclasses, time, typing
- Module docstring preview: Metrics collection and reporting for async ingestion pipeline.

## `ingestion/v2/src/ingest_pipeline.py`

- Size bytes: 33923
- Lines: 829
- Classes (0): 
- Functions (12): _enrich_doctrines, _is_ingest_completed, _ministers_progress_cb, _parse_chunks_from_file, _try_reconstruct_doctrine, build_minister_memories, classify_chapter, doctrine_density, ingest_folder, phase2_progress, phase_3_5_progress_cb, run_full_ingest_with_resume
- Imports (24): argparse, async_doctrine_workers, async_ingest_config, async_ingest_orchestrator, asyncio, capital_allocation, chapter_splitter, concurrent.futures, config, doctrine_extractor, embeddings, functools, ingestion_kis_enhancer, json, minister_converter, ollama_client, os, pdf_extraction, progress_tracker, shutil, sys, traceback, typing, utils
- Module docstring preview: Main ingestion pipeline orchestrator.

## `ingestion/v2/src/ingest_workers.py`

- Size bytes: 11531
- Lines: 346
- Classes (5): PipelineOrchestrator, PipelineWorker, WorkerMetrics, WorkerPool, WorkerStage
- Functions (22): __init__, __init__, __init__, _worker_loop, add_stage, dequeue_item, enqueue_item, example_chunk_worker, example_embed_worker, example_pipeline, example_store_worker, get_all_metrics, get_metrics, process_batch, process_item, process_item, record_item, start, start, stop, stop, to_dict
- Imports (6): asyncio, dataclasses, enum, json, time, typing
- Module docstring preview: Async Ingestion Workers - Parallel Processing Pipeline

## `ingestion/v2/src/ingestion_config.py`

- Size bytes: 10638
- Lines: 359
- Classes (7): AdaptiveControllerPresets, EnvironmentConfig, HighThroughput, Local, RateLimitPresets, Standard, WorkerPoolConfig
- Functions (4): create_orchestrator_config, get_adaptive_config, get_environment_config, get_full_config
- Imports (3): adaptive_controller, dataclasses, json
- Module docstring preview: Production Ingestion Configuration

## `ingestion/v2/src/ingestion_kis_enhancer.py`

- Size bytes: 15157
- Lines: 444
- Classes (2): IngestionKISContext, IngestionKISEnhancer
- Functions (11): __init__, __init__, create_kis_enhanced_worker_wrapper, enhance_aggregation_stage, enhance_minister_doctrine, enhanced_worker, get_ingestion_statistics, record_ingestion_failure, record_ingestion_success, save_ingestion_logs, to_dict
- Imports (8): datetime, json, logging, ml.kis.knowledge_integration_system, ml.ml_orchestrator, os, sys, typing
- Module docstring preview: Ingestion Pipeline KIS Integration Layer Connects the async ingestion pipeline (Phase 3.5) with the ML Wisdom System. The ingestion pipeline processes doctrine books: 1. CHUNKING: Split documents into knowledge units 2. EMBEDDING: Create semantic vectors 3. AGGREGATION: ← Use KIS to enhance minister

## `ingestion/v2/src/integration_examples.py`

- Size bytes: 10594
- Lines: 325
- Classes (1): IngestionConfig
- Functions (11): __init__, async_ingest_books, benchmark_async_vs_sync, convert_existing_parser, deploy_with_config, dummy_parser, from_json, ingest_and_process_capital_allocation, ingest_with_monitoring, to_json, wrapper
- Imports (9): async_ingest_config, async_ingest_orchestrator, asyncio, capital_allocation, ingest_metrics, json, pathlib, time, typing
- Module docstring preview: Integration example: wiring async pipeline into existing ingestion system. This shows how to adapt the existing ingest_pipeline.py or minister_converter.py to use the new async architecture for 10-20x throughput improvement.

## `ingestion/v2/src/memory_db.py`

- Size bytes: 7609
- Lines: 221
- Classes (1): MemoryDB
- Functions (16): __init__, _ensure_stub, _read, _write, adjust_attention_priors, adjust_entity_weights, create_doctrine_patch, get_recent_embeddings, init_schema, insert_embedding, insert_memory, recompute_cluster_centroids, retrieve_related_beliefs, store_doctrine_version, update_memory_salience, update_topk_cache
- Imports (4): json, os, typing, uuid
- Module docstring preview: Memory DB interface and schema for Phase 4-8 (Postgres + pgvector). Provides a light-weight fallback (file-backed) implementation when Postgres or psycopg2 isn't available so the rest of the pipeline can be exercised locally without external services.

## `ingestion/v2/src/minister_converter.py`

- Size bytes: 13119
- Lines: 359
- Classes (0): 
- Functions (5): add_category_entry, convert_all_doctrines, ensure_minister_structure, process_chapter_doctrine, update_combined_vector_index
- Imports (8): concurrent.futures, functools, json, os, pathlib, tempfile, typing, uuid
- Module docstring preview: Phase 3.5: Minister Conversion - Converts extracted doctrine to domain-specific minister structure.

## `ingestion/v2/src/minister_vector_db.py`

- Size bytes: 6909
- Lines: 215
- Classes (1): MinisterVectorDB
- Functions (7): __init__, close, connect, init_schema, insert_combined_embedding, search_by_domain, search_combined
- Imports (2): pgvector.psycopg2, psycopg2
- Module docstring preview: PostgreSQL + pgvector schema for minister vector database. This module defines the database schema for storing minister embeddings at both combined and domain-specific levels.

## `ingestion/v2/src/ollama_client.py`

- Size bytes: 7265
- Lines: 184
- Classes (1): OllamaClient
- Functions (4): __init__, call_json_llm_strict, embed, generate
- Imports (6): config, json, os, requests, subprocess, typing
- Module docstring preview: Ollama LLM client wrapper.

## `ingestion/v2/src/pdf_extraction.py`

- Size bytes: 2522
- Lines: 78
- Classes (0): 
- Functions (3): extract_pdf_pages, looks_glyph_encoded, repair_glyph_text
- Imports (5): logging, os, pypdf, typing, unicodedata
- Module docstring preview: PDF extraction helpers for v2.

## `ingestion/v2/src/progress_tracker.py`

- Size bytes: 2896
- Lines: 106
- Classes (0): 
- Functions (2): live_progress, update_progress
- Imports (4): json, os, time, typing
- Module docstring preview: Progress tracking and reporting utilities.

## `ingestion/v2/src/quickstart.py`

- Size bytes: 10693
- Lines: 320
- Classes (0): 
- Functions (5): example_basic_ingestion, example_custom_configuration, example_error_handling, example_with_benchmarks, main
- Imports (10): adaptive_controller, async_ingestion_orchestrator, asyncio, benchmark_harness, distributed_queue, ingestion_config, json, pathlib, sys, traceback
- Module docstring preview: Quick Start Example: Production Async Ingestion Pipeline This script demonstrates: 1. Creating an async ingestion orchestrator 2. Submitting ingestion jobs 3. Processing through the pipeline 4. Running benchmarks 5. Collecting metrics

## `ingestion/v2/src/rate_controller.py`

- Size bytes: 4603
- Lines: 128
- Classes (1): AdaptiveRateController
- Functions (10): __init__, _update_semaphore, acquire, adjust, get_status, record_error, record_rate_limit, record_success, release, sleep_backoff
- Imports (3): async_ingest_config, asyncio, typing
- Module docstring preview: Adaptive rate limiting controller for LLM embedding calls.

## `ingestion/v2/src/utils.py`

- Size bytes: 3935
- Lines: 153
- Classes (0): 
- Functions (7): chunk_text, dedupe_list, infer_domains_from_text, is_glyph_stream, looks_glyph_encoded, sha, text_quality_score
- Imports (6): config, hashlib, json, re, typing, unicodedata
- Module docstring preview: Utility functions for text processing, hashing, and validation.

## `ingestion/v2/src/vector_db.py`

- Size bytes: 6957
- Lines: 197
- Classes (1): VectorDBStub
- Functions (11): __init__, _cosine, _read, _write, insert_combined, insert_combined_batch, insert_domain, insert_domain_batch, search_combined, search_domain, validate_domain
- Imports (5): json, os, threading, typing, uuid
- Module docstring preview: Vector DB schema and helper functions for combined and per-domain embeddings. Provides SQL schema strings for Postgres + pgvector and a file-backed stub implementation for local testing and retrieval.

## `ingestion/v2/src/verify_installation.py`

- Size bytes: 5468
- Lines: 190
- Classes (0): 
- Functions (0): 
- Imports (7): async_ingest_config, async_ingest_orchestrator, ingest_metrics, os, pathlib, rate_controller, sys
- Module docstring preview: Verification script: confirms all async pipeline components are in place. Run this to validate installation before integrating into your system.

## `llm/__init__.py`

- Size bytes: 318
- Lines: 11
- Classes (0): 
- Functions (0): 
- Imports (1): ollama
- Module docstring preview: LLM interaction and interactive conversation modules. Provides: - OllamaRuntime: local Ollama CLI wrapper for model calls - OllamaModelSelector: interactive model picker - Interactive conversation terminals for USER↔LLM and USER↔Persona

## `llm/interactive_llm_conversation.py`

- Size bytes: 7468
- Lines: 223
- Classes (2): LLMPersona, LLMUser
- Functions (7): __init__, __init__, generate_next_input, main, print_header, print_turn, respond
- Imports (8): datetime, os, persona.context, persona.ollama_runtime, persona.state, sys, time, traceback
- Module docstring preview: INTERACTIVE LLM CONVERSATION: Both User and Persona use LLM Watch a real conversation unfold in real-time with both sides using AI.

## `llm/interactive_persona_chat.py`

- Size bytes: 1720
- Lines: 59
- Classes (0): 
- Functions (1): interactive_chat
- Imports (4): os, persona.state, persona_mas_integration_simple, sys
- Module docstring preview: Interactive Persona Chat - Talk directly with Persona in terminal

## `llm/ollama.py`

- Size bytes: 1489
- Lines: 38
- Classes (0): 
- Functions (2): chat, list
- Imports (1): subprocess
- Module docstring preview: Local shim for Ollama CLI to satisfy persona.ollama_runtime imports. Provides minimal `list()` and `chat()` functions used by the persona package. This avoids needing a separate Python `ollama` package and calls the installed `ollama` CLI instead. Output is decoded with replacement to avoid decoding

## `llm/ollama_model_selector.py`

- Size bytes: 2375
- Lines: 81
- Classes (0): 
- Functions (2): list_models, select_models
- Imports (3): shutil, subprocess, typing
- Module docstring preview: Small helper to list installed Ollama models and pick two. Functions: - list_models(): returns list of model names (strings) - select_models(preferred: list[str]|None): returns (user_model, program_model) Behavior: - If `ollama` CLI not found, returns empty list - If fewer than 2 models installed, r

## `llm_conversation.py`

- Size bytes: 9367
- Lines: 276
- Classes (1): LLMConversation
- Functions (7): __init__, _display_conversation, _save_conversation, demo_conversation, main, run_interactive, start_conversation
- Imports (6): argparse, datetime, json, pathlib, persona.ollama_runtime, sys
- Module docstring preview: Direct LLM-to-LLM Conversation Engine Enables User LLM (deepseek-r1:8b) and Program LLM (qwen3:14b) to have natural back-and-forth conversations on any topic. Usage: python llm_conversation.py # Interactive mode python llm_conversation.py --topic "..." # Specific topic python llm_conversation.py --r

## `ml/QUICKSTART.py`

- Size bytes: 11232
- Lines: 328
- Classes (0): 
- Functions (5): example_1_basic_kis, example_2_features_and_labels, example_3_ml_learning, example_4_orchestrator, main
- Imports (8): ml.features.feature_extractor, ml.judgment.ml_judgment_prior, ml.kis.knowledge_integration_system, ml.labels.label_generator, ml.ml_orchestrator, os, sys, traceback
- Module docstring preview: Quick Start Guide - ML Wisdom System This guide shows you how to get the ML system working in 10 minutes. Example: Decide whether to quit a job

## `ml/__init__.py`

- Size bytes: 1763
- Lines: 75
- Classes (0): 
- Functions (0): 
- Imports (6): features.feature_extractor, judgment.ml_judgment_prior, kis.knowledge_integration_system, labels.label_generator, llm_handshakes.llm_interface, ml_orchestrator
- Module docstring preview: ML Wisdom System Package Integrates Knowledge Integration System (KIS) with machine learning judgment priors to enable wise decision-making that learns from consequences. Main Components: - KIS: Multi-factor knowledge scoring - Features: Vectorization of situations - Labels: Outcome-based training -

## `ml/darbar.py`

- Size bytes: 1609
- Lines: 47
- Classes (0): 
- Functions (1): darbar_debate
- Imports (1): typing
- Module docstring preview: DARBAR hierarchical debate helper. Provides `darbar_debate` which runs multiple minister prompts and then asks a sovereign to synthesize the final decision.

## `ml/doctrine_update.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `ml/features/__init__.py`

- Size bytes: 666
- Lines: 30
- Classes (0): 
- Functions (0): 
- Imports (1): feature_extractor
- Module docstring preview: Feature Extraction Module

## `ml/features/feature_extractor.py`

- Size bytes: 10626
- Lines: 328
- Classes (10): ActionState, ActionType, Agency, ConstraintState, DecisionType, KISOutput, OutcomeState, RiskLevel, SituationState, TimeHorizon
- Functions (9): build_feature_vector, clamp, extract_action_features, extract_constraint_features, extract_knowledge_features, extract_situation_features, feature_vector_to_list, get_feature_names, safe_divide
- Imports (5): dataclasses, datetime, enum, math, typing
- Module docstring preview: Feature Extraction for ML Judgment Learning Extracts structured feature vectors from decision situations, knowledge usage, and actions for ML training and inference. Feature Contract: All values are numeric, bounded, deterministic. No text embedding. No floating variables.

## `ml/judgment/__init__.py`

- Size bytes: 175
- Lines: 12
- Classes (0): 
- Functions (0): 
- Imports (1): ml_judgment_prior
- Module docstring preview: ML Judgment Prior Module

## `ml/judgment/ml_judgment_prior.py`

- Size bytes: 8799
- Lines: 260
- Classes (2): MLJudgmentPrior, MLModelState
- Functions (9): __init__, add_training_sample, apply_ml_bias, compute_situation_hash, load, predict_prior, reset, save, train
- Imports (5): dataclasses, json, math, os, typing
- Module docstring preview: ML Judgment Prior Layer Learns from decision outcomes to biases KIS scoring toward knowledge types that repeatedly succeed in similar situations. Uses simple, interpretable models (no deep learning). Stays bounded and sovereign.

## `ml/kis/__init__.py`

- Size bytes: 299
- Lines: 16
- Classes (0): 
- Functions (0): 
- Imports (1): knowledge_integration_system
- Module docstring preview: KIS (Knowledge Integration System) Module

## `ml/kis/knowledge_integration_system.py`

- Size bytes: 15895
- Lines: 462
- Classes (5): KISRequest, KISResult, KnowledgeEntry, KnowledgeIntegrationSystem, KnowledgeType
- Functions (12): __init__, _empty_result, compute_context_weight, compute_domain_weight, compute_goal_weight, compute_memory_weight, compute_type_weight, extract_keywords, load_builtin_entries, load_knowledge_entries, synthesize_knowledge, to_dict
- Imports (7): dataclasses, enum, json, math, os, re, typing
- Module docstring preview: Knowledge Integration System (KIS) - Core Engine Multi-factor scoring algorithm that synthesizes domain-relevant knowledge from a distributed knowledge base. Ranks knowledge items using 5 independent weight factors. Location: c:\era\ml\kis\knowledge_integration_system.py

## `ml/labels/__init__.py`

- Size bytes: 330
- Lines: 18
- Classes (0): 
- Functions (0): 
- Imports (1): label_generator
- Module docstring preview: Label Generation Module

## `ml/labels/label_generator.py`

- Size bytes: 9449
- Lines: 273
- Classes (1): TypeWeights
- Functions (10): assess_severity, build_training_row, clamp, compute_label_certainty, generate_type_weights, interpret_outcome, log_label_decision, summarize_knowledge_usage, to_dict, to_list
- Imports (3): dataclasses, math, typing
- Module docstring preview: Label Generation for ML Judgment Learning Converts decision outcomes into training labels that tell the ML model "What kind of knowledge should have mattered more or less in situations like this?" This mirrors how humans learn judgment: from consequences, not advice.

## `ml/llm_handshakes/__init__.py`

- Size bytes: 484
- Lines: 22
- Classes (0): 
- Functions (0): 
- Imports (1): llm_interface
- Module docstring preview: LLM Handshakes Module

## `ml/llm_handshakes/llm_interface.py`

- Size bytes: 16353
- Lines: 495
- Classes (6): ConstraintExtractionOutput, CounterfactualOption, CounterfactualSketchOutput, IntentDetectionOutput, LLMInterface, SituationFrameOutput
- Functions (7): __init__, call_1_situation_framing, call_2_constraint_extraction, call_3_counterfactual_sketch, call_4_intent_detection, call_llm, run_handshake_sequence
- Imports (8): dataclasses, ingestion.v2.src.config, ingestion.v2.src.ollama_client, json, os, sys, time, typing
- Module docstring preview: LLM Handshakes - Structured Calls with Bounded Authority The LLM is a sensor only, not a decision-maker. It provides: 1. Situation classification (hard) 2. Constraint extraction (critical) 3. Counterfactual sketching (bounded) 4. Intent & bias detection (optional) All outputs are structured, bounded

## `ml/minister_retraining.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `ml/ml_orchestrator.py`

- Size bytes: 14653
- Lines: 371
- Classes (1): MLWisdomOrchestrator
- Functions (11): __init__, _assess_quality, _avg_kis_by_type, _extract_features_from_llm, _extract_kis_features, load_session, process_decision, process_interaction, record_outcome, run_training_cycle, save_session
- Imports (8): datetime, features.feature_extractor, json, labels.label_generator, os, outcomes.outcome_recorder, reward_shaping, typing
- Module docstring preview: ML Wisdom System Orchestrator Integrates all components: - LLM handshakes (sensing) - Feature extraction (vectorization) - KIS (knowledge ranking) - ML judgment priors (learned bias) - Label generation (training) - Outcome recording (feedback loop) Provides end-to-end pipeline from decision input to

## `ml/outcomes/__init__.py`

- Size bytes: 268
- Lines: 14
- Classes (0): 
- Functions (0): 
- Imports (1): outcome_recorder
- Module docstring preview: Outcome recording and training data collection.

## `ml/outcomes/outcome_recorder.py`

- Size bytes: 14743
- Lines: 434
- Classes (3): FeedbackIntegrator, OutcomeDatabase, TrainingDataGenerator
- Functions (16): __init__, __init__, __init__, _generate_decision_key, _load_index, _save_index, _save_trained_model, apply_learned_weights, generate_training_dataset, get_all_decisions_with_outcomes, get_decision, get_statistics, record_decision, record_outcome, run_training_cycle, save_training_dataset
- Imports (7): datetime, hashlib, json, labels.label_generator, os, pathlib, typing
- Module docstring preview: Outcome Recording Module - Step 4: Training Data Collection Records decision outcomes and persists them for ML training. Pipeline: 1. Decision made → stored in memory 2. Outcome observed → recorded to database 3. Training data generated → fed to ML models 4. Learned weights → applied back to system

## `ml/pattern_extraction.py`

- Size bytes: 11024
- Lines: 282
- Classes (1): PatternExtractor
- Functions (11): __init__, _avg_strength, _compute_pattern_stats, _extract_confidence_patterns, _extract_domain_patterns, _extract_outcome_patterns, _extract_sequential_patterns, extract_patterns, generate_learning_signals, identify_weak_patterns, save_patterns
- Imports (4): collections, datetime, json, typing
- Module docstring preview: Pattern Extraction: Identifies decision patterns and failure trends. Feeds learning signals to system retraining modules.

## `ml/quick_test_ml.py`

- Size bytes: 3514
- Lines: 115
- Classes (0): 
- Functions (0): 
- Imports (8): ml_integrated_conversation, pathlib, persona.domain_detector, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.ollama_runtime, persona.session_manager, sys
- Module docstring preview: Quick test of ML-integrated conversation system

## `ml/reward_shaping.py`

- Size bytes: 819
- Lines: 24
- Classes (0): 
- Functions (1): reward_function
- Imports (1): typing
- Module docstring preview: Mode-specific reward shaping utilities.

## `ml/sovereign_orchestrator.py`

- Size bytes: 25136
- Lines: 581
- Classes (1): SovereignOrchestrator
- Functions (10): __init__, _correct_mode_violation, _force_correction_with_acknowledgment, _generate_report, apply_ablation_config, attach_pwm, enable_evaluation_mode, get_state_snapshot, initialize_synthetic_human, run_turn
- Imports (16): analytics.dashboard, hse.simulation.human_persona_adapter, hse.simulation.stress_orchestrator, hse.simulation.synthetic_human_sim, ml.system_retraining, persona.learning.confidence_model, persona.learning.consequence_engine, persona.learning.episodic_memory, persona.learning.failure_analysis, persona.learning.outcome_feedback_loop, persona.learning.performance_metrics, persona.modes.mode_orchestrator, persona.persistence.conversation_arc, persona.pwm_integration.pwm_bridge, persona.validation.identity_validator, persona.validation.mode_validator
- Module docstring preview: Complete integration of all learning, validation, and feedback systems. Orchestrates: Memory, Metrics, Feedback, Validation, Retraining, Dashboard, Stress Testing

## `ml/system_retraining.py`

- Size bytes: 2981
- Lines: 93
- Classes (1): SystemRetraining
- Functions (6): __init__, encode_learned_doctrine, extract_success_patterns, rebalance_kis_weights, retrain_llm_if_local, update_minister_confidence_formulas
- Imports (1): collections

## `ml/test_ml_learning_loop.py`

- Size bytes: 6215
- Lines: 150
- Classes (0): 
- Functions (2): demonstrate_pattern_query, test_learning_processor
- Imports (3): json, pathlib, persona_learning_processor
- Module docstring preview: Test ML Learning Loop Integration Verify that: 1. Conversations are properly analyzed 2. Learning insights are persisted 3. Weak domains are identified 4. Recommendations are generated

## `ml/tests/__init__.py`

- Size bytes: 137
- Lines: 7
- Classes (0): 
- Functions (0): 
- Imports (0): 
- Module docstring preview: Test Suite for ML Wisdom System

## `ml/tests/test_ml_wisdom.py`

- Size bytes: 14091
- Lines: 405
- Classes (5): TestEndToEnd, TestFeatureExtraction, TestKISWeights, TestLabelGeneration, TestMLJudgmentPrior
- Functions (18): setUp, test_advice_led_failure_penalizes_advice, test_build_feature_vector_bounds, test_context_weight_keyword_matching, test_domain_weight_active, test_domain_weight_inactive, test_execution_success_boosts_rules, test_extract_constraint_features, test_extract_situation_features, test_kis_respects_max_items, test_kis_synthesis_nonempty, test_learning_from_successes, test_memory_weight_logarithmic, test_model_persistence, test_neutral_before_training, test_severe_failure_boosts_warnings, test_type_weight_ranges, test_weights_stay_bounded
- Imports (10): features.feature_extractor, json, judgment.ml_judgment_prior, kis.knowledge_integration_system, labels.label_generator, os, sys, tempfile, typing, unittest
- Module docstring preview: ML Wisdom System Tests Validates all components: - Feature extraction (correctness, bounds) - Label generation (learning signals) - KIS scoring (multi-factor ranking) - ML judgment priors (learning behavior) - Integration (end-to-end)

## `ml/vector_memory.py`

- Size bytes: 2398
- Lines: 71
- Classes (1): VectorMemory
- Functions (3): __init__, add, search
- Imports (3): faiss, numpy, sentence_transformers

## `multi_agent_sim/__init__.py`

- Size bytes: 731
- Lines: 16
- Classes (0): 
- Functions (0): 
- Imports (4): agents, archetypes, logger, orchestrator
- Module docstring preview: Multi-agent LLM simulation package. Provides a safe orchestrator to run closed-loop simulations between two LLM agents. Entry points: - Orchestrator: class-based closed-loop agent orchestrator - OllamaAgent, MockAgent: agent implementations - terminal: interactive multi-agent terminal (run via `pyth

## `multi_agent_sim/__main__.py`

- Size bytes: 890
- Lines: 33
- Classes (0): 
- Functions (1): main
- Imports (1): sys
- Module docstring preview: Entry point for running multi_agent_sim as a module. Usage: python -m multi_agent_sim.terminal # run terminal directly python -m multi_agent_sim.run_terminal # run with auto model selection python -m multi_agent_sim.demo # run demo simulation

## `multi_agent_sim/agents.py`

- Size bytes: 1769
- Lines: 53
- Classes (3): BaseAgent, MockAgent, OllamaAgent
- Functions (7): __init__, __init__, __init__, _call_ollama, respond, respond, respond
- Imports (3): shlex, subprocess, typing
- Module docstring preview: agents.py Defines agent wrappers. OllamaAgent calls `ollama run` via subprocess by default. Also includes a MockAgent useful for offline tests.

## `multi_agent_sim/archetypes.py`

- Size bytes: 648
- Lines: 15
- Classes (0): 
- Functions (0): 
- Imports (0): 
- Module docstring preview: archetypes.py Predefined user archetype system prompts for simulation.

## `multi_agent_sim/demo.py`

- Size bytes: 953
- Lines: 22
- Classes (0): 
- Functions (1): demo_with_mocks
- Imports (5): agents, archetypes, logger, orchestrator, os
- Module docstring preview: Demo runner for the multi-agent simulation. Run from the workspace root with Python to see a basic simulation using MockAgents or OllamaAgents if available.

## `multi_agent_sim/logger.py`

- Size bytes: 1061
- Lines: 34
- Classes (1): ConversationLogger
- Functions (4): __init__, append, clear, get_transcript
- Imports (2): datetime, typing
- Module docstring preview: logger.py Conversation logger that writes transcript to file and keeps in-memory record.

## `multi_agent_sim/orchestrator.py`

- Size bytes: 2713
- Lines: 55
- Classes (1): Orchestrator
- Functions (4): __init__, _build_program_prompt, _build_user_prompt, run
- Imports (3): agents, logger, typing
- Module docstring preview: orchestrator.py Implements the turn-based orchestrator that mediates between two agents. Provides safety: agents never see each other directly; orchestrator controls prompts, memory injection, logging, and termination.

## `multi_agent_sim/run_terminal.py`

- Size bytes: 2327
- Lines: 66
- Classes (0): 
- Functions (1): main
- Imports (6): argparse, llm.ollama_model_selector, os, pathlib, subprocess, sys
- Module docstring preview: Wrapper to auto-select two Ollama models and run the multi-agent terminal. Usage: python -m multi_agent_sim.run_terminal # runs and launches orchestrator python -m multi_agent_sim.run_terminal --dry-run # prints detected models and exits It sets env vars `USER_MODEL` and `PROGRAM_MODEL` for `termina

## `multi_agent_sim/simulation_runner.py`

- Size bytes: 6951
- Lines: 197
- Classes (1): DryRunLLM
- Functions (5): __init__, _load_dotenv_fallback, _load_env, main, speak
- Imports (13): __future__, argparse, datetime, dotenv, hse.human_profile, hse.simulation, os, pathlib, persona.council, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.ollama_runtime, sys
- Module docstring preview: Run bidirectional LLM simulation: User LLM <-> Persona LLM. No human typing is required in normal mode.

## `multi_agent_sim/terminal.py`

- Size bytes: 8181
- Lines: 255
- Classes (0): 
- Functions (3): call_model, check_ollama_available, main
- Imports (7): datetime, os, shutil, subprocess, sys, threading, time
- Module docstring preview: High-Control Multi-Agent Terminal Orchestrator Features: - Per-call timeout guard (kills model process on timeout) - Optional live streaming of model output - Optional conversation logging to `conversation.log` - Clean separators, turn numbers, graceful Ctrl-C handling Run: python -m multi_agent_sim

## `persona/__init__.py`

- Size bytes: 240
- Lines: 17
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `persona/analysis.py`

- Size bytes: 17303
- Lines: 438
- Classes (0): 
- Functions (10): _heuristic_domain_guess, _normalize_float, _safe_parse_json, assess_coherence, assess_emotional_metrics, assess_mode_fitness, assess_situation, assess_situation_heuristic, classify_domains, generate_clarifying_questions
- Imports (5): __future__, json, re, trace, typing
- Module docstring preview: persona/analysis.py Comprehensive LLM-driven analysis handshakes used by the persona runtime. Provides small, robust wrappers around LLM calls and a keyword fallback for domain classification. Functions are defensive, attempt to recover from malformed LLM output, and emit traces via `trace()` so the

## `persona/brain.py`

- Size bytes: 2062
- Lines: 49
- Classes (2): ControlDirective, PersonaBrain
- Functions (1): decide
- Imports (3): dataclasses, logging, typing
- Module docstring preview: PersonaBrain (clean) — pure control layer Minimal controller for deciding whether the assistant should `pass`, `halt`, `suppress` or remain `silence`. No I/O, no LLM calls, no state mutation.

## `persona/cache_manager.py`

- Size bytes: 9712
- Lines: 276
- Classes (1): CacheManager
- Functions (9): __init__, cleanup_by_size, cleanup_old_files, get_cache_report, get_cache_size, main, print_report, run_cleanup, validate_cache_dirs
- Imports (7): datetime, json, os, pathlib, shutil, time, typing
- Module docstring preview: Cache Cleanup & Rotation Policy for ERA System Implements automatic cleanup of old cache files to prevent disk space issues. Runs on system startup and periodically during operation.

## `persona/clarify.py`

- Size bytes: 3406
- Lines: 92
- Classes (0): 
- Functions (3): _trace_event, build_clarifying_question, format_question_for_user
- Imports (2): trace, typing
- Module docstring preview: persona/clarify.py Builds user-facing clarification prompts from a ControlDirective and state. This implementation is defensive: it accepts generic objects and will attempt to trace events using available `trace` functions when possible.

## `persona/context.py`

- Size bytes: 4847
- Lines: 136
- Classes (0): 
- Functions (4): build_system_context, enforce_frequency, estimate_user_frequency, trim_response
- Imports (3): pathlib, trace, yaml

## `persona/council.py`

- Size bytes: 8472
- Lines: 193
- Classes (2): CouncilAggregator, CouncilRecommendation
- Functions (2): __init__, convene
- Imports (4): dataclasses, ministers, trace, typing
- Module docstring preview: Council Aggregator - Coordinates Minister outputs and produces consensus recommendations. Aggregates individual minister stances into a coherent council recommendation that Prime Confident can use for final decision-making.

## `persona/council/__init__.py`

- Size bytes: 1061
- Lines: 37
- Classes (0): 
- Functions (1): _load_legacy_council
- Imports (4): dynamic_council, importlib.util, pathlib, sys
- Module docstring preview: Council package exports. This package coexists with the legacy ``persona/council.py`` module. Because the package shadows that module name, we explicitly load the legacy module and re-export its public classes here for backwards compatibility.

## `persona/council/dynamic_council.py`

- Size bytes: 8958
- Lines: 236
- Classes (1): DynamicCouncil
- Functions (8): __init__, _convene_mode_council, _determine_recommendation, convene_for_mode, get_current_mode, get_mode_description, list_available_modes, set_mode
- Imports (2): modes.mode_orchestrator, typing
- Module docstring preview: Dynamic Council - Adjusts behavior based on conversation mode and ministers involved. This module wraps CouncilAggregator with mode-aware council behavior, allowing the council composition and aggregation logic to change based on the selected mode (QUICK, WAR, MEETING, or DARBAR).

## `persona/doctrine_loader.py`

- Size bytes: 6191
- Lines: 167
- Classes (2): DoctrinalCanon, DoctrineLoader
- Functions (4): extract_warnings, extract_worldview_keywords, load, should_speak_based_on_doctrine
- Imports (4): dataclasses, os, typing, yaml
- Module docstring preview: Doctrine Loader - Reads and parses YAML doctrine files for ministers and Prime Confident. Each doctrine file contains: - role_type: "minister" or "confidant" - persona.canon: Core worldview and mental models - doctrine: Purpose, authority, triggers, failure modes, and scope

## `persona/domain_detector.py`

- Size bytes: 9152
- Lines: 267
- Classes (0): 
- Functions (8): analyze_situation, analyze_with_llm, detect_domains_by_keywords, detect_reversibility, detect_stakes, domain_similarity, extract_key_entities, extract_keywords_from_text
- Imports (3): pathlib, re, typing
- Module docstring preview: Domain Detection System Parses problem statements to extract active domains using: - Keyword matching against domain dictionaries - LLM-based situation analysis (via OllamaRuntime) - Context inference from previous sessions

## `persona/knowledge_engine.py`

- Size bytes: 21279
- Lines: 551
- Classes (0): 
- Functions (15): _clean_book_name, _detect_contradictions, _semantic_label_similarity, applies_applicability, apply_ml_judgment_prior, compute_kis, context_weight, domain_weight, extract_keywords, generate_diagnosis_counterfactual_synthesis, goal_weight, load_domain_knowledge, load_json_safe, memory_weight, synthesize_knowledge
- Imports (6): datetime, json, math, os, re, typing

## `persona/learning/__init__.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `persona/learning/confidence_model.py`

- Size bytes: 1058
- Lines: 39
- Classes (1): BayesianConfidence
- Functions (5): __init__, get_confidence, get_uncertainty, summary, update
- Imports (1): collections

## `persona/learning/consequence_engine.py`

- Size bytes: 2278
- Lines: 85
- Classes (1): ConsequenceEngine
- Functions (4): __init__, _estimate_severity, register_decision, tick
- Imports (2): datetime, random

## `persona/learning/episodic_memory.py`

- Size bytes: 5459
- Lines: 141
- Classes (2): Episode, EpisodicMemory
- Functions (11): __init__, __post_init__, _persist, detect_failure_clusters, detect_pattern_repetition, find_similar_episodes, get_recent_episodes, get_success_rate, load_from_disk, record_consequence, store_episode
- Imports (5): dataclasses, datetime, json, typing, uuid
- Module docstring preview: Episodic Memory: Stores decisions, outcomes, and consequences for learning. This is your PRIMARY LEARNING SYSTEM.

## `persona/learning/failure_analysis.py`

- Size bytes: 3857
- Lines: 107
- Classes (1): FailureAnalysis
- Functions (5): __init__, _analyze_kis_error, _analyze_minister_error, _consensus_was_flawed, analyze_failure
- Imports (0): 

## `persona/learning/outcome_feedback.py`

- Size bytes: 3261
- Lines: 84
- Classes (1): OutcomeFeedbackLoop
- Functions (5): __init__, detect_repeated_mistake, record_decision_outcome, retrain_ministers, update_kis_weights
- Imports (2): episodic_memory, typing
- Module docstring preview: Outcome Feedback Loop: Connects decisions to actual outcomes. Updates minister confidence and KIS weights based on results.

## `persona/learning/outcome_feedback_loop.py`

- Size bytes: 4449
- Lines: 133
- Classes (1): OutcomeFeedbackLoop
- Functions (7): __init__, _adjust_ministers, _update_doctrine_effectiveness, doctrine_report, record_decision_outcome, retrain_ministers, update_kis_weights
- Imports (2): collections, datetime

## `persona/learning/performance_metrics.py`

- Size bytes: 5422
- Lines: 137
- Classes (1): PerformanceMetrics
- Functions (9): __init__, _persist, detect_weak_domains, get_feature_coverage, get_success_rate, load_from_disk, measure_stability, record_decision, show_improvement_trajectory
- Imports (4): collections, datetime, json, typing
- Module docstring preview: Performance Metrics: Track decision quality, success rates, feature coverage. Identifies weak domains and improvement opportunities.

## `persona/main.py`

- Size bytes: 42911
- Lines: 841
- Classes (0): 
- Functions (4): _background_analysis, _mca_decision, main, validate_mode_coherence
- Imports (26): analysis, brain, clarify, concurrent.futures, context, council, council.dynamic_council, hse.human_profile, hse.simulation.synthetic_human_sim, json, knowledge_engine, learning.episodic_memory, learning.outcome_feedback, learning.performance_metrics, ml.pattern_extraction, modes.mode_metrics, modes.mode_orchestrator, ollama_runtime, os, sovereign.llm_adapter, sovereign.prime_confident, state, sys, trace, typing, validation.identity_validator
- Module docstring preview: Main interactive loop with clarifying-question integration. Key additions: - Creates a PersonaBrain and uses it to decide when to HALT and ask clarifying questions. - Calls situation/coherence handshakes synchronously (short) to provide the Brain with the info it needs immediately. - Asks clarifying

## `persona/ministers.py`

- Size bytes: 36851
- Lines: 901
- Classes (22): Minister, MinisterOfAdaptation, MinisterOfConflict, MinisterOfData, MinisterOfDiplomacy, MinisterOfDiscipline, MinisterOfGrandStrategy, MinisterOfIntelligence, MinisterOfLegitimacy, MinisterOfNarrative, MinisterOfOptionality, MinisterOfPower, MinisterOfPsychology, MinisterOfRisk, MinisterOfRiskResources, MinisterOfSovereign, MinisterOfTechnology, MinisterOfTiming, MinisterOfTribunal, MinisterOfTruth, MinisterOfWarMode, MinisterPosition
- Functions (25): __init__, _apply_prohibitions, _extract_stance_confidence, _score_worldview_match, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze, analyze
- Imports (6): abc, dataclasses, doctrine_loader, knowledge_engine, trace, typing
- Module docstring preview: Ministerial Cognitive Architecture (MCA) - Domain-specific decision advisors. Each Minister loads their doctrine from C:/era/data/doctrine/locked/*.yaml and analyzes user input through their canonical worldview and mental models. Doctrine includes: - Core worldview and mental models - Authority (wha

## `persona/modes/__init__.py`

- Size bytes: 755
- Lines: 33
- Classes (0): 
- Functions (0): 
- Imports (2): mode_metrics, mode_orchestrator
- Module docstring preview: Mode orchestration system for Persona. Controls decision pipeline based on conversation mode: - quick: Direct 1:1 mentoring (no council) - war: Victory-focused (Risk + Power + Strategy) - meeting: Structured debate (3-5 relevant ministers) - darbar: Full council wisdom (all 19 ministers)

## `persona/modes/mode_metrics.py`

- Size bytes: 6290
- Lines: 193
- Classes (1): ModeMetrics
- Functions (11): __init__, compare_modes, get_all_modes, get_best_mode, get_mode_performance, get_mode_summary, get_worst_mode, has_data_for_mode, record_mode_decision, reset_all, reset_mode
- Imports (2): collections, typing
- Module docstring preview: Mode-specific metrics tracking. Measure how well Persona performs in each mode: - QUICK mode: Fast, intuitive decisions - WAR mode: Victory-focused strategic decisions - MEETING mode: Balanced, consensus-seeking decisions - DARBAR mode: Full wisdom, doctrine-respecting decisions Tracks: - Decision c

## `persona/modes/mode_orchestrator.py`

- Size bytes: 23092
- Lines: 626
- Classes (9): DarbarModeStrategy, ExecutionConfig, MeetingModeStrategy, ModeOrchestrator, ModeResponse, ModeStrategy, QuickModeStrategy, UncertaintyPolicyConfig, WarModeStrategy
- Functions (37): __init__, _clamp01, aggregate_for_mode, aggregate_minister_inputs, aggregate_minister_inputs, aggregate_minister_inputs, aggregate_minister_inputs, aggregate_minister_inputs, apply_uncertainty_control, compute_composite_uncertainty, decide_ministers_to_invoke, decide_ministers_to_invoke, decide_ministers_to_invoke, decide_ministers_to_invoke, decide_ministers_to_invoke, frame_decision, frame_decision, frame_decision, frame_decision, frame_decision, frame_for_mode, get_current_mode, get_execution_plan, get_ministers_for_mode, get_mode_description, get_strategy, is_baseline_mode, list_modes, set_ablation_config, set_mode, set_uncertainty_predictor, should_invoke_council, should_invoke_council, should_invoke_council, should_invoke_council, should_invoke_council, should_invoke_council
- Imports (3): abc, dataclasses, typing
- Module docstring preview: MODE ORCHESTRATOR - Controls pipeline based on conversation mode. Different modes invoke different reasoning pathways: - QUICK MODE: 1:1 conversation, direct LLM response, no council - WAR MODE: Victory-focused, aggressive, Risk/Power/Strategy focus - MEETING MODE: Structured debate, 3-5 relevant mi

## `persona/ollama_runtime.py`

- Size bytes: 7394
- Lines: 180
- Classes (1): OllamaRuntime
- Functions (6): __init__, _extract_text, analyze, analyze_async, speak, speak_async
- Imports (4): concurrent.futures, ollama, os, time
- Module docstring preview: OllamaRuntime — runtime wrapper including the boot-time availability handshake. Handshakes implemented: - Boot-time ollama.list() availability check (hard fail unless SKIP_OLLAMA_CHECK=1) - analyze() and speak() functions (use configured models) - Deterministic sampling via temperature=0, top_p=1.0,

## `persona/persistence/__init__.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `persona/persistence/conversation_arc.py`

- Size bytes: 4942
- Lines: 153
- Classes (1): ConversationArc
- Functions (11): __init__, _is_conflicting, detect_decision_contradiction, detect_unresolved_loop, get_long_horizon_impact, record_decision, register_crisis, register_issue_reference, resolve_crisis, set_original_problem, track_decision_consequences
- Imports (2): collections, datetime

## `persona/persistence/memory_store.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `persona/persona_learning_processor.py`

- Size bytes: 20938
- Lines: 508
- Classes (1): ConversationLearningProcessor
- Functions (13): __init__, _analyze_conversation_quality, _analyze_domain_effectiveness, _extract_metrics, _extract_question_patterns, _generate_next_session_recommendations, _identify_weak_domains, _persist_learning, _print_learning_summary, _suggest_pattern, get_learned_patterns_for_domain, process_conversation, process_conversation_for_learning
- Imports (6): collections, datetime, json, os, pathlib, typing
- Module docstring preview: Post-Conversation ML Learning Processor After each conversation ends, analyze what was learned and extract improvements for future conversations. This closes the learning loop. Flow: 1. Conversation completes and stores Episode + Metrics 2. ML Processor analyzes: What worked? What didn't? 3. Extract

## `persona/persona_minister_kis_bridge.py`

- Size bytes: 13505
- Lines: 394
- Classes (1): MinisterKISBridge
- Functions (8): __init__, export_minister_logs, get_learning_summary, get_minister_context, get_minister_knowledge, minister_usage_example, record_minister_decision, record_outcome
- Imports (9): datetime, json, logging, ml.features.feature_extractor, ml.kis.knowledge_integration_system, ml.ml_orchestrator, os, sys, typing
- Module docstring preview: Minister KIS Integration Layer Wires the ML Wisdom System (KIS) into DARBAR minister decision-making. Each minister (risk, optionality, sovereignty, etc.) can now: 1. Request domain-specific knowledge synthesis 2. Shape their recommendations with KIS insights 3. Learn from outcomes to improve future

## `persona/pwm_integration/__init__.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `persona/pwm_integration/pwm_bridge.py`

- Size bytes: 16611
- Lines: 423
- Classes (1): PWMIntegrationBridge
- Functions (11): __init__, _commit_fact_to_pwm, _group_by_entity, _validate_entity_observations, _validate_single_observation, generate_validation_insights, get_pwm_facts_for_entity, get_validation_history, periodic_pwm_sync, queue_entity_observation, summary
- Imports (2): datetime, json
- Module docstring preview: PWM Integration Bridge - Proper Separation of Concerns This bridge manages ONE thing only: Converting validated observations into PWM facts. THREE SEPARATE SYSTEMS: 1. PWM (Knowledge Graph) — Slow, careful fact storage Purpose: "What proven facts do we know about people/relationships?" Update freque

## `persona/run_persona.py`

- Size bytes: 1285
- Lines: 41
- Classes (0): 
- Functions (1): _load_dotenv_fallback
- Imports (5): dotenv, os, pathlib, persona.main, sys

## `persona/run_persona_conversation.py`

- Size bytes: 1620
- Lines: 54
- Classes (0): 
- Functions (0): 
- Imports (4): os, persona.main, sys, traceback
- Module docstring preview: Launch Persona N with Synthetic Human Simulation This script starts the Persona system in automated simulation mode, where a synthetic user (powered by llama3.1:8b LLM) converses with Persona N (powered by qwen3:14b LLM) in real-time. The conversation demonstrates: - Mode-based decision orchestratio

## `persona/session_manager.py`

- Size bytes: 15512
- Lines: 412
- Classes (3): Session, SessionManager, SessionTurn
- Functions (16): __init__, _generate_session_id, _load_history, _save_session, add_turn, create_followup_session, end_session, find_related_sessions, get_session_context_for_continuity, get_session_statistics, load_consequences_for_session, record_consequence, record_satisfaction, should_escalate_mode, start_session, to_dict
- Imports (9): dataclasses, datetime, hashlib, json, os, pathlib, persona.domain_detector, time, typing
- Module docstring preview: Session Manager Manages multi-turn problem-solving sessions with: - Session lifecycle (start, track, conclude) - Consequence tracking (follow-up on previous outcomes) - Session replay (context from similar problems) - Problem continuity (related problems, follow-ups)

## `persona/state.py`

- Size bytes: 2879
- Lines: 61
- Classes (1): CognitiveState
- Functions (4): add_turn, get_recent_context, reset_for_new_conversation, update_domains
- Imports (2): dataclasses, typing

## `persona/test_session_workflow.py`

- Size bytes: 7478
- Lines: 210
- Classes (0): 
- Functions (5): test_consequence_tracking, test_domain_detection, test_session_continuity, test_session_management, test_statistics
- Imports (3): persona.domain_detector, persona.session_manager, traceback
- Module docstring preview: Test Session Workflow Validates: 1. Domain detection from problem statements 2. Session creation and management 3. Consequence tracking 4. Session continuity (follow-ups) 5. Session replay (related sessions)

## `persona/trace.py`

- Size bytes: 1716
- Lines: 57
- Classes (0): 
- Functions (3): _append_trace, print_trace, trace
- Imports (2): datetime, os
- Module docstring preview: Simple trace / observer utilities. Controlled via PERSONA_DEBUG environment var. Traces are no-op by default to avoid noisy output; turn on for debugging.

## `persona/validation/__init__.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `persona/validation/contradiction_detector.py`

- Size bytes: 0
- Lines: 0
- Classes (0): 
- Functions (0): 
- Imports (0): 

## `persona/validation/identity_validator.py`

- Size bytes: 3455
- Lines: 82
- Classes (1): IdentityValidator
- Functions (7): __init__, _extract_claims, _find_contradiction, check_self_contradiction, log_contradiction, record_teaching, validate_voice_consistency
- Imports (3): datetime, json, typing
- Module docstring preview: Identity Validator: Ensures Persona remains coherent and doesn't contradict itself.

## `persona/validation/mode_validator.py`

- Size bytes: 4670
- Lines: 149
- Classes (1): ModeValidator
- Functions (6): __init__, detect_mode_drift, inconsistency_score, mode_stability_score, record_mode, validate_response_mode_match
- Imports (2): collections, re

## `run_benchmark.py`

- Size bytes: 20807
- Lines: 501
- Classes (1): BenchmarkRunner
- Functions (8): __init__, _parse_model_response, _print_summary, _save_results, baseline_decision_engine, council_decision_engine, main, run_benchmark
- Imports (12): argparse, evaluation.evaluation_runner, evaluation.metrics.evaluation_metrics, evaluation.stats_engine, json, logging, os, pathlib, persona.ollama_runtime, re, sys, typing
- Module docstring preview: ERA Evaluation Benchmark Runner Research-grade evaluation with: - Deterministic LLM control (temperature=0, seed injection) - Rule-based deterministic scoring (zero LLM calls) - Dataset integrity verification - Isolation mode (no live system contamination) - 5-seed reproducibility - Statistical vali

## `run_eval_demo.py`

- Size bytes: 8759
- Lines: 216
- Classes (0): 
- Functions (1): run_demo
- Imports (10): evaluation.evaluation_runner, evaluation.scoring.outcome_scorer, evaluation.stats_engine, json, logging, numpy, os, pathlib, sys, typing
- Module docstring preview: ERA Evaluation Demo - Quick validation of research-grade framework Shows all major components without requiring full Ollama execution: - Dataset integrity verification - Isolation mode activation - Rule-based deterministic scoring - Statistical validation - Power analysis - Calibration diagnostics

## `scripts/STARTUP_GUIDE.py`

- Size bytes: 12043
- Lines: 396
- Classes (0): 
- Functions (0): 
- Imports (0): 
- Module docstring preview: =================================================================== 🚀 ML-INTEGRATED CONVERSATION SYSTEM - COMPLETE STARTUP GUIDE =================================================================== This is your complete LLM-to-LLM conversation system with integrated machine learning for continuous im

## `scripts/VISUAL_SUMMARY.py`

- Size bytes: 6767
- Lines: 168
- Classes (0): 
- Functions (8): print_banner, print_files_created, print_improvement_example, print_quick_start, print_result, print_storage, print_verification, print_what_happens
- Imports (0): 
- Module docstring preview: Visual Summary: ML Learning Loop Implementation Complete ✅ This shows what was delivered in response to your question: "After conversation it should go through ml layer and improve right?"

## `scripts/check_embed.py`

- Size bytes: 284
- Lines: 7
- Classes (0): 
- Functions (0): 
- Imports (1): ingestion.v2.src.ollama_client

## `scripts/check_ingestion_status.py`

- Size bytes: 1273
- Lines: 43
- Classes (0): 
- Functions (0): 
- Imports (3): json, os, pathlib
- Module docstring preview: Check successful ingestions with doctrine and embeddings.

## `scripts/check_models.py`

- Size bytes: 1324
- Lines: 35
- Classes (0): 
- Functions (0): 
- Imports (3): importlib.util, os, sys
- Module docstring preview: Diagnostic: check which model the pipeline is actually using for doctrine extraction.

## `scripts/check_ollama_api.py`

- Size bytes: 437
- Lines: 18
- Classes (0): 
- Functions (0): 
- Imports (1): requests

## `scripts/check_requirements.py`

- Size bytes: 897
- Lines: 35
- Classes (0): 
- Functions (0): 
- Imports (0): 
- Module docstring preview: Quick environment verification script for ingestion pipeline. Run: python scripts/check_requirements.py It will attempt to import key packages and report success/failure so you can confirm `pip install -r requirements.txt` completed correctly.

## `scripts/ingest_status.py`

- Size bytes: 2705
- Lines: 68
- Classes (0): 
- Functions (0): 
- Imports (3): json, os, pathlib
- Module docstring preview: Comprehensive ingestion status report.

## `scripts/run_embed_only.py`

- Size bytes: 855
- Lines: 20
- Classes (0): 
- Functions (1): run_once
- Imports (7): asyncio, ingestion.v2.src.async_ingest_orchestrator, ingestion.v2.src.config, ingestion.v2.src.ingest_pipeline, ingestion.v2.src.ollama_client, os, sys

## `scripts/scan_rag_storage.py`

- Size bytes: 2010
- Lines: 51
- Classes (0): 
- Functions (1): summarize_doctrine
- Imports (3): json, os, pathlib
- Module docstring preview: Scan rag_storage directories and summarize doctrine extraction counts.

## `scripts/stream_persona_live.py`

- Size bytes: 3801
- Lines: 109
- Classes (0): 
- Functions (4): append_log, call_user_model, main, safe_print
- Imports (10): hse.human_profile, json, os, pathlib, persona.context, persona.ollama_runtime, persona.state, subprocess, sys, time
- Module docstring preview: Stream a USER <-> PROGRAM (persona) conversation to the terminal and save to logs. Usage: run from repo root: python scripts/stream_persona_live.py This script runs a short automated streaming session (5 turns) where the USER is generated by a USER_MODEL via the `ollama` CLI and the PROGRAM is the p

## `sovereign/council/aggregator.py`

- Size bytes: 2018
- Lines: 46
- Classes (1): CouncilAggregator
- Functions (2): __init__, evaluate
- Imports (1): typing
- Module docstring preview: Simple Council Aggregator that evaluates minister outputs and decides whether consensus exists.

## `sovereign/llm_adapter.py`

- Size bytes: 5508
- Lines: 119
- Classes (1): OllamaAdapter
- Functions (8): __init__, analyze, analyze_async, evaluate_viability, generate, speak, speak_async, summarize
- Imports (6): concurrent.futures, json, persona.ollama_runtime, persona.trace, re, typing
- Module docstring preview: Simple Ollama LLM adapter used by sovereign flows. Provides a small adapter API: `generate`, `summarize`, `evaluate_viability`. Wraps `persona.ollama_runtime.OllamaRuntime` when available, with a safe fallback for unit tests or when Ollama isn't running.

## `sovereign/ministers/__init__.py`

- Size bytes: 5610
- Lines: 151
- Classes (2): MinisterModule, MinisterModuleOutput
- Functions (5): __init__, analyze, create_minister_module, generate_kis, invoke_with_prime
- Imports (5): dataclasses, persona.knowledge_engine, persona.ministers, persona.trace, typing
- Module docstring preview: Minister Modules - Individual domain-specific modules for each minister. Each minister is isolated into its own module that: 1. Loads and executes its minister role 2. Generates KIS (Knowledge Integration System) for its domain 3. Connects to Prime Confident flow for decision finalization LOCATION: 

## `sovereign/ministers/adaptation.py`

- Size bytes: 1222
- Lines: 36
- Classes (1): AdaptationModule
- Functions (3): __init__, generate_kis, get_adaptation_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Adaptation Module - Change and system evolution.

## `sovereign/ministers/base_minister.py`

- Size bytes: 1268
- Lines: 37
- Classes (1): BaseMinister
- Functions (2): __init__, produce_advice
- Imports (1): typing
- Module docstring preview: Base minister interface for MCA. Ministers must produce a structured, non-prose output contract.

## `sovereign/ministers/conflict.py`

- Size bytes: 875
- Lines: 28
- Classes (1): ConflictModule
- Functions (3): __init__, generate_kis, get_conflict_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Conflict Module - Adversarial dynamics.

## `sovereign/ministers/data.py`

- Size bytes: 758
- Lines: 22
- Classes (1): DataModule
- Functions (3): __init__, generate_kis, get_data_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Data Module - Evidence-based reasoning.

## `sovereign/ministers/diplomacy.py`

- Size bytes: 879
- Lines: 22
- Classes (1): DiplomacyModule
- Functions (3): __init__, generate_kis, get_diplomacy_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Diplomacy Module - Stakeholder relationships.

## `sovereign/ministers/discipline.py`

- Size bytes: 865
- Lines: 22
- Classes (1): DisciplineModule
- Functions (3): __init__, generate_kis, get_discipline_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Discipline Module - Consistency and principles.

## `sovereign/ministers/examples.py`

- Size bytes: 6948
- Lines: 195
- Classes (0): 
- Functions (5): example_individual_minister, example_judge_observation, example_kis_analysis, example_orchestrator_all_ministers, example_with_prime_confident
- Imports (6): sovereign.ministers.adaptation, sovereign.ministers.data, sovereign.ministers.orchestrator, sovereign.ministers.tribunal, sovereign.prime_confident, typing
- Module docstring preview: Example usage of Minister Modules with KIS and Prime Confident integration. Location: c:\era\sovereign\ministers\examples.py This example shows: 1. Running individual minister module 2. Running all ministers via orchestrator 3. Integrating with Prime Confident for final decision 4. Accessing KIS dat

## `sovereign/ministers/grand_strategist.py`

- Size bytes: 875
- Lines: 22
- Classes (1): GrandStrategyModule
- Functions (3): __init__, generate_kis, get_grand_strategy_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Grand Strategy Module - Long-term vision.

## `sovereign/ministers/intelligence.py`

- Size bytes: 875
- Lines: 22
- Classes (1): IntelligenceModule
- Functions (3): __init__, generate_kis, get_intelligence_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Intelligence Module - Information quality.

## `sovereign/ministers/legitimacy.py`

- Size bytes: 847
- Lines: 22
- Classes (1): LegitimacyModule
- Functions (3): __init__, generate_kis, get_legitimacy_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Legitimacy Module - Values alignment.

## `sovereign/ministers/meeting_flow.py`

- Size bytes: 12601
- Lines: 316
- Classes (4): DebateOutput, MeetingSynthesis, MinisterSelection, TopicCategory
- Functions (4): execute_minister_analysis, meeting_mode_flow, select_ministers_for_topic, synthesize_meeting_debate
- Imports (5): dataclasses, enum, persona.knowledge_engine, persona.trace, typing
- Module docstring preview: Meeting Mode Flow - 2-3 Minister Discussion & Debate Branch This is a conditional branch in the main orchestrator flow that: 1. Selects 2-3 relevant ministers based on topic 2. Executes minister analysis in parallel 3. Synthesizes shared output from debate 4. Passes synthesis to Prime Confident for 

## `sovereign/ministers/narrative.py`

- Size bytes: 824
- Lines: 22
- Classes (1): NarrativeModule
- Functions (3): __init__, generate_kis, get_narrative_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Narrative Module - Story coherence.

## `sovereign/ministers/optionality.py`

- Size bytes: 854
- Lines: 22
- Classes (1): OptionalityModule
- Functions (3): __init__, generate_kis, get_optionality_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Optionality Module - Freedom preservation.

## `sovereign/ministers/orchestrator.py`

- Size bytes: 13457
- Lines: 307
- Classes (2): MinisterFlowOrchestrator, MinisterFlowResult
- Functions (7): __init__, _execute_darbar_mode, _execute_meeting_mode, _get_attr, execute_ministers, get_orchestrator, invoke_prime_confident
- Imports (7): dataclasses, llm_adapter, meeting_flow, persona.council, persona.trace, prime_confident, typing
- Module docstring preview: Minister Flow Orchestrator - Coordinates all ministers with KIS and Prime Confident. Location: c:\era\sovereign\ministers\orchestrator.py This orchestrator: 1. Executes all minister modules in parallel 2. Generates domain-specific KIS for each 3. Invokes Prime Confident with aggregated input 4. Retu

## `sovereign/ministers/power.py`

- Size bytes: 799
- Lines: 22
- Classes (1): PowerModule
- Functions (3): __init__, generate_kis, get_power_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Power Module - Capability and leverage.

## `sovereign/ministers/psychology.py`

- Size bytes: 841
- Lines: 22
- Classes (1): PsychologyModule
- Functions (3): __init__, generate_kis, get_psychology_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Psychology Module - Human factors.

## `sovereign/ministers/risk.py`

- Size bytes: 813
- Lines: 23
- Classes (1): RiskModule
- Functions (3): __init__, generate_kis, get_risk_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Risk Module - Downside protection.

## `sovereign/ministers/risk_minister.py`

- Size bytes: 2799
- Lines: 68
- Classes (1): RiskMinister
- Functions (2): __init__, produce_advice
- Imports (3): base_minister, persona.knowledge_engine, typing
- Module docstring preview: Risk minister implementation (simple, KIS-backed).

## `sovereign/ministers/risk_resources.py`

- Size bytes: 882
- Lines: 22
- Classes (1): RiskResourcesModule
- Functions (3): __init__, generate_kis, get_risk_resources_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Risk & Resources Module - Scarcity management.

## `sovereign/ministers/sovereign.py`

- Size bytes: 824
- Lines: 22
- Classes (1): SovereignModule
- Functions (3): __init__, generate_kis, get_sovereign_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Sovereign Module - Meta coherence.

## `sovereign/ministers/technology.py`

- Size bytes: 821
- Lines: 22
- Classes (1): TechnologyModule
- Functions (3): __init__, generate_kis, get_technology_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Technology Module - Technical feasibility.

## `sovereign/ministers/timing.py`

- Size bytes: 781
- Lines: 22
- Classes (1): TimingModule
- Functions (3): __init__, generate_kis, get_timing_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Timing Module - When to act.

## `sovereign/ministers/tribunal.py`

- Size bytes: 1192
- Lines: 28
- Classes (1): TribunalModule
- Functions (4): __init__, generate_kis, get_tribunal_module, invoke_with_prime
- Imports (2): persona.ministers, typing
- Module docstring preview: Tribunal Module - Advisory judge (non-voting).

## `sovereign/ministers/truth.py`

- Size bytes: 796
- Lines: 22
- Classes (1): TruthModule
- Functions (3): __init__, generate_kis, get_truth_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of Truth Module - Reality enforcement.

## `sovereign/ministers/war_mode.py`

- Size bytes: 819
- Lines: 22
- Classes (1): WarModeModule
- Functions (3): __init__, generate_kis, get_war_mode_module
- Imports (2): persona.ministers, typing
- Module docstring preview: Minister of War Mode Module - Aggressive action.

## `sovereign/prime_confident.py`

- Size bytes: 8412
- Lines: 161
- Classes (1): PrimeConfident
- Functions (5): __init__, _analyze_emotional_distortion, _apply_doctrine_constraints, _detect_pattern_recurrence, decide
- Imports (5): os, persona.doctrine_loader, persona.trace, sys, typing
- Module docstring preview: Prime Confident runtime: final authority that merges council recommendations and provides final decision and rationale. Loads doctrine from C:/era/data/doctrine/locked/n.yaml which defines: - Role identity: Mirror with teeth, synthesis point for personal context - Core worldview: Pattern recurrence,

## `sovereign/runtime/council_runtime.py`

- Size bytes: 1820
- Lines: 49
- Classes (2): CouncilRuntime, MockMinister
- Functions (4): __init__, __init__, advice, run
- Imports (3): sovereign.council.aggregator, sovereign.prime_confident, typing
- Module docstring preview: Runtime that runs ministers, aggregates council, and asks PrimeConfident for final decision. Provides a demo-run method that uses Mock ministers or real ministers.

## `sovereign/runtime/minister_runtime.py`

- Size bytes: 1037
- Lines: 28
- Classes (1): MinisterRuntime
- Functions (3): __init__, activate_ministers, register_minister
- Imports (1): typing
- Module docstring preview: minister_runtime.py Orchestrates minister activation and execution based on latched domains.

## `sovereign/sovereign_main.py`

- Size bytes: 5076
- Lines: 152
- Classes (0): 
- Functions (2): call_model, run_instance
- Imports (13): datetime, hse.analytics_server, hse.crisis_injector, hse.human_profile, hse.personality_drift, hse.population_manager, json, ml.ml_orchestrator, os, random, subprocess, threading, time

## `sovereign/sovereign_main_integration_example.py`

- Size bytes: 10978
- Lines: 301
- Classes (0): 
- Functions (2): generate_persona_response, main_simulation_loop
- Imports (2): ml.sovereign_orchestrator, traceback
- Module docstring preview: Example integration of SovereignOrchestrator into a main simulation loop. Shows how to use all 12 cognitive systems together.

## `system_main.py`

- Size bytes: 33762
- Lines: 865
- Classes (1): DecisionGuidanceSystem
- Functions (14): __init__, _generate_ml_recommendations, _generate_problem_via_llm, _get_problem_from_user, _get_problem_statement, _print_final_summary, _print_summary_stats, _run_ml_analysis, _store_episode, _store_metrics, main, run_continuous, run_interactive, run_session
- Imports (19): argparse, datetime, json, os, pathlib, persona.council.dynamic_council, persona.domain_detector, persona.knowledge_engine, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.modes.mode_orchestrator, persona.ollama_runtime, persona.session_manager, re, sovereign.prime_confident, sys, time, traceback, typing
- Module docstring preview: Advanced Decision Guidance System with Machine Learning Intelligent multi-turn problem-solving engine with: • Automatic or manual problem intake • Domain detection (15 domains, stakes, reversibility) • Multi-turn dialogue with automatic complexity escalation • KIS synthesis (Knowledge Integration Sy

## `tests/advanced_persona_test_suite.py`

- Size bytes: 19861
- Lines: 497
- Classes (3): AdvancedPersonaAgent, AdvancedTestSuite, TestMetrics
- Functions (16): __init__, __init__, print_results, respond, run_all, test, test_domain, test_domain_accumulation, test_edge, test_emotion, test_orchestration, test_response, test_state_persistence, test_strategy, test_telemetry, user_behavior
- Imports (13): dataclasses, datetime, json, multi_agent_sim.agents, multi_agent_sim.logger, multi_agent_sim.orchestrator, os, persona.brain, persona.state, random, sys, time, typing
- Module docstring preview: ADVANCED PERSONA TEST SUITE - CALIBRATED & OPTIMIZED Rigorous dynamic testing with real-world scenarios

## `tests/check_extraction.py`

- Size bytes: 1360
- Lines: 29
- Classes (0): 
- Functions (0): 
- Imports (1): json
- Module docstring preview: Check extraction results.

## `tests/check_kis_in_doctrine.py`

- Size bytes: 700
- Lines: 20
- Classes (0): 
- Functions (0): 
- Imports (1): json

## `tests/comprehensive_feature_test.py`

- Size bytes: 17131
- Lines: 486
- Classes (2): FeatureTestAgent, QuickPersonaAgent
- Functions (16): __init__, __init__, main, print_section, respond, respond, test_feature_1_state_management, test_feature_2_domain_detection, test_feature_3_emotional_intelligence, test_feature_4_persona_brain, test_feature_5_system_context, test_feature_6_conversation_logging, test_feature_7_orchestration, test_feature_8_trace_observability, test_feature_9_combined_suite, user_behavior
- Imports (12): datetime, json, multi_agent_sim.agents, multi_agent_sim.logger, multi_agent_sim.orchestrator, os, persona.brain, persona.context, persona.ollama_runtime, persona.state, persona.trace, sys
- Module docstring preview: COMPREHENSIVE FEATURE TEST: All Persona System Features Tests with BOTH mock and LLM modes enabled.

## `tests/comprehensive_persona_test_suite.py`

- Size bytes: 30672
- Lines: 761
- Classes (5): ComprehensivePersonaAgent, DynamicTestCaseGenerator, RigorousTestSuite, SuiteResult, TestResult
- Functions (24): __init__, __init__, _aggregate_results, add_result, generate_decision_scenarios, generate_domain_scenarios, generate_edge_cases, generate_emotional_scenarios, generate_learning_scenarios, generate_report, pass_rate, print_detailed_report, respond, run_all_tests, summary, test_decision_directives, test_domain_classification, test_edge_cases, test_emotional_intelligence, test_knowledge_synthesis, test_mode_variations, test_multi_agent_orchestration, test_state_management, user_behavior
- Imports (14): dataclasses, datetime, json, multi_agent_sim.agents, multi_agent_sim.logger, multi_agent_sim.orchestrator, os, persona.brain, persona.context, persona.knowledge_engine, persona.state, sys, time, typing
- Module docstring preview: COMPREHENSIVE PERSONA + MULTI-AGENT SIMULATION TEST SUITE Dynamic, rigorous testing of all features to their limits Tests: - All persona modes (quick, war, meeting, darbar) - All PersonaBrain directives (pass/halt/suppress/silence) - Emotional intelligence variants - Domain classification accuracy -

## `tests/conftest.py`

- Size bytes: 2545
- Lines: 75
- Classes (0): 
- Functions (7): era_root, ingestion_dir, pytest_collection_modifyitems, pytest_configure, rag_storage_dir, temp_test_dir, test_data_dir
- Imports (4): os, pathlib, pytest, sys
- Module docstring preview: Shared pytest configuration and fixtures for ERA Test Suite

## `tests/debug_kis_ingestion.py`

- Size bytes: 2281
- Lines: 60
- Classes (0): 
- Functions (0): 
- Imports (3): ingestion.v2.src.ingestion_kis_enhancer, json, sys
- Module docstring preview: Debug why KIS guidance is empty in doctrines

## `tests/master_test_orchestrator.py`

- Size bytes: 26140
- Lines: 620
- Classes (2): MasterTestOrchestrator, TestPersonaAgent
- Functions (24): __init__, __init__, _create_persona_agent, _extract_domains, _generate_report, _get_emotional_intensity, _print_summary, _save_reports, _test_agent_creation, _test_basic_functionality, _test_basic_response, _test_domain_classification, _test_edge_cases, _test_emotional_intelligence, _test_kis_features, _test_multi_agent_integration, _test_persona_modes, _test_response_generation, _test_state_init, _test_state_management, _test_telemetry, respond, run_master_suite, user_behavior
- Imports (14): dataclasses, datetime, io, json, multi_agent_sim.agents, multi_agent_sim.logger, multi_agent_sim.orchestrator, os, persona.brain, persona.state, random, sys, time, typing
- Module docstring preview: MASTER TEST ORCHESTRATOR - COMPREHENSIVE VALIDATION Tests all Persona + Multi-Agent features end-to-end Generates dynamic test scenarios and validation reports

## `tests/run_adapter_test.py`

- Size bytes: 207
- Lines: 7
- Classes (0): 
- Functions (0): 
- Imports (1): ml.ml_orchestrator

## `tests/run_kis_integration_test.py`

- Size bytes: 7181
- Lines: 216
- Classes (0): 
- Functions (6): check_doctrine_kis_guidance, check_kis_logs, check_ml_learning, cleanup_phase3, main, run_ingestion
- Imports (8): ingestion.v2.src.ingest_pipeline, json, ml.ml_orchestrator, os, pathlib, shutil, sys, traceback
- Module docstring preview: Complete KIS Integration Test - Run ingestion on a fresh book - Verify KIS enhancement - Check outcome logging - Verify ML learning

## `tests/run_phase1_test.py`

- Size bytes: 1157
- Lines: 29
- Classes (0): 
- Functions (0): 
- Imports (5): ingest, json, llm, os, sys

## `tests/run_tests.py`

- Size bytes: 5432
- Lines: 167
- Classes (1): TestRunner
- Functions (9): __init__, _execute_command, generate_report, main, run_all_tests, run_by_marker, run_unit_tests_only, run_verification_only, run_with_coverage
- Imports (6): datetime, json, os, pathlib, subprocess, sys
- Module docstring preview: ERA Test Runner - Execute and report on all tests and verifications Usage: python run_tests.py # Run all tests python run_tests.py --verify-only # Run verification suite only python run_tests.py --unit-only # Run unit tests only python run_tests.py --coverage # Run with coverage report python run_te

## `tests/run_v2_ingest_test.py`

- Size bytes: 387
- Lines: 12
- Classes (0): 
- Functions (0): 
- Imports (3): os, src.ingest_pipeline, sys

## `tests/sovereign_stress_test.py`

- Size bytes: 10851
- Lines: 328
- Classes (0): 
- Functions (7): _detect_failure, _log_turn, call_model, main, run_sync_instance, signal_handler, simulation_instance
- Imports (13): argparse, asyncio, datetime, llm.ollama_model_selector, ml.darbar, ml.ml_orchestrator, ml.reward_shaping, ml.vector_memory, random, signal, subprocess, sys, time
- Module docstring preview: Sovereign ML Stress Test Runs a multi-agent stress loop and invokes the ML orchestrator each turn. Features: - Dry-run mode (no Ollama calls) for local validation - Auto-select models if not provided - Passes conversation (USER + PROGRAM) into ML via `process_decision` - Periodic retraining via `--r

## `tests/test_async_embed.py`

- Size bytes: 3184
- Lines: 86
- Classes (0): 
- Functions (2): _parse_chunks_from_file, test_async_embed
- Imports (9): asyncio, ingestion.v2.src.async_ingest_config, ingestion.v2.src.async_ingest_orchestrator, ingestion.v2.src.config, ingestion.v2.src.ollama_client, json, os, sys, traceback
- Module docstring preview: Quick test of async embedding to verify ThreadPoolExecutor fix.

## `tests/test_async_embed_debug.py`

- Size bytes: 3480
- Lines: 100
- Classes (0): 
- Functions (2): _parse_chunks_from_file, test_async_embed
- Imports (10): asyncio, ingestion.v2.src.async_ingest_config, ingestion.v2.src.async_ingest_orchestrator, ingestion.v2.src.config, ingestion.v2.src.ollama_client, json, logging, os, sys, traceback
- Module docstring preview: Quick test of async embedding with detailed logging.

## `tests/test_async_ingest.py`

- Size bytes: 6045
- Lines: 205
- Classes (0): 
- Functions (7): main, stub_parse_func, test_chunk_dataclass, test_imports, test_metrics_collection, test_rate_controller, test_simple_pipeline
- Imports (10): async_ingest_config, async_ingest_orchestrator, async_workers, asyncio, ingest_metrics, json, logging, rate_controller, sys, traceback
- Module docstring preview: Test suite for async ingestion pipeline.

## `tests/test_async_ingestion.py`

- Size bytes: 11893
- Lines: 363
- Classes (6): TestAdaptiveController, TestAsyncIngestionOrchestrator, TestBenchmarkHarness, TestDistributedQueue, TestIntegrationPipeline, TestPipelineWorkers
- Functions (15): dummy_processor, test_benchmark_result_statistics, test_benchmark_suite_collection, test_enqueue_dequeue, test_feedback_adjustment, test_full_pipeline_execution, test_job_processing, test_job_submission, test_multiple_jobs, test_orchestrator_startup, test_priority_ordering, test_rate_limiting, test_retry_logic, test_token_bucket_basic, test_worker_pool_processing
- Imports (8): adaptive_controller, async_ingestion_orchestrator, asyncio, benchmark_harness, distributed_queue, ingest_workers, pytest, typing
- Module docstring preview: Integration Tests for Production Async Ingestion Pipeline

## `tests/test_deepseek_doctrine.py`

- Size bytes: 4737
- Lines: 122
- Classes (0): 
- Functions (0): 
- Imports (3): json, requests, traceback
- Module docstring preview: Test deepseek model with doctrine extraction prompt.

## `tests/test_direct_ingest.py`

- Size bytes: 914
- Lines: 27
- Classes (0): 
- Functions (0): 
- Imports (5): ingestion.v2.src.ingest_pipeline, json, pathlib, shutil, sys

## `tests/test_e2e_ingestion.py`

- Size bytes: 7548
- Lines: 207
- Classes (0): 
- Functions (3): create_test_book, parse_test_book_module, test_e2e_ingestion
- Imports (10): async_ingest_config, async_ingest_orchestrator, asyncio, json, logging, pathlib, sys, tempfile, traceback, vector_db
- Module docstring preview: End-to-end test: verify complete ingestion pipeline from start to vector schema.

## `tests/test_embed.py`

- Size bytes: 349
- Lines: 13
- Classes (0): 
- Functions (0): 
- Imports (1): requests

## `tests/test_embed_model.py`

- Size bytes: 664
- Lines: 17
- Classes (0): 
- Functions (0): 
- Imports (2): requests, time

## `tests/test_features.py`

- Size bytes: 4849
- Lines: 152
- Classes (0): 
- Functions (0): 
- Imports (11): hse.simulation.synthetic_human_sim, json, ml.ml_orchestrator, os, persona.brain, persona.council.dynamic_council, persona.knowledge_engine, persona.modes.mode_orchestrator, persona.state, sovereign.prime_confident, sys
- Module docstring preview: Quick feature test

## `tests/test_generate.py`

- Size bytes: 344
- Lines: 13
- Classes (0): 
- Functions (0): 
- Imports (1): requests

## `tests/test_improved_doctrine.py`

- Size bytes: 6537
- Lines: 146
- Classes (0): 
- Functions (1): test_extraction
- Imports (6): importlib.util, json, os, requests, sys, traceback
- Module docstring preview: Test script to verify improved doctrine extraction prompt.

## `tests/test_kis_enhancement_direct.py`

- Size bytes: 2078
- Lines: 61
- Classes (0): 
- Functions (0): 
- Imports (7): ingestion.v2.src.ingestion_kis_enhancer, json, ml.kis.knowledge_integration_system, os, pathlib, shutil, sys

## `tests/test_kis_exact_scenario.py`

- Size bytes: 3270
- Lines: 91
- Classes (0): 
- Functions (0): 
- Imports (5): ingestion.v2.src.ingestion_kis_enhancer, json, os, sys, traceback
- Module docstring preview: Replicate exact ingestion scenario to find KIS issue

## `tests/test_kis_integration.py`

- Size bytes: 1580
- Lines: 43
- Classes (0): 
- Functions (0): 
- Imports (4): ingestion.v2.src.ingestion_kis_enhancer, ml.kis.knowledge_integration_system, sys, traceback
- Module docstring preview: Test KIS integration independently

## `tests/test_llm_client.py`

- Size bytes: 4350
- Lines: 129
- Classes (0): 
- Functions (0): 
- Imports (4): ml.llm_handshakes.llm_interface, os, sys, traceback
- Module docstring preview: Step 3: Test LLM Client Integration Verifies that: 1. LLMInterface connects to Ollama 2. 4-call handshake works 3. JSON parsing succeeds 4. Retry logic handles failures

## `tests/test_llm_kis_integration.py`

- Size bytes: 5875
- Lines: 154
- Classes (0): 
- Functions (0): 
- Imports (5): json, ml.judgment.ml_judgment_prior, ml.kis.knowledge_integration_system, ml.llm_handshakes.llm_interface, sys
- Module docstring preview: Integration Test: LLM Client + KIS System Demonstrates how the LLM handshake integrates with KIS for decision guidance.

## `tests/test_minister_converter.py`

- Size bytes: 10483
- Lines: 290
- Classes (0): 
- Functions (6): main, test_basic_structure, test_chapter_conversion, test_combined_index_update, test_entry_creation, test_multiple_chapters
- Imports (7): json, minister_converter, os, pathlib, sys, tempfile, traceback
- Module docstring preview: Test Phase 3.5 Minister Converter functionality. This script tests the core functions of the minister conversion system against sample doctrine data.

## `tests/test_split.py`

- Size bytes: 1422
- Lines: 46
- Classes (0): 
- Functions (0): 
- Imports (2): llm, sys

## `tests/test_split_direct.py`

- Size bytes: 1231
- Lines: 28
- Classes (0): 
- Functions (0): 
- Imports (2): subprocess, sys

## `tests/test_split_qwen25.py`

- Size bytes: 1186
- Lines: 48
- Classes (0): 
- Functions (0): 
- Imports (3): ingest, llm, sys

## `tests/test_step3_simple.py`

- Size bytes: 1186
- Lines: 36
- Classes (0): 
- Functions (0): 
- Imports (3): ml.llm_handshakes.llm_interface, sys, traceback

## `tests/test_step4_training_data.py`

- Size bytes: 11183
- Lines: 309
- Classes (0): 
- Functions (7): main, test_feedback_loop_integration, test_ml_model_training, test_outcome_recording, test_outcome_recording_with_feedback, test_outcomes_directory_structure, test_training_data_generation
- Imports (10): datetime, json, ml.judgment.ml_judgment_prior, ml.kis.knowledge_integration_system, ml.llm_handshakes.llm_interface, ml.ml_orchestrator, ml.outcomes.outcome_recorder, os, pathlib, traceback
- Module docstring preview: Step 4: Training Data Collection - Complete Test Demonstrates the feedback loop: 1. Record decisions with LLM + KIS guidance 2. Record outcomes for those decisions 3. Generate training data from outcomes 4. Train ML models on the data 5. Save trained weights for next iteration

## `tests/vector_db_smoke.py`

- Size bytes: 554
- Lines: 17
- Classes (0): 
- Functions (0): 
- Imports (2): sys, vector_db

## `tests/verification/check_chapter_text.py`

- Size bytes: 953
- Lines: 28
- Classes (0): 
- Functions (0): 
- Imports (3): json, pathlib, traceback
- Module docstring preview: Check what chapter text looks like.

## `tests/verification/check_doctrine.py`

- Size bytes: 1140
- Lines: 30
- Classes (0): 
- Functions (0): 
- Imports (2): json, traceback
- Module docstring preview: Check doctrine extraction.

## `tests/verification/check_extraction.py`

- Size bytes: 1360
- Lines: 29
- Classes (0): 
- Functions (0): 
- Imports (1): json
- Module docstring preview: Check extraction results.

## `tests/verification/check_ingestion_status.py`

- Size bytes: 1510
- Lines: 50
- Classes (0): 
- Functions (0): 
- Imports (3): json, os, pathlib
- Module docstring preview: Check doctrine extraction across all books.

## `tests/verification/check_v2_status.py`

- Size bytes: 1410
- Lines: 47
- Classes (0): 
- Functions (0): 
- Imports (2): json, pathlib
- Module docstring preview: Check doctrine extraction across all books.

## `tests/verification/quick_verify.py`

- Size bytes: 5286
- Lines: 170
- Classes (0): 
- Functions (0): 
- Imports (10): persona.analysis, persona.brain, persona.clarify, persona.context, persona.knowledge_engine, persona.main, persona.ollama_runtime, persona.state, persona.trace, sys
- Module docstring preview: Quick System Verification - Confirms all features are accessible

## `tests/verification/test_ml_layer.py`

- Size bytes: 8726
- Lines: 231
- Classes (0): 
- Functions (0): 
- Imports (9): hse.human_profile, hse.simulation.synthetic_human_sim, ml.pattern_extraction, os, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.modes.mode_metrics, persona.ollama_runtime, sys
- Module docstring preview: Test ML layer integration: episodic memory, metrics, learning, and improvement. Shows: 1. Data collection (episodic memory) 2. Pattern analysis (pattern extraction) 3. Performance tracking (metrics) 4. Learning signals (weak domains, risks) 5. Improvement trajectory

## `tests/verification/test_persona_simple.py`

- Size bytes: 2055
- Lines: 69
- Classes (0): 
- Functions (1): run_main
- Imports (6): os, persona.main, sys, threading, time, traceback
- Module docstring preview: Simplified test of persona main() with timeout and output monitoring

## `tests/verification/test_startup.py`

- Size bytes: 750
- Lines: 27
- Classes (0): 
- Functions (0): 
- Imports (4): os, persona.main, sys, traceback

## `tests/verification/verify_all_features.py`

- Size bytes: 9616
- Lines: 401
- Classes (0): 
- Functions (1): test_feature
- Imports (8): persona.analysis, persona.brain, persona.clarify, persona.knowledge_engine, persona.main, persona.ollama_runtime, persona.state, time
- Module docstring preview: Complete Features Verification Script Validates that ALL 40+ Persona system features are working

## `tests/verification/verify_and_run.py`

- Size bytes: 8632
- Lines: 254
- Classes (0): 
- Functions (0): 
- Imports (15): hse.human_profile, hse.simulation.synthetic_human_sim, ml.pattern_extraction, os, persona.council.dynamic_council, persona.learning.episodic_memory, persona.learning.outcome_feedback, persona.learning.performance_metrics, persona.main, persona.modes.mode_metrics, persona.modes.mode_orchestrator, persona.ollama_runtime, persona.state, sys, traceback
- Module docstring preview: Comprehensive system integration check before synthetic conversation. Tests: 1. LLM Runtime - Can connect to Ollama 2. Mode Orchestrator - Can switch modes and route ministers 3. Dynamic Council - Can convene council 4. Mode Metrics - Can track performance 5. Episodic Memory - Can store episodes 6. 

## `tests/verification/verify_improvements.py`

- Size bytes: 3819
- Lines: 98
- Classes (0): 
- Functions (0): 
- Imports (6): ingestion.v2.src.config, inspect, json, persona, persona.state, sys
- Module docstring preview: Verify all system improvements have been successfully implemented.

## `tests/verification/verify_llm_integration.py`

- Size bytes: 2114
- Lines: 68
- Classes (0): 
- Functions (0): 
- Imports (5): os, persona.brain, persona.ollama_runtime, persona_mas_integration, sys
- Module docstring preview: Quick test: Verify Persona LLM Integration Tests that PersonaAgent can be created with LLM support

## `tests/verify_api_fixes.py`

- Size bytes: 7144
- Lines: 200
- Classes (0): 
- Functions (0): 
- Imports (12): inspect, pathlib, persona.council.dynamic_council, persona.domain_detector, persona.knowledge_engine, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.ollama_runtime, persona.session_manager, sovereign.prime_confident, sys, traceback
- Module docstring preview: Verification: All API Incompatibilities Fixed This script documents the 4 API fixes that enable the full conversation workflow. Run: python verify_api_fixes.py

## `tests/verify_kis_integration.py`

- Size bytes: 1918
- Lines: 62
- Classes (0): 
- Functions (0): 
- Imports (7): glob, ingestion.v2.src.ingest_pipeline, json, os, pathlib, shutil, sys
- Module docstring preview: Verify KIS enhancement is saved to doctrines

## `tests/verify_kis_saved.py`

- Size bytes: 931
- Lines: 25
- Classes (0): 
- Functions (0): 
- Imports (1): json

## `tests/verify_llm_implementation.py`

- Size bytes: 4813
- Lines: 147
- Classes (0): 
- Functions (0): 
- Imports (2): ml.llm_handshakes.llm_interface, sys
- Module docstring preview: Quick verification: LLM Client implementation (no Ollama calls)

## `tests/verify_ml_integration.py`

- Size bytes: 10751
- Lines: 349
- Classes (0): 
- Functions (8): main, print_summary, test_domain_detection, test_learning_components, test_llm_connection, test_session_manager, verify_directories, verify_imports
- Imports (11): ml.ml_orchestrator, ml_integrated_conversation, pathlib, persona.domain_detector, persona.knowledge_engine, persona.learning.episodic_memory, persona.learning.performance_metrics, persona.modes.mode_orchestrator, persona.ollama_runtime, persona.session_manager, sys
- Module docstring preview: ML-Integrated Conversation System: Verification & Quick Test Verifies all components are properly integrated and working.

## `utils/ML_WISDOM_INTEGRATION_GUIDE.py`

- Size bytes: 15207
- Lines: 465
- Classes (0): 
- Functions (10): check_system_status, complete_decision_cycle_example, get_learning_metrics, make_decision_with_tracking, record_batch_outcomes, record_decision_outcome, run_decision_batch, setup_ml_wisdom_system, train_on_accumulated_outcomes, troubleshoot_system
- Imports (4): ml.judgment.ml_judgment_prior, ml.kis.knowledge_integration_system, ml.llm_handshakes.llm_interface, ml.ml_orchestrator
- Module docstring preview: ML Wisdom System - Complete Integration Guide Steps 2, 3, and 4 fully implemented and integrated. Ready for production deployment with continuous learning.

## `utils/__init__.py`

- Size bytes: 317
- Lines: 9
- Classes (0): 
- Functions (0): 
- Imports (0): 
- Module docstring preview: Utility scripts for system operations. Includes: - batch_convert_rag_storage.py: batch conversion of RAG format - cleanup_atomic_dirs.py: clean up temporary/atomic directories - migrate_to_consolidated.py: data migration utilities - ML_WISDOM_INTEGRATION_GUIDE.py: ML wisdom integration documentation

## `utils/batch_convert_rag_storage.py`

- Size bytes: 5174
- Lines: 152
- Classes (0): 
- Functions (2): batch_convert_rag_storage, progress_callback
- Imports (8): argparse, io, json, minister_converter, os, pathlib, sys, traceback
- Module docstring preview: Batch convert all doctrines from rag_storage into minister structure.

## `utils/cleanup_atomic_dirs.py`

- Size bytes: 2654
- Lines: 82
- Classes (0): 
- Functions (2): cleanup_domain, main
- Imports (3): os, shutil, sys
- Module docstring preview: Clean up old atomic entry directories after consolidation to consolidated JSON files. Removes the subdirectories (principles/, rules/, claims/, warnings/) from each domain since they are now replaced by consolidated JSON files.

## `utils/migrate_to_consolidated.py`

- Size bytes: 7512
- Lines: 196
- Classes (0): 
- Functions (2): main, migrate_domain
- Imports (4): json, os, pathlib, sys
- Module docstring preview: Migrate atomic entry files to consolidated category JSON files. Converts the old structure (atomic files in subdirectories) to the new structure (consolidated array JSON files per category).
