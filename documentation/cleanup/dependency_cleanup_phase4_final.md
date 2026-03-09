# Phase 4 Dependency Cleanup Finalization

## Outcome
- Phase-2 candidate list is now fully exhausted.
- Remaining phase-2 candidates still present in tree: `0`.

## Final Removals in This Pass
- `modules/domain_analysis/native.py`
- `modules/knowledge_synthesis/native.py`
- `modules/council_execution/native.py`
- `persona/council.py`
- `llm_conversation.py`

## Replacement Strategy Applied
- Inlined native implementations into:
  - `modules/domain_analysis/engine.py`
  - `modules/knowledge_synthesis/engine.py`
  - `modules/council_execution/engine.py`
- Preserved compatibility contracts by adding:
  - `persona/council/aggregator.py`
  - package exports in `persona/council/__init__.py`
- Removed stale entrypoint references:
  - `README.md`
  - `START_HERE.md`
  - `tests/test_no_legacy_pipeline_imports.py`
  - `documentation/DYNAMIC_COUNCIL_GUIDE.md`
- Removed obsolete guide:
  - `documentation/LLM_CONVERSATION_GUIDE.md`

## Validation
- Targeted regression suite: `73 passed`.
- Smoke run: `python system_main.py --input "..."`
  - Completed (non-fatal warning: `telemetry_metadata_invalid_type`).
- CLI smoke: `python run_refactored.py --help`
  - Completed.
