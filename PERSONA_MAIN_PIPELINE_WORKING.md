# Persona Contribution to Main Pipeline

## Short Answer
Yes. `persona` is a primary execution subsystem in this repository, not an isolated module. It contributes directly to benchmark execution, Phase2 robustness evaluation, system runtime orchestration, and sovereign wrappers.

## Where `persona` Connects to Main Pipeline

### 1) Benchmark path
- File: `run_benchmark.py`
- Direct dependency: `from persona.ollama_runtime import OllamaRuntime`
- Contribution:
  - Provides live LLM runtime interface used during benchmark runs.
  - Any runtime behavior change in `persona/ollama_runtime.py` changes benchmark behavior.

### 2) Phase2 evaluation path (core/adversarial/OOD)
- File: `evaluation/run_phase2_robustness.py`
- Direct dependencies:
  - `from persona.modes.mode_orchestrator import ModeOrchestrator, ExecutionConfig`
  - `from persona.ollama_runtime import OllamaRuntime`
- Contribution:
  - Mode policy and escalation logic (QUICK/MEETING/DARBAR).
  - Uncertainty-based control switching.
  - Runtime generation path for council decisions.

### 3) End-to-end system runtime
- File: `system_main.py`
- Direct dependencies:
  - `persona.ollama_runtime.OllamaRuntime`
  - `persona.domain_detector.analyze_situation`
  - `persona.session_manager.SessionManager`
  - `persona.modes.mode_orchestrator.ModeOrchestrator`
  - `persona.knowledge_engine.synthesize_knowledge`
  - `persona.council.dynamic_council.DynamicCouncil`
- Contribution:
  - Domain inference, session progression, mode selection, council invocation, knowledge synthesis.

### 4) Sovereign integration layer
- Files:
  - `sovereign/llm_adapter.py`
  - `sovereign/ministers/orchestrator.py`
  - `sovereign/ministers/__init__.py`
- Contribution:
  - Reuses persona runtime (`OllamaRuntime`), council aggregation contracts, knowledge synthesis, and minister base interfaces.

## What `persona` Does Internally

## A) Runtime I/O Layer
- File: `persona/ollama_runtime.py`
- Responsibilities:
  - Boot-time availability handshake with Ollama server.
  - `analyze()` and `speak()` wrappers for model calls.
  - Fail-fast error raising on call failure.
- Pipeline impact:
  - If runtime fails, evaluation and benchmark paths fail fast.

## B) Mode Control and Escalation
- File: `persona/modes/mode_orchestrator.py`
- Responsibilities:
  - Strategy selection for modes: QUICK, WAR, MEETING, DARBAR.
  - Composite uncertainty calculation.
  - Control policy application for escalation and caution signaling.
- Pipeline impact:
  - Determines when deep council deliberation is activated.
  - Affects compute usage, deliberation depth, and robustness behavior.

## C) Council Composition and Aggregation
- Files:
  - `persona/council/dynamic_council.py`
  - `persona/council.py`
  - `persona/council/__init__.py`
- Responsibilities:
  - Dynamic council membership by mode.
  - Minister invocation and position collection.
  - Aggregate recommendation and confidence.
- Pipeline impact:
  - Directly changes scenario-level council decisions and confidence outputs used by evaluators.

## D) Knowledge Synthesis (KIS path)
- File: `persona/knowledge_engine.py`
- Responsibilities:
  - Load domain knowledge entries from `data/ministers/*`.
  - Score/weight principles/rules/warnings/claims/advice.
  - Produce synthesized guidance and trace/debug metadata.
- Pipeline impact:
  - Influences minister rationale quality and decision framing.
  - Impacts principle coverage signals used in evaluation.

## E) Domain and Session Intelligence
- Files:
  - `persona/domain_detector.py`
  - `persona/session_manager.py`
- Responsibilities:
  - Detect active domains, stakes, reversibility proxies.
  - Track sessions, turns, related-history retrieval, escalation decisions.
- Pipeline impact:
  - Improves context continuity and mode progression stability across turns.

## F) Minister Layer
- File: `persona/ministers.py`
- Responsibilities:
  - Defines minister roles and per-minister `analyze(...)` behavior.
  - Exposes minister registry (`MINISTERS`, `JUDGES`) consumed by council orchestration.
- Pipeline impact:
  - Shapes disagreement patterns, confidence variance, and final aggregate decision quality.

## G) Learning/Validation/Persistence Extensions
- Paths:
  - `persona/learning/*`
  - `persona/validation/*`
  - `persona/persistence/*`
  - `persona/pwm_integration/*`
- Responsibilities:
  - Episodic memory, outcome feedback, confidence modeling, mode/identity validation, persistence arcs, PWM bridge.
- Pipeline impact:
  - Supports robustness instrumentation and future adaptive behavior without replacing core council path.

## End-to-End Execution Trace (Main Pipeline View)
1. Input scenario enters evaluator or runtime driver.
2. LLM runtime initialized via `persona.ollama_runtime.OllamaRuntime`.
3. Domain/context signals extracted (`domain_detector`, scenario features).
4. Mode selected by `ModeOrchestrator`.
5. If mode requires council, `DynamicCouncil` invokes appropriate ministers.
6. Ministers use `knowledge_engine` and context to produce positions.
7. Council aggregate recommendation/confidence is produced.
8. Uncertainty policy may trigger escalation (e.g., DARBAR second pass).
9. Final decision/rationale/confidence returned to evaluator.
10. Evaluator computes score/lift/calibration/robustness metrics.

## Why This Means `persona` Contributes to Main Pipeline
- Main benchmark and Phase2 runners import persona modules directly.
- Control policy, runtime behavior, and council logic in persona affect primary reported metrics.
- Sovereign and system runners reuse persona contracts rather than duplicating them.

Conclusion: `persona` is a core pipeline dependency and an active decision/control engine, not an optional plugin.
