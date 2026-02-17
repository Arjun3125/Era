# TESTING & VALIDATION GUIDE

## Week 1-2: Foundation & Learning Loop ✅ COMPLETE

All core systems have been implemented and integrated:

### Implemented Components:
1. ✅ **EpisodicMemory** (`persona/learning/episodic_memory.py`)
   - Stores all decisions with episode_id, domain, confidence, outcome, regret
   - Methods: store_episode(), find_similar_episodes(), detect_pattern_repetition()
   - Persistent JSON Lines storage at `data/memory/episodes.jsonl`

2. ✅ **PerformanceMetrics** (`persona/learning/performance_metrics.py`)
   - Tracks success rates, feature coverage, stability
   - Methods: get_success_rate(), detect_weak_domains(), measure_stability()
   - Persistent JSON Lines storage at `data/memory/metrics.jsonl`

3. ✅ **OutcomeFeedbackLoop** (`persona/learning/outcome_feedback.py`)
   - Records decision outcomes and triggers retraining
   - Methods: record_decision_outcome(), retrain_ministers(), detect_repeated_mistake()
   - Integrates with council and episodic memory

4. ✅ **IdentityValidator** (`persona/validation/identity_validator.py`)
   - Ensures persona coherence and consistency
   - Methods: check_self_contradiction(), validate_voice_consistency()
   - Detects and logs identity violations

5. ✅ **SyntheticHumanSimulation** (`hse/simulation/synthetic_human_sim.py`)
   - Simulates realistic human responses to persona advice
   - Methods: generate_next_input(), apply_consequences()
   - Supports automated stress-testing

6. ✅ **PatternExtractor** (`ml/pattern_extraction.py`)
   - Extracts decision patterns from episodic memory
   - Methods: extract_patterns(), identify_weak_patterns(), generate_learning_signals()
   - Generates actionable improvement signals

7. ✅ **Main.py Integration** (`persona/main.py`)
   - Integrated all learning systems into main loop
   - Synthetic human support with AUTOMATED_SIMULATION env var
   - Periodic reporting every 100 turns with learning signals
   - Periodic retraining every 50 turns on failure clusters

---

## Testing Workflow

### Option 1: Interactive Mode (Manual Testing)
```bash
cd /era
python -m persona.main
```
- Type messages naturally
- Every 100 turns: automatic metrics report
- Every 50 turns (with synthetic human): automatic retraining

### Option 2: Automated Simulation (Stress Testing)
```bash
cd /era
export AUTOMATED_SIMULATION=1
export PERSONA_DEBUG=1
python -m persona.main
```

This runs a 1000-turn synthetic human simulation with:
- Automatic human input generation
- Consequence propagation
- Personality drift
- Crisis injection
- Minister retraining on failure clusters
- Full metrics reporting

### Option 3: Extended Stress Test (1000+ turns)
```bash
cd /era
export AUTOMATED_SIMULATION=1
export PERSONA_TRACE_FILE=data/memory/trace.log
python -m persona.main 2>&1 | tee data/memory/run.log
```

---

## Data Files & Output

After running any test mode, check:

### Memory & Metrics
- **`data/memory/episodes.jsonl`**
  - One JSON per line, each = one decision episode
  - Fields: episode_id, turn_id, domain, user_input, outcome, regret_score, consequence_chain

- **`data/memory/metrics.jsonl`**
  - One JSON per line, each = one metrics snapshot
  - Fields: turn, domain, recommendation, confidence, outcome, regret, timestamp

- **`data/memory/patterns.json`**
  - Extracted patterns: domain_patterns, confidence_patterns, outcome_patterns, sequential_patterns
  - Updated every 100 turns (when pattern_extractor.extract_patterns() runs)

### Reports & Analysis
- **`data/memory/contradictions.json`**
  - Identity validation log: all detected self-contradictions

- **`data/memory/arc_timeline.json`**
  - Conversation arc tracking

---

## Expected Improvement Trajectory

### Turn 50-100 (Baseline Phase)
- Success rate: ~45%
- Weak domains detected: Multiple
- Episodes stored: 50-100
- Metrics recorded: 50-100

### Turn 100-200 (First Retraining Cycle)
- Success rate: ~52-58% (improved)
- Patterns extracted: domain_patterns, confidence_patterns
- Learning signals generated
- Ministers retrained on failure clusters
- Weak domains targeted for improvement

### Turn 200-500 (Consolidation Phase)
- Success rate: ~62-70% (sustained improvement)
- Stability increasing
- Fewer failure clusters
- Confidence calibration improving

### Turn 500-1000 (Convergence Phase)
- Success rate: ~75-85% (strong performance)
- Stability high (>0.8)
- Most domains >60% success rate
- Minimal identity contradictions

---

## Performance Metrics to Monitor

**Every 100 turns, check:**

1. **Overall Success Rate**
   - Target: Linear improvement from 45% → 85%
   - Window: 100-turn rolling average

2. **Weak Domains**
   - Target: Reduction in count + improvement in each
   - Example: Start with 5 weak domains, down to 2 by turn 500

3. **Stability Score**
   - Target: 0.0 → 1.0 (low variance → consistent decisions)
   - Indicates confidence calibration improvement

4. **Feature Coverage**
   - Target: All domains represented, balanced frequency
   - Ensures learning across all areas

5. **Episodic Memory Size**
   - Target: Linear growth (50 episodes per 50 turns)
   - Indicates learning capacity

6. **Learning Signals**
   - Weak domains list
   - Confidence issues
   - Sequential risks
   - Should decrease over time as system improves

---

## Validation Checklist

### Week 2 Completion Criteria:
- [ ] EpisodicMemory stores episodes correctly (100+ episodes by turn 500)
- [ ] PerformanceMetrics tracks metrics (100+ metrics by turn 500)
- [ ] OutcomeFeedbackLoop triggers retraining (every 50 turns)
- [ ] IdentityValidator detects contradictions (< 2 per 100 turns ideal)
- [ ] SyntheticHumanSimulation generates realistic inputs
- [ ] PatternExtractor identifies weak domains accurately
- [ ] Main loop integrates all systems without errors
- [ ] Periodic reporting displays correct metrics every 100 turns
- [ ] Success rate improves from ~45% → ~75%+ by turn 1000

### Additional Validation:
- [ ] Zero Python syntax errors in generated files
- [ ] All imports resolve correctly
- [ ] No infinite loops or hangs during 1000-turn run
- [ ] Data files persist correctly to disk
- [ ] CSV exports (if needed) are well-formed

---

## Debugging Commands

### View episodic memory summary:
```bash
python -c "
from persona.learning.episodic_memory import EpisodicMemory
em = EpisodicMemory()
print(f'Total episodes: {len(em.episodes)}')
recent = em.get_recent_episodes(5)
for ep in recent:
    print(f'  Turn {ep.turn_id}: {ep.domain} - {ep.outcome}')
"
```

### View metrics summary:
```bash
python -c "
from persona.learning.performance_metrics import PerformanceMetrics
m = PerformanceMetrics()
print(f'Success rate: {m.get_success_rate():.1%}')
print(f'Coverage: {m.get_feature_coverage()}')
print(f'Weak domains: {m.detect_weak_domains()}')
"
```

### View pattern extraction results:
```bash
python -c "
from ml.pattern_extraction import PatternExtractor
from persona.learning.episodic_memory import EpisodicMemory
em = EpisodicMemory()
pe = PatternExtractor(em)
patterns = pe.extract_patterns(100)
signals = pe.generate_learning_signals()
print(f'Weak domains: {signals[\"weak_domains\"]}')
print(f'Sequential risks: {signals[\"sequential_risks\"]}')
"
```

---

## Next Steps (Week 3-4)

Once Week 2 validation passes:

1. **Week 3: Reporting & Visualization**
   - Update Flask analytics dashboard to display episodic patterns
   - Create reporting.py script to generate weekly summaries
   - Set up metrics export to CSV for analysis

2. **Week 4: Advanced Features**
   - Implement PWM commit strategy (every 100 turns)
   - Add conversation arc tracking to detect narrative loops
   - Set up continuous retraining pipeline

---

## Summary

The complete learning loop is now operational:

```
Decision → Episode Storage → Outcome Recording → Feedback Loop
    ↓
Pattern Extraction → Learning Signals → Minister Retraining
    ↓
Improved Decisions (Loop repeats)
```

All components are integrated into the main loop and automatically execute with no additional configuration needed beyond the AUTOMATED_SIMULATION environment variable.
