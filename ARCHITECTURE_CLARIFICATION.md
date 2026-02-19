# Architecture Clarification - Module Relationships

**Generated:** February 19, 2026  
**Status:** ⚠️ DEFERRED DECISIONS (clarification pending)

---

## Overview

This document clarifies relationships between overlapping and unclear modules in ERA. Some relationships have been resolved; others deferred pending architectural decisions.

---

## Resolved: LLM Integration Layer

### ✅ Canonical LLM Interface: `persona/ollama_runtime.py`

**Primary Implementation:** `persona/ollama_runtime.py`
- Initializes Ollama connections
- Used by `llm_conversation.py`
- Used by `system_main.py`
- Wraps structured calls to Ollama

```python
# Primary entry point
from persona.ollama_runtime import OllamaRuntime

speak_llm = OllamaRuntime(speak_model='deepseek-r1:8b')
analyze_llm = OllamaRuntime(analyze_model='qwen3:14b')
```

**Secondary Implementations:**
1. `ml/llm_handshakes/llm_interface.py` - Structured KIS calls (different purpose)
2. `llm/ollama.py` - (DEPRECATED - consolidate to primary)

**Recommendation:** `persona/ollama_runtime.py` is canonical. Consider migrating utilities from `llm/` to consolidate.

---

## Deferred: Simulation Layer Decision (hse/ vs multi_agent_sim/)

### ⚠️ Two Parallel Simulation Systems

#### 1. HSE (Human Simulation Engine) - `hse/`

**Purpose:** Synthetic human generation for stress testing
**Status:** Documented, actively maintained
**Files:**
- `hse/population_manager.py` - Create synthetic humans
- `hse/human_profile.py` - Individual profiles
- `hse/crisis_injector.py` - Stress scenarios
- `hse/analytics_server.py` - Metrics tracking

**Usage:**
```python
from hse.population_manager import PopulationManager

manager = PopulationManager()
humans = manager.create(n=5)  # 5 synthetic humans
```

**Integrated With:**
- `sovereign_main.py` (simulation runner)
- Test suites (stress testing)

---

#### 2. Multi-Agent Sim - `multi_agent_sim/`

**Purpose:** Agent-based simulation (unclear project scope)
**Status:** Less documented, may be parallel or legacy
**Files:**
- `multi_agent_sim/agents.py` - Agent implementation
- `multi_agent_sim/orchestrator.py` - Agent coordination
- `multi_agent_sim/simulation_runner.py` - Execution
- ~10 other files

**Usage:**
```python
from multi_agent_sim.orchestrator import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator()
results = orchestrator.run(config)
```

**Integrated With:**
- Tests (21 external imports)
- Other modules

---

### Decision Required

**Question:** Is `multi_agent_sim/` meant to replace `hse/`, or are they complementary?

**Options:**
1. **Option A (Consolidate):** Migrate `multi_agent_sim/` to `hse/`, deprecate legacy
   - Reduces duplication
   - Simplifies imports
   - One canonical simulation layer

2. **Option B (Clarify):** Document when to use each
   - `hse/` = Human-focused simulation
   - `multi_agent_sim/` = General agent-based simulation
   - Keep both if serving different purposes

3. **Option C (Archive):** Move `multi_agent_sim/` to `archive/` if `hse/` is sufficient
   - Simplest approach if overlap confirmed

**Current Status:** DEFERRED - Needs architect decision

**Recommendation:** Review git history and use case to decide.

---

## Deferred: Memory Architecture (Memory/ vs persona/learning/)

### ⚠️ Two Potential Memory Systems

#### 1. Episodic Learning - `persona/learning/`

**Purpose:** Short-term episodic memory and metrics
**Status:** Actively used
**Files:**
- `persona/learning/episodic_memory.py` - Episode storage
- `persona/learning/performance_metrics.py` - Metrics tracking
- `persona/learning/confidence_model.py` - Confidence scoring

**Storage Format:** JSON files in `data/memory/`

**Architecture Tier:** Tier 1 (episodic), Tier 2 (metrics)

**Data Stored:**
```json
{
  "episode_id": "...",
  "domain": "psychology",
  "outcome": "success",
  "regret_score": 0.1,
  "timestamp": "2026-02-19T..."
}
```

---

#### 2. PWM Storage - `Memory/`

**Purpose:** Personal World Model (Tier 3 - longer-term patterns)
**Status:** Documented, may be legacy
**Files:**
- `Memory/pwm.py` - Personal World Model implementation
- `Memory/schema.sql` - Database schema
- `Memory/templates/` - Template files

**Storage Format:** SQL database (different from Tier 1/2)

**Architecture Tier:** Tier 3 (PWM / patterns)

---

### Relationship Analysis

| Aspect | persona/learning/ | Memory/ |
|--------|------------------|---------|
| **Purpose** | Episodes & metrics | Patterns & PWM |
| **Storage** | JSON files | SQL database |
| **Tier** | 1-2 | 3 |
| **Format** | Flat files | Schema-based |
| **Integration** | Active | Unclear |

### Potential Overlap

- Both store decision-related data
- Both contribute to learning
- Storage formats differ (JSON vs SQL)
- Schema/relationship unclear

### Decision Required

**Question:** Is `Memory/` canonical, legacy, or complementary?

**Options:**
1. **Option A (Consolidate):** Merge into single episodic memory system
   - Simpler architecture
   - Unified storage
   - Clearer data flow

2. **Option B (Clarify):** Document that Memory/ stores Tier 3 (patterns)
   - Keep both if serving distinct purposes
   - Document data flow between tiers

3. **Option C (Archive):** Move `Memory/` to archive if `persona/learning/` is sufficient
   - If PWM not actively used

**Current Status:** DEFERRED - Needs architect decision

**Recommendation:** Run `find_python_usages` on both to see actual usage patterns.

---

## Resolved: Ingestion Pipeline

### ✅ Canonical: `ingestion/v2/`

**Primary:** Async ingestion pipeline (v2 - modern)
```bash
python ingestion/v2/run_all_v2_ingest.py
```

**Legacy:** ingestion/v1/ (older approach, keep for reference)

**Recommendation:** Use v2 only for new work. v1 is for reference/legacy support.

---

## Resolved: Analytics Layer

### ✅ Status: Verified Functional

**Location:** `analytics/`
- `analytics/dashboard.py` - Real-time metrics dashboard
- `analytics/reporting.py` - Report generation
- `analytics/improvement_tracker.py` - Improvement tracking

**Status:** Built and functional
**Integration:** Used by `hse/analytics_server.py`

**Recommendation:** Keep. Fully operational.

---

## Resolved: Utilities

### ✅ Status: Migration Scripts (Complete)

**Location:** `utils/`
- `migrate_to_consolidated.py` - Completed migration
- `batch_convert_rag_storage.py` - One-time conversion
- `cleanup_atomic_dirs.py` - One-time cleanup

**Status:** Migration complete, scripts are archived functionality
**Recommendation:** Keep for reference; migrations are done.

---

## Summary: Deferred Decisions

| Question | Modules | Status | Impact |
|----------|---------|--------|--------|
| Which simulation layer is canonical? | hse/ vs multi_agent_sim/ | ⚠️ DEFERRED | Medium |
| Do Memory/ and persona/learning/ overlap? | Memory/ vs persona/learning/ | ⚠️ DEFERRED | Low |
| Any other LLM utilities to consolidate? | llm/ + persona/ + ml/ | ✅ RESOLVED | Low |

---

## Action Items for Architect

1. **Simulation Layer (Priority: MEDIUM)**
   - Review `multi_agent_sim/` use cases
   - Decide: Consolidate with `hse/` or keep parallel?
   - Document decision in architecture

2. **Memory Architecture (Priority: LOW)**
   - Review `Memory/` schema and usage
   - Decide: Consolidate with `persona/learning/`?
   - Document tier relationships if keeping both

3. **LLM Interface (Priority: LOW - Already Resolved)**
   - ✅ Canonical: `persona/ollama_runtime.py`
   - Consider moving `llm/` utilities into canonical layer

---

## Next Steps

**For Developers:**
- Use documented canonical layers (see above)
- Avoid importing from unclear modules
- Document any new integrations

**For Architects:**
- Make decisions on simulation layer and memory architecture
- Update SYSTEM_ARCHITECTURE.md with clarity
- Add module dependency diagram

**Timeline:**
- Immediate: Use resolved modules as canonical
- This month: Make decisions on deferred items
- This quarter: Update architecture docs accordingly

---

**Last Updated:** February 19, 2026  
**Author:** Architecture Analysis  
**Status:** ⚠️ DEFERRED ITEMS IDENTIFIED

Next review: [After architect decisions made]
