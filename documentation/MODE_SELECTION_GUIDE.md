# Mode Selection & Orchestration Guide

## Overview

Persona N now supports **4 distinct decision-making modes**, each with a different pipeline and optimization. The mode you select fundamentally changes how decisions are made.

## Modes at a Glance

| Mode | Council | Ministers | Use Case | Advice Style |
|------|---------|-----------|----------|--------------|
| **QUICK** | ❌ No | None | Initial exploration, casual advice, emotional support | Personal, intuitive, exploratory |
| **WAR** | ✅ Yes | 5 (Risk, Power, Strategy, Tech, Timing) | Victory-focused, competitive, defensive crises | Aggressive, rapid, short-term optimized |
| **MEETING** | ✅ Yes | 3-5 (domain-relevant) | Complex decisions, multi-stakeholder issues | Balanced, consensus-seeking, thoughtful |
| **DARBAR** | ✅ Yes | 18 (all ministers) | High-stakes decisions, existential questions | Deep, nuanced, multi-perspective wisdom |

## Starting the System

When you run `python -m persona.main`, you'll see:

```
============================================================
PERSONA N - DECISION MODE SELECTION
============================================================

Select your decision-making mode:
  [1] QUICK MODE      - 1:1 mentoring (personal, fast, no council)
  [2] WAR MODE        - Victory-focused (aggressive, Risk/Power/Strategy)
  [3] MEETING MODE    - Balanced debate (3-5 relevant ministers)
  [4] DARBAR MODE     - Full council wisdom (all 18 ministers)

Enter mode [1-4] (default: 3/MEETING):
```

### Default: MEETING MODE
If you press Enter without selecting, the system defaults to **MEETING MODE** — a balanced approach suitable for most situations.

## Mode Descriptions

### 1. QUICK MODE 🚀
**Decision Pipeline:** User Input → Direct LLM Response (No Council)

**When to use:**
- Initial exploration of a new topic
- Need fast, intuitive advice
- Building rapport with Persona
- Personal mentoring/coaching
- You want a thinking partner, not a consensus

**Characteristics:**
- No ministerial council
- Direct, personal LLM response
- Fast turnaround
- Conversational, warm tone
- Good for brainstorming

**Example:**
```
USER: I'm thinking about changing careers
QUICK MODE: Persona responds as a mentor would—asking clarifying questions,
            exploring your motivations, building understanding
            (No background analysis of risk vs opportunity)
```

---

### 2. WAR MODE ⚔️
**Decision Pipeline:** User Input → 5 Ministers (Risk, Power, Strategy, Tech, Timing) → Council Consensus

**When to use:**
- Competitive situations (job negotiations, market entry, rivalry)
- Defensive crises (reputation damage, resource loss)
- Need to "WIN" in the short-term
- High-stakes, time-critical decisions
- You're willing to sacrifice long-term relationships for winning moves

**Characteristics:**
- Invokes 5 ministers specifically trained for victory:
  - **Risk**: Downside protection, existential safeguards
  - **Power**: Leverage & advantage maximization
  - **Strategy**: Strategic wins & positioning
  - **Technology**: Tactical advantage & innovation
  - **Timing**: Strike when ready, momentum exploitation
- Frame: "How do we WIN this?"
- Optimizes for speed and competitive advantage
- Aggressive but smart (never violates ethics or ignores existential risks)

**Red Lines (Still Enforced):**
- ❌ Existential risks (death, bankruptcy, legal trouble)
- ❌ Irreversible damage that outlasts the victory
- ❌ Fraud, corruption, illegality

**Example:**
```
USER: A competitor just undercut my prices. How do we fight back?
WAR MODE: Council convenes focusing on Power (leverage), Strategy (market positioning),
          Risk (ensure we don't destroy long-term value), and Timing (strike window).
          
          Recommendation: Aggressive short-term move that establishes dominance
          while protecting long-term viability.
```

---

### 3. MEETING MODE 🤝
**Decision Pipeline:** User Input → 3-5 Relevant Ministers (domain-chosen) → Consensus + Synthesis

**When to use:**
- Complex decisions with multiple stakeholders
- Balanced advice needed
- Moderate urgency
- Decision affects multiple life domains
- You want diverse perspectives synthesized into consensus

**Characteristics:**
- Domain-intelligent minister selection (3-5 ministers)
- Each minister presents their perspective
- Structured debate showing agreements and disagreements
- Synthesis into balanced recommendation
- Respects multiple viewpoints

**Domain-to-Minister Mapping:**
- **Career**: Grand Strategist, Psychology, Timing
- **Financial**: Risk, Optionality, Data
- **Relationships**: Diplomacy, Psychology, Legitimacy
- **Health**: Psychology, Timing, Risk
- **Strategy**: Grand Strategist, Intelligence, Timing
- **Power**: Power, Diplomacy, Conflict
- **Ethics**: Legitimacy, Truth, Discipline
- **Innovation**: Technology, Grand Strategist, Risk

**Example:**
```
USER: Should I accept a promotion that requires relocating my family?
MEETING MODE: Council convenes with Diplomacy (family aspect), Psychology (emotional),
              Grand Strategist (career), Risk (downside), and Timing (window).
              
              Each presents perspective. Synthesis shows tradeoffs:
              - Short-term: family disruption vs career acceleration
              - Long-term: location flexibility vs career trajectory
              
              Balanced recommendation: Yes IF you can secure...
```

---

### 4. DARBAR MODE 👑
**Decision Pipeline:** User Input → 18 Ministers (Full Council) → Deep Deliberation → Doctrine-Compliant Synthesis

**When to use:**
- Existential decisions (life direction, values reorientation)
- High-stakes with complex ethical dimensions
- Final arbitration needed
- You want the deepest wisdom your system can offer
- Decision sets precedent for future choices

**Characteristics:**
- ALL 18 ministers convened
- Full doctrine-driven deliberation
- Multiple perspectives on every dimension
- Red lines explicitly surfaced:
  - **Legitimacy violations** (fraud, corruption, illegality)
  - **Truth violations** (deception, manipulation)
  - **Fundamental harm** (death, irreversible damage, existential risk)
- If red lines triggered, recommendation is blocked with explanation

**All Ministers Present:**
Adaptation, Conflict, Diplomacy, Data, Discipline,
Grand Strategist, Intelligence, Timing, Risk, Power,
Psychology, Technology, Legitimacy, Truth, Narrative,
Resources, Optionality, Sovereign

**Example:**
```
USER: Should I blow the whistle on my company's dangerous practices?
DARBAR MODE: All 18 ministers convene. Perspectives on:
              - Risk: Personal career risk, legal exposure
              - Legitimacy: Is whistleblowing legally protected, ethical
              - Truth: Are the danger claims documented, verifiable
              - Power: What leverage do I have, employer retaliation risk
              - Diplomacy: Can I work internally first
              - Psychology: What's impact on my mental health/family
              - Technology: Can evidence be safely secured
              - Narrative: What's the story if I go public
              
              Red lines checked: Does following the truth/legitimacy require
              personal existential sacrifice? If yes, that's noted explicitly.
              
              Synthesis: Comprehensive wisdom with full reasoning visible.
```

---

## Switching Modes Mid-Conversation

You can change modes at any time without restarting.

### Command Syntax:
```
/mode quick
/mode war
/mode meeting
/mode darbar
```

### Example:
```
USER: /mode war
[MODE] Switched to WAR - Victory-focused (aggressive, Risk/Power/Strategy focus)
[MODE] Ministers: risk, power, grand_strategist, technology, timing

USER: Now we're switching to aggressive strategy. My competitor just...
[Response comes from war-mode council]

USER: /mode darbar
[MODE] Switched to DARBAR - Full council wisdom (all 18 ministers)

USER: Actually, before we commit to that aggressive move, I need wisdom on the
      ethical implications. Is this the right thing?
[Response comes from full-council deep deliberation]
```

## Integration with Learning Systems

Regardless of mode, all learning systems remain active:

- **EpisodicMemory**: Records every decision (all modes)
- **PerformanceMetrics**: Tracks success rates (all modes)
- **OutcomeFeedbackLoop**: Applies consequences (all modes)
- **IdentityValidator**: Checks coherence (all modes)
- **PatternExtractor**: Identifies weak domains (all modes)

### Insight: Learning is Mode-Agnostic
Whether you use Quick Mode or Darbar Mode, the learning loop captures:
- What you asked
- What we recommended
- What happened
- Whether it succeeded
- What patterns emerge

This means **you learn from all mode perspectives**, even if you favor one.

## Decision Quality by Mode

### Speed
- **Quick**: Fastest ⭐⭐⭐⭐⭐
- **War**: Fast ⭐⭐⭐⭐
- **Meeting**: Medium ⭐⭐⭐
- **Darbar**: Slowest ⭐⭐

### Depth
- **Quick**: Shallow ⭐
- **War**: Focused ⭐⭐⭐
- **Meeting**: Moderate ⭐⭐⭐
- **Darbar**: Deepest ⭐⭐⭐⭐⭐

### Consensus
- **Quick**: N/A (no council)
- **War**: Victory-focused, not consensus
- **Meeting**: Consensus-seeking ⭐⭐⭐⭐
- **Darbar**: Doctrine-compliant consensus ⭐⭐⭐⭐⭐

### Ethical Safeguards
- **Quick**: Standard LLM safety
- **War**: Victory + but red lines protected
- **Meeting**: Multi-perspective ethics
- **Darbar**: Full doctrine protection ⭐⭐⭐⭐⭐

## Recommended Mode Sequences

### For Exploration (1st-3rd turn)
```
1. Quick Mode    - Get intuitive starting direction
2. Meeting Mode  - Validate with multiple perspectives
3. Darbar Mode   - Check for deep objections if high-stakes
```

### For Competitive Decisions
```
1. War Mode      - Generate winning moves
2. Meeting Mode  - Reality-check those moves
3. Darbar Mode   - Verify ethical grounding (if major decision)
```

### For Life Decisions
```
1. Quick Mode    - Explore emotionally
2. Meeting Mode  - Get balanced perspectives
3. Darbar Mode   - Deep wisdom pass before committing
```

### For Emergency Situations
```
1. War Mode      - Fast analysis for immediate action
2. Quick Mode    - Trust your instinct for execution
3. Darbar Mode   - Debrief afterwards to learn
```

## Technical Implementation

### ModeOrchestrator (In persona/modes/mode_orchestrator.py)

The orchestrator manages all modes:

```python
from persona.modes import ModeOrchestrator

# Create orchestrator
mode_orch = ModeOrchestrator()

# Set mode
mode_orch.set_mode("war")

# Check if council needed
should_convene = mode_orch.should_invoke_council("war")  # True

# Get relevant ministers
ministers = mode_orch.get_ministers_for_mode("war", context)
# Returns: ["risk", "power", "grand_strategist", "technology", "timing"]

# Get mode-specific framing
framing = mode_orch.frame_for_mode(user_input, "war", context)
# Returns: System prompt tuned for war mode

# Aggregate results according to mode rules
aggregation = mode_orch.aggregate_for_mode(ministry_positions, "war")
# Returns: Dict with war-mode aggregation logic
```

### Main Loop Integration

In `persona/main.py`:

1. **Startup**: User selects mode (default MEETING)
2. **Each Turn**: 
   - Check for `/mode` commands
   - Pass mode_orchestrator to `_mca_decision()`
3. **MCA Decision**:
   - Get mode's minister list
   - Convene only if mode says so
   - Use mode's aggregation rules
4. **Learning**: All epis odes tagged with mode used

## FAQ

**Q: Can modes make decisions that conflict with doctrine?**
A: No. Red lines (Legitimacy, Truth, Fundamental Harm) are enforced across ALL modes. War Mode and Quick Mode still refuse unethical actions.

**Q: Does switching modes lose context?**
A: No. All episodic memory, metrics, and debates stay in context. You're switching analytical frames, not losing knowledge.

**Q: Should I use Darbar Mode for everything?**
A: No. Darbar is slower and more deliberate. Use it for:
- High-stakes decisions
- Existential questions
- Final arbitration
- Learning from past decisions
Use Quick/War/Meeting for everyday advice.

**Q: Can I see what ministers disagree about?**
A: Yes. Meeting and Darbar modes explicitly surface disagreement. Quick and War modes don't show council deliberation.

**Q: Do different modes learn differently?**
A: The learning systems are mode-agnostic. But over time, patterns emerge:
- War Mode decisions tend to succeed short-term but sometimes fail long-term
- Darbar decisions tend to be more sustainable
- This insight feeds back into future decisions

**Q: What if my current mode is wrong?**
A: Switch! `/mode meeting` or `/mode darbar` instantly. No penalties, just different perspective.

## Next Steps

1. **Run the system**: `python -m persona.main`
2. **Select a mode** (or take default: MEETING)
3. **Try asking a decision question**
4. **Switch modes** with `/mode` commands to see different perspectives
5. **After 100+ turns**: Check learning signals in metrics report

---

**Remember**: Modes are tools. The best Persona user switches modes strategically to get wisdom suited to their current situation.
