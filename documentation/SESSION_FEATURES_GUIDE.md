# Session-Based Problem Solving System

## Overview

Implemented a complete session-based problem-solving workflow that integrates all Persona N features:

1. **Domain Detection** - Auto-parse problem statements to identify relevant domains
2. **Session Management** - Track multi-turn conversations with full lifecycle
3. **Consequence Tracking** - Record follow-up outcomes and learn from them
4. **Session Replay** - Reference previous similar problems for continuity
5. **Problem Continuity** - Link follow-up problems to original sessions

---

## Components

### 1. Domain Detector (`persona/domain_detector.py`)

**Purpose**: Automatically analyze problem statements to extract domains, stakes, and reversibility.

**Key Functions**:

```python
# Analyze a complete situation
analysis = analyze_situation(problem_statement, llm_adapter=None)
# Returns: {
#   "problem": str,
#   "domains": ["career", "psychology", ...],
#   "domain_confidence": 0.85,
#   "stakes": "high|medium|low",
#   "reversibility": "fully_reversible|partially_reversible|irreversible",
#   "key_entities": [],
#   "domain_scores": {...}
# }

# Detect domains by keywords
domains_scores = detect_domains_by_keywords(problem_statement, threshold=1)

# Estimate stakes level
stakes = detect_stakes(problem_statement)  # Returns: "high", "medium", or "low"

# Assess decision reversibility
reversibility = detect_reversibility(problem_statement)
```

**Domain Mapping** (15 domains): career, psychology, risk, strategy, power, optionality, timing, technology

**Stakes Detection**:
- **High**: "urgent", "emergency", "critical", "dangerous", "quit", "death"
- **Medium**: "soon", "important", "concern", "conflict", "problem"
- **Low**: everything else

**Reversibility Assessment**:
- **Irreversible**: "quit", "resign", "divorce", "relocate", "surgery"
- **Partially Reversible**: "try", "experiment", "test"
- **Fully Reversible**: default

---

### 2. Session Manager (`persona/session_manager.py`)

**Purpose**: Manage the complete lifecycle of problem-solving sessions with persistence.

**Session Lifecycle**:

```
START SESSION (problem_statement, domains, domain_confidence, stakes)
         ↓
ADD TURNS (mode, user_input, council_positions, prime_decision, kis_items)
         ↓
CHECK SATISFACTION (user_satisfied, confidence)
         ↓
ESCALATE MODE (based on turn count)
         ↓
END SESSION (conclusion, satisfaction, confidence)
         ↓
STORE EPISODE (save to data/sessions/completed/)
```

**Key Methods**:

```python
manager = SessionManager(storage_dir="data/sessions")

# Start a new session
session = manager.start_session(
    problem_statement="I'm overwhelmed at work",
    domains=["career", "psychology"],
    domain_confidence=0.85,
    stakes="high",
    reversibility="partially_reversible",
    parent_session_id=None  # Link to previous session
)

# Record a turn during conversation
turn = manager.add_turn(
    mode="QUICK|MEETING|WAR|DARBAR",
    user_input="...",
    council_positions=[...],
    prime_decision="...",
    kis_items=[...],
    confidence=0.75
)

# Check if should continue
should_continue = manager.record_satisfaction(
    satisfied=True,
    confidence=0.85
)

# End the session
session = manager.end_session(
    conclusion="...",
    satisfaction=True,
    confidence=0.85
)
```

**Mode Escalation** (automatic):
- Turns 1-2: `QUICK` - Simple direct response
- Turns 3-5: `MEETING` - 3-5 relevant ministers
- Turns 6-8: `WAR` - Aggressive assessment
- Turns 9+: `DARBAR` - Full wisdom council (all 18 ministers)

**Session Storage**: `data/sessions/completed/session_*.json`

Each session stores:
- session_id, started_at, ended_at
- problem_statement, domains, domain_confidence
- stakes, reversibility, parent_session_id
- All turns with mode, decision, KIS items
- Final conclusion, satisfaction, confidence

---

### 3. Consequence Tracking

**Purpose**: Record what happened after a session ended (did user follow through? what was the outcome?)

**Usage**:

```python
# Record a consequence follow-up
manager.record_consequence(
    session_id="session_12345_abc",
    followup="User negotiated with manager",
    outcome="Manager agreed to 30% workload reduction"
)

# Retrieve all consequences for a session
consequences = manager.load_consequences_for_session(session_id)
# Returns: [{session_id, followup, outcome, recorded_at}, ...]
```

**Storage**: `data/sessions/consequences.jsonl` (append-only log)

**Learning Value**:
- Tracks whether advice was followed
- Records actual outcomes vs predicted outcomes
- Enables future regret analysis
- Improves judgment priors for similar domains

---

### 4. Session Replay & Continuity

**Purpose**: Reference previous sessions to provide context for current problems.

**Methods**:

```python
# Find sessions with related domains
related = manager.find_related_sessions(
    current_domains=["career", "psychology"],
    limit=3
)

# Get formatted context from related sessions
context = manager.get_session_context_for_continuity(current_domains)
# Useful for prepending to LLM prompts

# Create a follow-up session explicitly linked to a previous one
follow_up = manager.create_followup_session(
    parent_session_id="session_12345_abc",
    followup_problem="I tried negotiation but it didn't work"
)

# View session statistics
stats = manager.get_session_statistics()
# Returns: {
#   total_sessions, avg_turns, satisfaction_rate,
#   most_common_domains, avg_confidence
# }
```

**Use Cases**:

1. **Related Problem Reference**: "Career conflicts" session links to previous "Team dynamics" session
2. **Continuity Tracking**: "Follow-up to yesterday's burnout discussion" explicitly links to prior session
3. **Pattern Recognition**: Statistics show if certain domains have higher satisfaction rates
4. **Learning from Consequences**: Outcomes inform future decisions in similar domains

---

## Session-Based Conversation Flow

### File: `run_session_conversation.py`

Entry point for multi-session problem-solving conversations.

**Full Workflow**:

```
1. USER PROVIDES PROBLEM
   Input: "I'm feeling overwhelmed at work"

2. DOMAIN DETECTION (auto)
   ↳ Extract: domains=["career", "psychology"], stakes="high"

3. CHECK SESSION CONTINUITY (auto)
   ↳ Find related previous sessions
   ↳ Note if this is a follow-up

4. START SESSION
   ↳ Initialize with detected parameters

5. MULTI-TURN LOOP (up to 15 turns max):
   Turn 1: Mode=QUICK  → LLM analysis
   Turn 2: Mode=QUICK  → Refinement
   Turn 3: Mode=MEETING → 3-5 ministers
   Turn 4: Mode=MEETING → Council consensus
   Turn 5: Mode=MEETING → Deeper dive
   Turn 6+: Mode=WAR/DARBAR → Escalated wisdom
   
   Per Turn:
   a) KIS Synthesis (retrieve relevant knowledge)
   b) Council Decision (mode-appropriate ministers)
   c) Prime Confident (final authority)
   d) Satisfaction Check (continue or end?)

6. SESSION CONCLUSION
   ↳ Generate summary and store

7. CONSEQUENCE TRACKING
   ↳ Offer to record follow-ups later

8. START NEW SESSION
   ↳ Loop for next problem or exit
```

**Running the System**:

```bash
# Interactive problem-solving sessions
python run_session_conversation.py

# Menu:
# [Menu] Start session > <enter>
#   → Starts new session
# [Menu] Start session > stats
#   → Shows session statistics
# [Menu] Start session > describe my problem
#   → Treats text as problem statement
# [Menu] Start session > exit
#   → Exit
```

---

## Data Storage Structure

```
data/sessions/
├── completed/
│   ├── session_1708270219_a1b2c3d4.json
│   ├── session_1708270445_f5e6d7c8.json
│   └── ...
├── consequences.jsonl            # Append-only consequence log
└── problems.jsonl               # Problem registry (future)

data/memory/
├── episodes.jsonl               # Episodic memory (from main.py)
├── metrics.jsonl                # Performance metrics (from main.py)
└── ... (existing files)
```

---

## Integration with Existing Systems

### Mode Orchestrator
- Automatically selects mode based on turn count
- Respects mode-specific council size rules
- Works with existing ModeOrchestrator class

### Knowledge Integration System (KIS)
- Retrieves knowledge based on auto-detected domains
- Uses domain_confidence for relevance scoring
- Returns 5-10 items depending on mode

### Dynamic Council
- Invokes appropriate number of ministers per mode
- Receives active domains from problem analysis
- Returns consensus positions for Prime Confident

### Prime Confident
- Makes final decision based on council input
- Uses doctrine to prevent emotional reasoning
- Records confidence score

### Episodic Memory & Metrics
- Sessions stored as episodes with outcomes
- Learning signals generated automatically
- Pattern extraction from session data

---

## Example Usage Scenario

```
User: "I'm burnout at work and considering quitting"

System Analysis:
  ✓ Domains detected: career, psychology, risk
  ✓ Stakes: high
  ✓ Reversibility: irreversible
  ✓ Found 2 related sessions from 3 months ago

=== SESSION START ===

Turn 1 (QUICK):
  [KIS] 5 items synthesized
  [Decision] "Consider negotiating workload first"
  [Satisfaction] "That helps, but not enough depth"

Turn 2 (QUICK):
  [KIS] 5 items synthesized
  [Decision] "Explore specific stress sources"
  [Satisfaction] "Good progress, but need more options"

Turn 3 (MEETING):
  [KIS] 10 items synthesized
  [Council] Risk + Psychology + Strategy ministers
  [Decision] "Three-part plan: negotiate → support → evaluate"
  [Satisfaction] "Yes, this feels complete"

=== SESSION END ===
Conclusion: User will attempt workload negotiation before considering resignation
Confidence: 0.92
Satisfaction: YES

Follow-up offered: "When you implement this, please report back on outcomes"

=== NEW SESSION AVAILABLE ===
```

---

## Features Summary

| Feature | Status | File | Storage |
|---------|--------|------|---------|
| Domain Detection | ✅ Complete | `persona/domain_detector.py` | In-memory |
| Session Management | ✅ Complete | `persona/session_manager.py` | `data/sessions/completed/*.json` |
| Turn Tracking | ✅ Complete | SessionManager | Within session JSON |
| Mode Escalation | ✅ Complete | SessionManager | In-memory (turn count) |
| Satisfaction Checking | ✅ Complete | SessionManager | Within session JSON |
| Consequence Tracking | ✅ Complete | SessionManager | `data/sessions/consequences.jsonl` |
| Session Replay | ✅ Complete | SessionManager | `find_related_sessions()` |
| Continuity Linking | ✅ Complete | SessionManager | `parent_session_id` field |
| Statistics | ✅ Complete | SessionManager | `get_session_statistics()` |
| Session Persistence | ✅ Complete | SessionManager | JSON + JSONL |
| Multi-Session Loop | ✅ Complete | `run_session_conversation.py` | Orchestrated |

---

## Testing

Run the test suite to validate all features:

```bash
python test_session_workflow.py
```

Tests cover:
- Domain detection from various problem types
- Session creation and turn recording
- Mode escalation logic
- Satisfaction recording
- Consequence tracking
- Related session finding
- Session continuity context
- Statistics generation

---

## Future Enhancements

1. **LLM-powered domain detection** - Enhance keyword matching with LLM analysis
2. **Consequence outcome learning** - Use recorded consequences to update judgment priors
3. **Pattern visualization** - Graph domains, satisfaction rates, vs time
4. **Session comparison** - Show how current session differs from related ones
5. **Persona adaptation** - Adjust posture based on historical satisfaction patterns
6. **Consequence scheduling** - Remind users to report back on session outcomes
7. **Cross-session reasoning** - Use related sessions in council deliberations
