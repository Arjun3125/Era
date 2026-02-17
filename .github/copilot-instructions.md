# Copilot Instructions for PERSONA N System

## Architecture Overview

**Project Type**: Sovereign decision governance system (not a chatbot). A Ministerial Cognitive Architecture (MCA) combining modal decision-making with multi-perspective ministerial councils and machine learning judgment priors.

### Three Core Layers

1. **Mode Orchestrator** (`persona/modes/`) - Routes decisions through 4 modes:
   - **QUICK**: 1:1 mentoring, direct LLM, no council
   - **WAR**: Victory-focused, 5 ministers (Risk, Power, Intelligence, etc.)
   - **MEETING**: Balanced debate, 3-5 relevant ministers
   - **DARBAR**: Full wisdom council, all 19 voting ministers + 1 judge

2. **Ministerial Council** (`sovereign/ministers/`) - 19 domain-bounded advisors:
   - Each minister generates KIS (Knowledge Integration System) in their domain
   - Ministers advise sovereignty via Prime Confident's final decision authority
   - Voting rules by mode; Judge (Tribunal) observes consequences only

3. **ML Wisdom System** (`ml/`) - 4-layer learning stack:
   - **Layer 1**: LLM Handshakes - Situation framing, constraint extraction, intent detection
   - **Layer 2**: Feature Extraction - Decision state → bounded numeric vectors
   - **Layer 3**: KIS - 5-factor knowledge scoring (domain, type, memory, context, goal)
   - **Layer 4**: ML Judgment Priors - Learn which knowledge types matter in similar decisions

### Integration Points

```
User Input → Mode Orchestrator → [Decision Routing] → Ministers or Direct LLM
                                      ↓
                                  Minister Analysis + KIS
                                      ↓
                                  Prime Confident (Final Authority)
                                      ↓
                            Store Episode → Record Metrics → Extract Patterns
```

---

## Essential Conventions & Patterns

### 1. Knowledge Integration System (KIS)

**Location**: `persona/knowledge_engine.py` and `ml/kis/`

Every decision involving multiple perspectives calls `synthesize_knowledge()`:
```python
from persona.knowledge_engine import synthesize_knowledge

kis_result = synthesize_knowledge(
    user_input="Should I change careers?",
    active_domains=["career", "wealth"],
    domain_confidence=0.8
)
# Returns: {"synthesized_knowledge": [...], "relevance_scores": {...}}
```

**5-Factor KIS Scoring**: Domain weight (0.25–1.4) × Type weight (0.9–1.1) × Memory weight (1.0–~8.0) × Context weight (0.85–1.4) × Goal alignment

### 2. Minister Pattern

**Location**: `sovereign/ministers/{domain}.py`

```python
from persona.ministers import MINISTERS

# Each minister module must:
# 1. Load its minister class (e.g., RiskMinister)
# 2. Generate KIS for its domain
# 3. Return MinisterModuleOutput: {minister_name, domain, stance, confidence, kis_data}
# 4. Invoke via Prime Confident for final decision

# To add a minister's logic:
minister_module = minister_factory("risk")
output = minister_module.analyze(user_input, context)
```

**Critical Rule**: Ministers provide positions; Prime Confident owns the decision. Never let ministers negotiate with users mid-decision.

### 3. Mode-Specific Routing

**Location**: `persona/modes/mode_orchestrator.py`

Every decision checks mode via `ModeOrchestrator`:
```python
from persona.modes.mode_orchestrator import ModeOrchestrator

orchestrator = ModeOrchestrator()
mode_response = orchestrator.decide(user_input, context)
# Returns: ModeResponse(text, mode, ministers_involved, reasoning)
```

**Mode Rules** (sacred—don't break):
- QUICK: No council invocation, direct LLM
- WAR: Risk + Power + Intelligence always; filter others by aggressiveness
- MEETING: Diplomacy + Data always; rotate others by relevance
- DARBAR: All 19 ministers, full KIS synthesis, consensus-seeking

### 4. Trace & Observability

**Location**: `persona/trace.py`

For debugging and audit trails:
```python
from persona.trace import trace

trace("decision_point", {
    "mode": "MEETING",
    "ministers": ["Risk", "Data"],
    "confidence": 0.87
})
```

This logs to `logs/` for reconstruction of reasoning chains.

### 5. Async Patterns

**Location**: `ingestion/v2/src/`

For embedding/LLM calls:
- Use `aiohttp` for concurrent HTTP calls, not sequential requests
- Queue-based pipeline: Reader → Embed → DB Write (each stage independent)
- Never block on LLM calls; batch or parallelize instead
- `asyncpg` for database operations

---

## Critical Workflows & Commands

### Run the System

```bash
# Main simulation with synthetic humans
python sovereign_main.py

# Persona N interactive conversation
python -u -m persona.main
python run_persona_conversation.py

# ML layer testing
python test_ml_layer.py
```

### Run Tests

```bash
# All tests
cd c:\era
pytest tests/ -v

# Specific suite
pytest tests/verification/ -v
pytest tests/ -k "test_embed" -v

# With Python runner
python tests/run_tests.py --coverage
```

### Check System Status

```bash
# Verify KIS engine
python tests/verification/check_doctrine.py

# Check ingestion pipeline
python tests/verification/check_ingestion_status.py

# Validate LLM integration
python tests/verification/verify_llm_integration.py
```

---

## Data Structures & State Management

### Persona State

**Location**: `persona/state.py`

```python
from persona.state import PersonaState

state = PersonaState()
state.set_mode("MEETING")
state.add_episode(user_input, decision, outcome)
state.get_metrics()  # Returns: {mode_perf, minister_contributions, kis_quality}
```

### Episode Storage

Every turn stores:
```json
{
  "ts": "2026-02-17T...",
  "turn": 42,
  "mode": "MEETING",
  "user_input": "...",
  "ministers": ["Risk", "Data", "Diplomacy"],
  "kis_summary": {...},
  "decision": "...",
  "outcome_feedback": {...},
  "personality_drift": {...}
}
```

Location: `logs/{persona_id}.log` or `persona/persistence/`

---

## Common Patterns to Reuse

### Pattern 1: Multi-Minister Consensus

```python
# In persona/council/dynamic_council.py
positions = [minister.analyze(input) for minister in selected_ministers]
aggregated = aggregate_by_mode(positions, mode="MEETING")
final = prime_confident.decide(aggregated, user_input)
```

### Pattern 2: KIS + Context-Aware Reasoning

```python
kis = synthesize_knowledge(input, active_domains=detected_domains)
feature_vector = build_feature_vector(input, context, kis)
ml_judgment = ml_wisdom.predict_outcome(feature_vector)
```

### Pattern 3: Learning from Outcomes

```python
# In ml/judgment/ml_judgment_prior.py
outcome = get_user_feedback()
label = generate_training_label(outcome, decision)
ml_system.update_judgment_weights(label, decision_context)
```

### Pattern 4: Personality Drift Detection

```python
# In hse/personality_drift.py
signals = {"stress": crisis_severity, "success_rate": outcome_reward}
drift = drift_engine.apply(human_profile, signals)
# Drift affects subsequent responses and KIS activation
```

---

## Project-Specific Gotchas

1. **Minister Voting**: Not democratic—mode determines who votes. QUICK mode has no vote.
2. **KIS Caching**: Results cached per minister per input. Invalidate if doctrine updates.
3. **Ollama Integration**: Requires running Ollama service. Models: `deepseek-r1:8b`, `qwen3:14b`
4. **Async Pipeline**: Don't use `requests` for embedding; use `aiohttp` with proper backpressure.
5. **Episode Logging**: Logs unrotated—disk management needed for production.
6. **Personality Drift**: Accumulates over time; can cause "persona corruption" if not monitored.

---

## Key Files Reference

| File | Purpose | Pattern |
|------|---------|---------|
| `persona/modes/mode_orchestrator.py` | Decision routing by mode | Extend `ModeStrategy` for new mode |
| `sovereign/ministers/{domain}.py` | Domain-bounded advisor | Implement `.analyze()` returning `MinisterModuleOutput` |
| `ml/ml_orchestrator.py` | Learning pipeline | Call `.process_decision()` with outcomes |
| `persona/knowledge_engine.py` | KIS generation | `synthesize_knowledge(input, domains)` |
| `tests/run_tests.py` | Test runner | Use `pytest.ini` markers: `@pytest.mark.integration` |
| `hse/population_manager.py` | Synthetic humans | `.create(n=3)` for multi-agent stress tests |

---

## When Stuck: Documentation Roadmap

- **Architecture questions**: [SOVEREIGN_ORCHESTRATOR_GUIDE.md](../SOVEREIGN_ORCHESTRATOR_GUIDE.md)
- **Mode selection logic**: [MODE_SELECTION_GUIDE.md](../MODE_SELECTION_GUIDE.md)
- **ML wisdom system**: [ml/README.md](ml/README.md)
- **Minister patterns**: [sovereign/ministers/README.md](sovereign/ministers/README.md)
- **Test suite**: [tests/README.md](tests/README.md)
- **Integration examples**: [sovereign_main_integration_example.py](sovereign_main_integration_example.py)
