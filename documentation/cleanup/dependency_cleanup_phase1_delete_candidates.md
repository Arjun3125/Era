# Phase 1 Dependency-Driven Cleanup (No Deletions)

## Summary
- Python files scanned: 391
- Import edges found: 645
- Entrypoints detected: 3
- Candidates: 97
- Risk counts: high=61, medium=33, low=3

## Candidate Tag Definitions
- `unused`: no incoming imports in static graph and not identified as entrypoint/test/package init
- `legacy-adapter`: archived/legacy area with no incoming imports
- `experimental`: standalone evaluation or utility scripts with no incoming imports
- `uncertain`: looked unused but referenced in docs/text or dynamic patterns may apply

## Entrypoints Detected
- `run_benchmark.py`
- `run_eval_demo.py`
- `system_main.py`

## High Risk Candidates
- `ingestion/v1/ingest.py` | tag=unused | in=0 out=1 | core subsystem file has no incoming imports
- `ingestion/v1/llm.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/run_all_v2_ingest.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/scripts/generate_chapters_fallback.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `ingestion/v2/src/ASYNC_PIPELINE_GUIDE.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/adaptive_controller.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/async_ingestion_orchestrator.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/benchmark_harness.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/demo_async_pipeline.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/distributed_queue.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/ingest_workers.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/ingestion_config.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/integration_examples.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/minister_vector_db.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/quickstart.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ingestion/v2/src/verify_installation.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `llm/interactive_llm_conversation.py` | tag=unused | in=0 out=3 | core subsystem file has no incoming imports
- `llm/interactive_persona_chat.py` | tag=unused | in=0 out=1 | core subsystem file has no incoming imports
- `ml/QUICKSTART.py` | tag=unused | in=0 out=5 | core subsystem file has no incoming imports
- `ml/doctrine_update.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ml/minister_retraining.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ml/quick_test_ml.py` | tag=unused | in=0 out=5 | core subsystem file has no incoming imports
- `ml/test_ml_learning_loop.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `ml/tests/test_ml_wisdom.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `multi_agent_sim/__main__.py` | tag=unused | in=0 out=1 | core subsystem file has no incoming imports
- `multi_agent_sim/demo.py` | tag=unused | in=0 out=4 | core subsystem file has no incoming imports
- `multi_agent_sim/run_terminal.py` | tag=unused | in=0 out=1 | core subsystem file has no incoming imports
- `multi_agent_sim/simulation_runner.py` | tag=unused | in=0 out=6 | core subsystem file has no incoming imports
- `multi_agent_sim/terminal.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `persona/cache_manager.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `persona/council.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `persona/persistence/memory_store.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `persona/persona_learning_processor.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `persona/persona_minister_kis_bridge.py` | tag=unused | in=0 out=3 | core subsystem file has no incoming imports
- `persona/run_persona.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `persona/run_persona_conversation.py` | tag=unused | in=0 out=1 | core subsystem file has no incoming imports
- `persona/test_session_workflow.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `persona/validation/contradiction_detector.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `sovereign/ministers/conflict.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/diplomacy.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/discipline.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/examples.py` | tag=unused | in=0 out=5 | core subsystem file has no incoming imports
- `sovereign/ministers/grand_strategist.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/intelligence.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/legitimacy.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/narrative.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/optionality.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/power.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/psychology.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/risk.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/risk_minister.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/risk_resources.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/sovereign.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/technology.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/timing.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/truth.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/ministers/war_mode.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/runtime/council_runtime.py` | tag=unused | in=0 out=2 | core subsystem file has no incoming imports
- `sovereign/runtime/minister_runtime.py` | tag=unused | in=0 out=0 | core subsystem file has no incoming imports
- `sovereign/sovereign_main.py` | tag=unused | in=0 out=6 | core subsystem file has no incoming imports
- `sovereign/sovereign_main_integration_example.py` | tag=unused | in=0 out=1 | core subsystem file has no incoming imports

## Medium Risk Candidates
- `Memory/pwm.py` | tag=unused | in=0 out=0 | no incoming imports in static graph
- `analytics/improvement_tracker.py` | tag=unused | in=0 out=0 | no incoming imports in static graph
- `analytics/reporting.py` | tag=unused | in=0 out=0 | no incoming imports in static graph
- `analyze_conversation_learning.py` | tag=unused | in=0 out=0 | no incoming imports in static graph
- `evaluation/analyze_kis_failure_mode.py` | tag=experimental | in=0 out=1 | evaluation pipeline script with no incoming imports
- `evaluation/analyze_minister_similarity.py` | tag=experimental | in=0 out=2 | evaluation pipeline script with no incoming imports
- `evaluation/build_kis2_index.py` | tag=experimental | in=0 out=1 | evaluation pipeline script with no incoming imports
- `evaluation/build_phase2_gating_dataset.py` | tag=experimental | in=0 out=4 | evaluation pipeline script with no incoming imports
- `evaluation/freeze_diversity_baseline.py` | tag=experimental | in=0 out=0 | evaluation pipeline script with no incoming imports
- `evaluation/gate_milestone3.py` | tag=experimental | in=0 out=0 | evaluation pipeline script with no incoming imports
- `evaluation/reliability_analysis.py` | tag=experimental | in=0 out=1 | evaluation pipeline script with no incoming imports
- `evaluation/run_phase2_with_gates.py` | tag=experimental | in=0 out=3 | evaluation pipeline script with no incoming imports
- `evaluation/run_phase4_stress.py` | tag=experimental | in=0 out=0 | evaluation pipeline script with no incoming imports
- `evaluation/train_kis2_reranker.py` | tag=experimental | in=0 out=0 | evaluation pipeline script with no incoming imports
- `evaluation/train_phase2_gating.py` | tag=experimental | in=0 out=2 | evaluation pipeline script with no incoming imports
- `evaluation/uncertainty_analysis.py` | tag=experimental | in=0 out=0 | evaluation pipeline script with no incoming imports
- `llm_conversation.py` | tag=unused | in=0 out=2 | no incoming imports in static graph
- `scripts/STARTUP_GUIDE.py` | tag=experimental | in=0 out=0 | utility script with no incoming imports
- `scripts/VISUAL_SUMMARY.py` | tag=experimental | in=0 out=0 | utility script with no incoming imports
- `scripts/check_embed.py` | tag=experimental | in=0 out=1 | utility script with no incoming imports
- `scripts/check_ingestion_status.py` | tag=experimental | in=0 out=0 | utility script with no incoming imports
- `scripts/check_models.py` | tag=experimental | in=0 out=0 | utility script with no incoming imports
- `scripts/check_ollama_api.py` | tag=experimental | in=0 out=0 | utility script with no incoming imports
- `scripts/check_requirements.py` | tag=experimental | in=0 out=0 | utility script with no incoming imports
- `scripts/convert_markdown_to_docx.py` | tag=experimental | in=0 out=0 | utility script with no incoming imports
- `scripts/ingest_status.py` | tag=experimental | in=0 out=0 | utility script with no incoming imports
- `scripts/run_embed_only.py` | tag=experimental | in=0 out=4 | utility script with no incoming imports
- `scripts/scan_rag_storage.py` | tag=experimental | in=0 out=0 | utility script with no incoming imports
- `scripts/stream_persona_live.py` | tag=experimental | in=0 out=4 | utility script with no incoming imports
- `utils/ML_WISDOM_INTEGRATION_GUIDE.py` | tag=unused | in=0 out=4 | no incoming imports in static graph
- `utils/batch_convert_rag_storage.py` | tag=unused | in=0 out=0 | no incoming imports in static graph
- `utils/cleanup_atomic_dirs.py` | tag=unused | in=0 out=0 | no incoming imports in static graph
- `utils/migrate_to_consolidated.py` | tag=unused | in=0 out=0 | no incoming imports in static graph

## Low Risk Candidates
- `archive/integrations_old/persona_mas_integration.py` | tag=legacy-adapter | in=0 out=10 | under archive/* and no incoming imports
- `archive/integrations_old/persona_mas_integration_simple.py` | tag=legacy-adapter | in=0 out=8 | under archive/* and no incoming imports
- `archive/runtime_old/run_sim.py` | tag=legacy-adapter | in=0 out=6 | under archive/* and no incoming imports

## Next Safe Action
- Delete only low-risk `legacy-adapter` and low-risk `experimental` candidates in small batches (3-10 files).
- Run full tests and evaluation after each batch.
- Promote medium/high candidates only after runtime verification and grep-based call-site confirmation.
