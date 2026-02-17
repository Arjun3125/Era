# Dynamic Council Integration Guide

## Overview

**DynamicCouncil** wraps the existing `CouncilAggregator` with mode-aware behavior. It integrates with `ModeOrchestrator` to:

1. Route council composition based on conversation mode
2. Adjust aggregation logic for each mode
3. Control when council is invoked (QUICK mode skips it entirely)
4. Determine final recommendations based on mode rules

## Architecture

```
ModeOrchestrator (Controls which ministers)
        ↓
    DynamicCouncil (Orchestrates council behavior)
        ↓
    CouncilAggregator (Legacy - still runs ministers)
        ↓
    Individual Ministers analyze situation
        ↓
    DynamicCouncil aggregates by mode rules
        ↓
    Mode-specific recommendation
```

## Key Differences from CouncilAggregator

| Aspect | CouncilAggregator | DynamicCouncil |
|--------|-------------------|----------------|
| **Ministers** | All 18 always | Only mode-selected |
| **Quick Mode** | Invokes council | Skips council → direct response |
| **Aggregation** | Standard consensus logic | Mode-specific rules |
| **Recommendation** | Binary (support/oppose) | Mode-contextual |
| **Mode Awareness** | None | Full integration |

## Files Created

### 1. `persona/council/dynamic_council.py` (140+ lines)

The main module with:

- **DynamicCouncil** class
  - `__init__(llm)` - Initialize with base council
  - `set_mode(mode)` - Change decision mode
  - `convene_for_mode(mode, user_input, context)` - Main entry point
  - `_convene_mode_council()` - Internal council orchestration
  - `_determine_recommendation()` - Mode-specific recommendation logic
  - `get_current_mode()` - Query active mode
  - `get_mode_description(mode)` - Get mode info
  - `list_available_modes()` - List all 4 modes

### 2. `persona/council/__init__.py` (10 lines)

Package initialization that:
- Exports `DynamicCouncil`
- Documents that legacy `council.py` still exists
- Maintains backwards compatibility

## How It Works

### 1. Mode-Based Council Invocation

```python
dynamic_council = DynamicCouncil(llm=llm)

# QUICK MODE: Returns immediately without council
result = dynamic_council.convene_for_mode(
    mode="quick",
    user_input="What should I do?",
    context={}
)
# Result has: outcome="quick_mode_direct_response", ministers_involved=[]

# WAR MODE: 5 ministers focused on winning
result = dynamic_council.convene_for_mode(
    mode="war",
    user_input="How do we win?",
    context={"domains": ["competitive"]}
)
# Result has: ministers_involved=[risk, power, strategy, tech, timing]
```

### 2. Minister Selection by Mode

```python
# In DynamicCouncil._convene_mode_council():

# Get mode-appropriate ministers from ModeOrchestrator
minister_names = self.mode_orchestrator.get_ministers_for_mode(mode, context)

# Only analyze those ministers
for minister_name in minister_names:
    position = minister.analyze(user_input, context)
    minister_positions[minister_name] = position
```

### 3. Mode-Specific Aggregation

```python
# Get mode aggregation rules
mode_aggregation = self.mode_orchestrator.aggregate_for_mode(
    mode,
    minister_positions
)

# Determine recommendation based on mode
recommendation = self._determine_recommendation(
    mode, support_count, oppose_count, neutral_count, positions
)

# Example outputs:
# WAR mode:    "aggressive_proceed" or "defensive_hold_or_pivot"
# MEETING mode: "balanced_consensus_..." 
# DARBAR mode:  "red_line_blocks_recommendation"
```

### 4. Return Structure

All modes return a consistent dict:

```python
{
    "outcome": str,                    # Mode outcome type
    "recommendation": str,              # Action to take
    "mode": str,                        # Which mode was used
    "ministers_involved": List[str],    # Which ministers analyzed
    "minister_positions": Dict,         # Their stances
    "support_count": int,               # Quantitative metrics
    "oppose_count": int,
    "red_line_concerns": List[str],    # Doctrine violations
    "consensus_strength": float,        # 0-1, how strong agreement
}
```

## Integration into main.py

To use DynamicCouncil instead of CouncilAggregator:

### Step 1: Update Import

```python
# OLD:
from .council import CouncilAggregator

# NEW:
from .council import DynamicCouncil
```

### Step 2: Initialize

```python
# OLD:
council = CouncilAggregator(llm=llm)

# NEW:
dynamic_council = DynamicCouncil(llm=llm)
```

### Step 3: Set Mode

```python
# When user selects mode at startup
dynamic_council.set_mode(selected_mode)  # e.g., "meeting"
```

### Step 4: Call Dynamic Council

```python
# In _mca_decision function:

# OLD:
council_rec = council.convene(user_input, context)

# NEW:
council_rec = dynamic_council.convene_for_mode(
    mode=mode_orchestrator.get_current_mode(),
    user_input=user_input,
    context=context
)
```

### Step 5: Handle Results

```python
# Same as before, but now council composition varies by mode
if council_rec["outcome"] == "quick_mode_direct_response":
    # Skip council, use direct LLM
    return council_rec

minister_positions = council_rec["minister_positions"]
# ... rest of MCA logic
```

## Decision Flow with DynamicCouncil

```
User asks question
    ↓
System gets current mode from ModeOrchestrator
    ↓
DynamicCouncil.convene_for_mode(mode, input, context)
    ↓
    ├─ QUICK MODE?
    │  └─ Return direct_response → LLM handles directly
    │
    └─ Other modes?
       ├─ Get mode-specific ministers
       ├─ Invoke only those ministers
       ├─ Aggregate by mode rules
       ├─ Determine mode-specific recommendation
       └─ Return council result with mode metadata
    ↓
Prime Confident reviews (same as before)
    ↓
Response displayed
    ↓
Learning systems record episode (in all modes)
```

## Mode-Specific Behaviors

### QUICK MODE
- **Council Status**: ❌ SKIPPED
- **Return Value**: `outcome="quick_mode_direct_response"`
- **Recommendation**: `"use_direct_llm_response"`
- **Time Saving**: No council overhead, instant

### WAR MODE
- **Ministers**: risk, power, grand_strategist, technology, timing
- **Recommendation Logic**:
  - If red lines triggered: `"red_line_block_override_needed"`
  - If support ≥ oppose: `"aggressive_proceed"`
  - Otherwise: `"defensive_hold_or_pivot"`
- **Use**: Competitive advantage, fast decisions

### MEETING MODE
- **Ministers**: 3-5 domain-relevant (auto-selected)
- **Recommendation Logic**:
  - Strong support > oppose + neutral: `"strong_consensus_support"`
  - Strong oppose > support + neutral: `"strong_consensus_oppose"`
  - Otherwise: `"mixed_consensus_with_tradeoffs"`
- **Use**: Balanced wisdom, consensus-building

### DARBAR MODE
- **Ministers**: All 18
- **Recommendation Logic**:
  - Red lines triggered: `"red_line_blocks_recommendation"`
  - Consensus ≥ 80%: `"strong_doctrine_aligned_consensus"`
  - Consensus ≥ 60%: `"consensus_with_noted_dissent"`
  - Otherwise: `"deep_disagreement_defer_decision"`
- **Use**: Existential decisions, deep wisdom

## Example Usage

### Scenario: Career Decision in Different Modes

```python
# Initialize
dynamic_council = DynamicCouncil(llm=llm)
mode_orch = ModeOrchestrator()

user_input = "Should I accept the promotion?"

# TRY QUICK MODE
dynamic_council.set_mode("quick")
result_quick = dynamic_council.convene_for_mode("quick", user_input, {})
print(f"Quick: {result_quick['recommendation']}")  
# Output: "use_direct_llm_response"

# TRY MEETING MODE
dynamic_council.set_mode("meeting")
context = {"domains": ["career"]}
result_meeting = dynamic_council.convene_for_mode("meeting", user_input, context)
print(f"Meeting: {result_meeting['recommendation']}")  
# Output: "mixed_consensus_with_tradeoffs"
print(f"Ministers: {result_meeting['ministers_involved']}")
# Output: ['grand_strategist', 'psychology', 'timing', 'risk']

# TRY DARBAR MODE
dynamic_council.set_mode("darbar")
result_darbar = dynamic_council.convene_for_mode("darbar", user_input, context)
print(f"Darbar: {result_darbar['recommendation']}")  
# Output: "consensus_with_noted_dissent"
print(f"All {result_darbar['total_ministers_consulted']} ministers: {result_darbar['ministers_involved']}")
```

## Backwards Compatibility

The legacy `council.py` module remains unchanged. The new `DynamicCouncil` can coexist with existing code:

- Existing imports still work: `from .council import CouncilAggregator`
- New imports available: `from .council import DynamicCouncil`
- Package provides both paths

## Testing the Integration

### Unit Tests

```python
# Test QUICK mode returns early
dc = DynamicCouncil(llm=mock_llm)
result = dc.convene_for_mode("quick", "test", {})
assert result["outcome"] == "quick_mode_direct_response"
assert len(result["ministers_involved"]) == 0

# Test WAR mode has 5 ministers
result = dc.convene_for_mode("war", "test", {})
assert len(result["ministers_involved"]) == 5
assert "risk" in result["ministers_involved"]

# Test DARBAR mode has all ministers
result = dc.convene_for_mode("darbar", "test", {})
assert result["total_ministers_consulted"] == 18

# Test recommendation varies by mode
result_quick = dc.convene_for_mode("quick", "test", {})
result_war = dc.convene_for_mode("war", "test", {})
assert result_quick["recommendation"] != result_war["recommendation"]
```

### Integration Tests

1. **Mode Switching**: Set mode, convene council, verify minister list matches expected
2. **Recommendation Logic**: Test each mode's recommendation for same input
3. **Red Line Protection**: Verify red lines block recommendations in all modes
4. **Performance**: Time comparison between modes
5. **Learning**: Verify episodes captured regardless of mode

## Future Enhancements

1. **Mode Statistics**: Track success rate by mode
2. **Auto-Recommendation**: Suggest optimal mode for detected question type
3. **Mode Voting**: Compare recommendations from all modes
4. **Adaptive Modes**: Modes that adjust based on historical performance
5. **Custom Modes**: Let users define custom minister sets

## Configuration

No configuration needed - DynamicCouncil uses ModeOrchestrator's settings:

```python
# Get available modes
modes = dynamic_council.list_available_modes()  # ["quick", "war", "meeting", "darbar"]

# Get mode description
desc = dynamic_council.get_mode_description("war")
# Output: "Victory-focused (aggressive, Risk/Power/Strategy focus)"

# Get current mode
current = dynamic_council.get_current_mode()
```

## Troubleshooting

**Problem**: Import error for CouncilAggregator

**Solution**: Check that `persona/council.py` exists. The dynamic council loads it dynamically.

**Problem**: Ministers not being invoked in some mode

**Solution**: Check `ModeOrchestrator.get_ministers_for_mode(mode, context)` returns expected list.

**Problem**: Recommendation doesn't match mode expectation

**Solution**: Check mode detection with `dynamic_council.get_current_mode()` - ensure correct mode is set.

---

## Summary

**DynamicCouncil** provides:

✅ Seamless integration with ModeOrchestrator
✅ Mode-aware minister selection
✅ Mode-specific aggregation and recommendations
✅ Performance benefits (QUICK mode skips council)
✅ Backwards compatible with existing code
✅ Consistent return structure across modes
✅ Red line protection in all modes

**Ready to integrate into main.py** - see Step-by-Step Integration above.
