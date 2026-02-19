# Advanced Decision Guidance System

## Summary

**Single unified system for intelligent problem-solving with natural back-and-forth dialogue:**

**NEW:** Multi-turn conversational dialogue where Prime asks clarifying questions and User LLM responds authentically.

| Feature | Status |
|---------|--------|
| Auto problem generation | ✓ |
| Session management | ✓ |
| Domain detection | ✓ |
| KIS synthesis | ✓ |
| Dynamic council | ✓ |
| Prime Confident | ✓ |
| Mode escalation | ✓ |
| Episodic learning | ✓ |
| ML analysis | ✓ |
| Session continuity | ✓ |
| Performance metrics | ✓ |
| Continuous loop | ✓ |
| User input mode | ✓ |

---

## Implementation

### Core File
- **system_main.py** (29.8 KB, 600+ lines)
  - Complete system implementation
  - Single unified codebase
  - Both auto and manual problem sources

### Supporting Modules
- **persona/** - Decision agent, domains, sessions, council, learning
- **ml/** - Learning orchestrator, pattern extraction, KIS synthesis
- **sovereign/** - Prime Confident, decision authority, minister coordination
- **llm/** - LLM interfaces and adapters
- **hse/** - Human simulation, personality modeling
- **multi_agent_sim/** - Multi-agent orchestration
- **tests/** - Verification and integration tests
- **scripts/** - Utility and helper scripts

---

## Architecture: 9-Phase Unified Flow with Conversational Dialogue

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Problem Generation/Input                           │
│   • Auto: LLM generates realistic problem (User-deepseek)   │
│   • Manual: User types problem statement                    │
└──────────────┬────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────┐
│ PHASE 2: Domain Analysis                                   │
│   • Auto-detect 15 domains                                │
│   • Analyze stakes (low/medium/high)                      │
│   • Classify reversibility                                │
│   • Calculate domain confidence                           │
└──────────────┬────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────┐
│ PHASE 3: Session Continuity Check                         │
│   • Find related previous sessions                        │
│   • Load learned patterns                                 │
│   • Link to parent session if follow-up                   │
└──────────────┬────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────┐
│ PHASE 4: Session Start                                     │
│   • Initialize SessionManager                             │
│   • Create unique session ID                              │
│   • Set initial mode (QUICK)                              │
└──────────────┬────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────┐
│ PHASE 5: Conversational Dialogue Phase (3 Exchanges)     │
│                                                            │
│   Multi-Turn Back-and-Forth Clarification:                │
│   ┌──────────────────────────────────────────────────┐  │
│   │ CLARIFICATION EXCHANGE 1                         │  │
│   │ ├─ Prime asks 2-3 clarifying questions          │  │
│   │ ├─ User LLM responds with rich details          │  │
│   │ └─ Store exchange in dialogue context           │  │
│   └──────────────────────────────────────────────────┘  │
│   ┌──────────────────────────────────────────────────┐  │
│   │ CLARIFICATION EXCHANGE 2                         │  │
│   │ ├─ Prime asks follow-up questions               │  │
│   │ ├─ User LLM provides more context               │  │
│   │ └─ Full context accumulates                      │  │
│   └──────────────────────────────────────────────────┘  │
│   ┌──────────────────────────────────────────────────┐  │
│   │ CLARIFICATION EXCHANGE 3                         │  │
│   │ ├─ Prime asks specific questions                │  │
│   │ ├─ User LLM clarifies constraints/values        │  │
│   │ └─ Prepare for synthesis phase                  │  │
│   └──────────────────────────────────────────────────┘  │
│                                                            │
│   Synthesis with Full Context (not just initial problem)  │
│   ├─ KIS Synthesis (15-20+ knowledge items)              │
│   ├─ Mode Escalation (QUICK→MEETING→WAR→DARBAR)         │
│   ├─ Council Invocation (relevant ministers)             │
│   └─ Prime's Informed Decision (based on full dialogue)   │
└──────────────┬────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────┐
│ PHASE 6: User LLM Feedback                                │
│   • User LLM evaluates Prime's guidance authentically     │
│   • Responds with hesitations, thoughts, enthusiasm       │
│   • Dialogue naturally reveals satisfaction               │
└──────────────┬────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────┐
│ PHASE 7: Natural Satisfaction Assessment                 │
│   • Not binary yes/no - assessed from dialogue quality    │
│   • Evaluate emotional tone and resonance                 │
│   • Check willingness to move forward                     │
│   • Record satisfaction in session manager                │
└──────────────┬────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────┐
│ PHASE 8: Episode + Metrics Storage                       │
│   • Store full dialogue context in Episode                │
│   • Record PerformanceMetrics with dialogue data          │
│   • Persist to: data/memory/episodes.jsonl               │
│                 data/memory/metrics.jsonl                │
└──────────────┬────────────────────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────┐
│ PHASE 9: ML Analysis & Learning                          │
│   • Analyze dialogue effectiveness by domain              │
│   • Extract patterns from conversation quality            │
│   • Learn what questions work best                        │
│   • Generate improvement recommendations                  │
│   • Continuous learning for next sessions                 │
└──────────────┬────────────────────────────────────────────┘
               │
         [Next Session Uses
          Learned Dialogue Patterns]
```

---

## Operating Modes

### Mode 1: Auto (LLM-Generated Problems)
```bash
python system_main.py
```

**Behavior:**
1. Generates realistic problem via User LLM (deepseek-r1:8b)
2. Analyzes domains, stakes, reversibility
3. Runs multi-turn dialogue (KIS + Council + Prime)
4. Stores episode and metrics
5. ML analysis and learning
6. Automatically starts next session
7. **Continuous loop** until Ctrl+C

**Use case:** Research, bulk testing, observing system improvement

### Mode 2: Manual (User-Provided Problems)
```bash
python system_main.py --mode manual
```

**Behavior:**
1. Shows menu: `[Menu] > `
2. User types problem statement
3. Runs multi-turn dialogue
4. Shows results and learning
5. Waits for next user input
6. Commands: `exit` (quit), `stats` (show statistics), `[Enter]` (new problem)

**Use case:** Personal use, manual testing, controlled experiments

---

## System Components

### 1. **OllamaRuntime (LLMs)**
- **User LLM:** deepseek-r1:8b (generates problems, evaluates satisfaction)
- **Program LLM:** qwen3:14b (domain detection, council guidance, prime decision)

### 2. **Domain Detector**
- 15 domain keywords (career, finance, health, relationships, psychology, etc.)
- Stakes: low/medium/high
- Reversibility: reversible/partially_reversible/irreversible
- Confidence scoring

### 3. **Session Manager**
- Session lifecycle: start → add_turn → record_satisfaction → end
- Mode escalation: QUICK → MEETING → WAR → DARBAR
- Related session discovery
- Session persistence: data/sessions/completed/*.json
- Consequence tracking: data/sessions/consequences.jsonl

### 4. **KIS (Knowledge Integration System)**
- Retrieves domain-relevant knowledge items
- 40,162+ doctrine entries
- Weighted by: domain relevance, knowledge type, memory, context, goal alignment

### 5. **Dynamic Council**
- Selects ministers per mode:
  - QUICK: No council (direct LLM)
  - MEETING: Diplomacy + Data + 1-3 others
  - WAR: Risk + Power + Intelligence always
  - DARBAR: All 19 ministers voting

### 6. **Prime Confident**
- Final decision authority
- Integrates all council input
- Synthesizes reasoning
- Provides confidence score (0-100%)

### 7. **EpisodicMemory**
- Stores Episode objects with:
  - Problem statement
  - Decision made
  - Confidence level
  - Outcome (success/partial/failure)
  - Regret score
- File: data/memory/episodes.jsonl

### 8. **PerformanceMetrics**
- Tracks per domain:
  - Turns needed
  - Success rate
  - Average confidence
  - Weak vs strong domains
- File: data/memory/metrics.jsonl

### 9. **ML Orchestrator**
- Pattern extraction
- Domain effectiveness analysis
- Weak domain identification
- Learning suggestions
- Cross-session pattern recognition

### 10. **Mode Orchestrator**
- Automatic mode escalation
- Turn-count based progression
- Complexity adaptation

---

## Data Flow & Storage

### Input
```
User Problem (auto-generated or typed)
       ↓
Domain Detection
       ↓
Session Start
```

### Processing
```
KIS Synthesis (retrieve knowledge)
       ↓
Council Decision (minister positions)
       ↓
Prime Confident (final recommendation)
       ↓
User Satisfaction Check
       ↓
Repeat until satisfied or max turns
```

### Output & Storage
```
Episode Storage
   → data/memory/episodes.jsonl
   
Metrics Recording
   → data/memory/metrics.jsonl
   
Session Data
   → data/sessions/completed/*.json
   
Conversations
   → data/conversations/*.json
   
ML Insights
   → Printed to console
   → Optionally stored for analysis
```

---

## Session Flow Example

```
==================== SESSION 1 ====================

[Problem] Should I change careers?
  → Domains: career, finance, psychology
  → Stakes: high
  → Reversibility: partially_reversible

[Mode QUICK - Turn 1]
  KIS: 5 items retrieved
  Council: 1 minister
  Prime: "Let's explore your motivation..."
  Satisfaction: PARTIAL

[Mode QUICK - Turn 2]
  KIS: 5 items retrieved
  Council: 1 minister
  Prime: "Consider financial runway..."
  Satisfaction: PARTIAL

[Mode MEETING - Turn 3]
  KIS: 10 items retrieved
  Council: 4 ministers
  Prime: "Final recommendation: 12-month plan..."
  Satisfaction: SATISFIED ✓

Result: 3 turns, 87% confidence

[ML Analysis]
Pattern: "Career domain responds well to structured approach"
Learning: "KIS + quick council works for this domain"

================== SESSION 2 (Learns from 1) ==================

[Problem] Should I freelance?
  → Domains: career, finance
  → Related: Session 1 about career change
  → ML: "Found successful pattern"

[Mode QUICK - Turn 1]
  Applied learned approach
  Prime: "Based on similar past guidance..."
  Satisfaction: SATISFIED ✓

Result: 1 turn, 92% confidence (IMPROVEMENT!)

[ML Analysis]
Pattern: "Learned pattern successfully applied"
Learning: "Reuse strategy for career domain"
```

---

## Features Summary

| Feature | Status | Details |
|---------|--------|---------|
| **Problem Generation** | ✅ | User LLM generates realistic problems |
| **Domain Detection** | ✅ | 15 domains auto-detected with stakes/reversibility |
| **KIS Synthesis** | ✅ | Retrieves 5-10 knowledge items from 40K+ doctrine |
| **Dynamic Council** | ✅ | Mode-based minister selection and consensus |
| **Prime Confident** | ✅ | Final decision authority with confidence scores |
| **Mode Escalation** | ✅ | QUICK→MEETING→WAR→DARBAR automatic progression |
| **Satisfaction Checking** | ✅ | LLM or manual evaluation |
| **Episode Storage** | ✅ | Persistent episodic memory for learning |
| **Metrics Tracking** | ✅ | Per-domain performance tracking |
| **ML Analysis** | ✅ | Pattern extraction and weak domain ID |
| **Session Continuity** | ✅ | Related session discovery and context |
| **Automatic Loop** | ✅ | Continuous sessions with learning |
| **Interactive Mode** | ✅ | Manual user input mode |
| **Statistics** | ✅ | Session summary and analytics |

---

## Quick Start

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Run the system (automatic mode)
python system_main.py

# OR: Interactive mode  
python system_main.py --mode interactive
```

## Design Philosophy

This is **one unified system**, not a combination of two approaches:

- Single codebase handles all decision guidance scenarios
- Problem input is flexible (auto-generated or user-provided)
- Decision pipeline is consistent regardless of problem source
- Learning system operates identically in both modes
- Both operating modes share the same core architecture
- Seamless switching between modes via command-line argument

---

## Documentation

- **UNIFIED_SYSTEM_GUIDE.txt** - Complete user guide
- **system_main.py** - Source code with comments
- **Architecture:** 8-phase flow, 10 components, 2 modes
- **Data:** 4 storage locations (episodes, metrics, sessions, conversations)

---

## Files Organization

```
c:\era\
├── system_main.py ← MAIN EXECUTABLE (ALL-IN-ONE)
├── UNIFIED_SYSTEM_GUIDE.txt ← USER GUIDE
├── persona/ ← Agent system
├── ml/ ← Learning components
├── sovereign/ ← Decision authority (Prime Confident)
├── data/
│   ├── sessions/completed/
│   ├── memory/
│   │   ├── episodes.jsonl
│   │   └── metrics.jsonl
│   └── conversations/
└── ...
```

---

## Ready to Use ✅

The system is production-ready:
- ✅ All imports verified
- ✅ All components integrated
- ✅ Both modes functional
- ✅ Learning pipeline complete
- ✅ Zero redundancy
- ✅ Clean single entrypoint

**Run:** `python system_main.py`
