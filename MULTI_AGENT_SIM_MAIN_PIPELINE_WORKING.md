# Multi-Agent Sim Contribution to Main Pipeline

## Short Answer
`multi_agent_sim` can contribute to the main pipeline, but today it is primarily wired as a simulation/test harness rather than a required runtime path for Phase2 benchmark execution.

## What `multi_agent_sim` Does

`multi_agent_sim` provides a reusable framework to run closed-loop conversations between two agents (LLM or mock), with orchestration and logging.

Core modules:
- `multi_agent_sim/agents.py`
  - `BaseAgent`: abstract interface (`respond(system_prompt, user_prompt)`).
  - `OllamaAgent`: subprocess-based Ollama caller.
  - `MockAgent`: deterministic/local test agent.
- `multi_agent_sim/orchestrator.py`
  - `Orchestrator`: turn loop engine with max-turn control and optional stop condition.
- `multi_agent_sim/logger.py`
  - `ConversationLogger`: in-memory + file transcript logging.
- `multi_agent_sim/terminal.py`
  - interactive high-control terminal with timeout-guarded model calls.
- `multi_agent_sim/run_terminal.py`
  - launcher that auto-selects models and sets env for terminal.
- `multi_agent_sim/simulation_runner.py`
  - bidirectional user-LLM <-> persona-LLM simulation entrypoint.
  - Integrates `hse` synthetic human + `persona` runtime + optional persona council.
- `multi_agent_sim/demo.py`
  - mock demonstration path.
- `multi_agent_sim/__main__.py`
  - module-level dispatcher to terminal/run_terminal/demo.

## Where It Is Referenced (Non-Document Code)

### Tests (active)
`multi_agent_sim` is actively imported by test suites:
- `tests/master_test_orchestrator.py`
- `tests/comprehensive_persona_test_suite.py`
- `tests/comprehensive_feature_test.py`
- `tests/advanced_persona_test_suite.py`
- `tests/conftest.py` adds `multi_agent_sim` to import path.

### Legacy archive (historical)
- `archive/integrations_old/persona_mas_integration.py`
- `archive/integrations_old/persona_mas_integration_simple.py`

### Not directly used by primary Phase2 runner
No direct import into the core evaluation runner path:
- `evaluation/run_phase2_robustness.py` (does not import `multi_agent_sim`)
- `run_benchmark.py` (does not import `multi_agent_sim`)
- `system_main.py` (does not import `multi_agent_sim`)

## How It Can Contribute to Main Pipeline

## 1) Adversarial / stress loop generation
`multi_agent_sim` already has turn orchestration and agent abstraction. It can be used to generate stress trajectories and synthetic interaction transcripts that feed into:
- robustness evaluation datasets,
- uncertainty/control validation,
- governance red-team scenarios.

## 2) Repeatable synthetic user simulation
`simulation_runner.py` already bridges:
- `hse` synthetic humans,
- `persona` runtime (`OllamaRuntime`),
- optional `persona` dynamic council.

This makes it a practical source for generating additional routed decisions and edge-case interaction traces.

## 3) Fast offline regression via `MockAgent`
The `MockAgent` + orchestrator path gives deterministic replay-style checks for orchestration logic without live LLM cost.

## Current Role vs Mainline Role

Current role:
- Test and simulation support layer.
- Not a hard dependency for baseline/Phase2 benchmark runs.

Potential mainline role:
- Upstream scenario generator for Milestone 4 stress/adversarial layers.
- Standardized self-play harness that emits artifacts consumable by `evaluation/*`.

## Integration Recommendation

To make `multi_agent_sim` a first-class main-pipeline contributor without replacing existing runners:

1. Keep evaluation authority in `evaluation/run_phase2_robustness.py`.
2. Use `multi_agent_sim` as a scenario/exchange generator only.
3. Export simulation outputs in schema compatible with evaluation scenario format.
4. Add an optional ingestion flag in evaluation runner, e.g.:
   - `--scenario-source multi_agent_sim_export.json`
5. Preserve one scorer/evaluator path for comparability.

## Bottom Line

`multi_agent_sim` is not currently the main execution path for benchmark/Phase2, but it is a valid and useful contributor as a simulation-driven input generation and stress-testing layer. It should be integrated as a producer feeding the existing evaluation runner, not as a parallel evaluator.
