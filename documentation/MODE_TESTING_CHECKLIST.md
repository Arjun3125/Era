# Mode System Testing & Validation Checklist

## Pre-Launch Verification

### Code Quality
- [x] `persona/modes/mode_orchestrator.py` - No syntax errors
- [x] `persona/modes/__init__.py` - Proper module exports
- [x] `persona/main.py` - Integration complete, no errors
- [x] All imports resolvable
- [x] ModeOrchestrator instantiation works
- [x] Mode switching logic present
- [x] MCA decision function updated

### Documentation
- [x] `MODE_SELECTION_GUIDE.md` - Complete (450+ lines)
- [x] `MODE_QUICK_REFERENCE.md` - Quick lookup ready
- [x] `INTEGRATION_SUMMARY.md` - Integration docs
- [x] `MODE_EXAMPLES.md` - Worked examples provided
- [x] Examples show each mode's unique perspective
- [x] Usage scenarios documented

## Startup Testing

### Test 1: Mode Selection Menu
**Steps:**
1. Run: `python -m persona.main`
2. Verify menu displays:
   - [ ] "PERSONA N - DECISION MODE SELECTION"
   - [ ] All 4 options visible: [1] QUICK, [2] WAR, [3] MEETING, [4] DARBAR
   - [ ] Default option indicated ([3] MEETING)
   - [ ] Input prompt clear

**Expected Result**: Menu displays properly, accepts numeric input [1-4]

---

### Test 2: Default Mode Selection
**Steps:**
1. Display shows selection menu
2. Press Enter (no input) to accept default
3. Verify system enters MEETING mode

**Expected Result**: 
- Confirmation message: "Mode: MEETING - (description)"
- Main loop starts
- System ready for input

---

### Test 3: Mode 1 - Quick Mode
**Steps:**
1. Select [1] at startup
2. Verify confirmation: "Mode: QUICK - 1:1 mentoring..."
3. Enter a test question: "What should I do about my career?"

**Expected Result**:
- Response is personal, exploratory, warm
- No council members listed in output
- Fast response
- Response labeled "[QUICK]"

**Optional**: Confirm that `_mca_decision()` returns early with `"decision": "direct_response"`

---

### Test 4: Mode 2 - War Mode
**Steps:**
1. Select [2] at startup
2. Verify confirmation: "Mode: WAR - Victory-focused..."
3. Verify ministers listed: Risk, Power, Grand Strategist, Technology, Timing
4. Enter test question: "Competitor undercut our prices. How do we fight back?"

**Expected Result**:
- Council convenes with 5 ministers
- Response is aggressive but smart
- Winning strategy emphasized
- Response labeled "[WAR]"
- Risk concerns still present (red lines protected)

---

### Test 5: Mode 3 - Meeting Mode (Default)
**Steps:**
1. Select [3] at startup (or just press Enter)
2. Verify confirmation: "Mode: MEETING - Balanced debate..."
3. Enter test question: "Should I accept the promotion?"

**Expected Result**:
- Council convenes with 3-5 relevant ministers
- Multiple perspectives shown
- Disagreements/consensus noted
- Balanced synthesis provided
- Response labeled "[MEETING]"

---

### Test 6: Mode 4 - Darbar Mode
**Steps:**
1. Select [4] at startup
2. Verify confirmation: "Mode: DARBAR - Full council wisdom..."
3. Verify ministers listed: All 18 ministers shown
4. Enter test question: "Is this the right ethical choice?"

**Expected Result**:
- Council convenes with all 18 ministers
- Red lines explicitly checked
- Deep, nuanced perspectives
- Full doctrine compliance shown
- Response labeled "[DARBAR]"
- Longest, most thorough response

---

## Mid-Conversation Testing

### Test 7: Mode Switching - Quick → War
**Steps:**
1. Start in QUICK mode (select [1])
2. Ask a question: "What's a good business strategy?"
3. Get Quick mode response
4. Type: `/mode war`
5. Verify confirmation shows
6. Ask same question again

**Expected Result**:
- Confirmation: "[MODE] Switched to WAR"
- Ministers listed: risk, power, grand_strategist, technology, timing
- Same question produces aggressive/winning-focused response
- Dramatically different tone from Quick mode

---

### Test 8: Mode Switching - War → Darbar
**Steps:**
1. Currently in WAR mode (from previous test)
2. Type: `/mode darbar`
3. Verify confirmation shows all 18 ministers

**Expected Result**:
- Confirmation: "[MODE] Switched to DARBAR"
- All 18 ministers listed
- System ready with deepest analysis mode

---

### Test 9: Mode Switching - Invalid Mode
**Steps:**
1. Type: `/mode invalid`
2. Verify system handles gracefully

**Expected Result**:
- Error message: "[MODE ERROR] Unknown mode 'invalid'. Available: quick, war, meeting, darbar"
- System continues (no crash)
- User can continue or try valid mode

---

### Test 10: Mode Help/Info
**Steps:**
1. Type: `/mode`  (without argument)
2. Or type: `/help` or `?`

**Expected Behavior** (if implemented):
- Should show available modes or brief help
- Or gracefully handle as unknown command

---

## Learning System Integration

### Test 11: Episode Recording (All Modes)
**Steps:**
1. Use QUICK mode - ask a decision question
2. Get response
3. Switch to `/mode war` - ask similar question
4. Check `data/memory/episodes.jsonl`

**Expected Result**:
- File contains JSON entries for both turns
- Each episode has: turn_id, domain, user_input, persona_recommendation, confidence, mode_used (if tracked)
- Both episodes recorded regardless of mode

---

### Test 12: Metrics Recording (All Modes)
**Steps:**
1. Use multiple modes for 10+ turns
2. Check `data/memory/metrics.jsonl`

**Expected Result**:
- Metrics recorded for each decision
- Metrics include: turn, domain, confidence, outcome (if synthetic)
- No skipping based on mode

---

### Test 13: Pattern Extraction (All Modes)
**Steps:**
1. Run system for 100+ turns (or use automated simulation)
2. At turn 100, check output for pattern extraction results
3. Check `data/memory/patterns.json` created/updated

**Expected Result**:
- At 100-turn mark: Pattern extraction triggers
- Learning signals displayed
- Weak domains identified
- Patterns file JSON created
- Works regardless of modes used

---

## Performance Tests

### Test 14: Response Time by Mode
**Steps:**
1. Time a response in QUICK mode
2. Time same question in WAR mode
3. Time same question in MEETING mode
4. Time same question in DARBAR mode

**Expected Results** (approximately):
- QUICK: < 2 seconds
- WAR: 3-5 seconds
- MEETING: 5-8 seconds
- DARBAR: 10-15 seconds

(Times vary based on LLM performance and network conditions)

---

### Test 15: Council Invocation
**Steps:**
1. Enable PERSONA_DEBUG=1 to see traces
2. Run in each mode
3. Check trace output for "mca_mode_routing"

**Expected Result**: Traces show:
- QUICK: `should_convene: false`
- WAR: `should_convene: true, ministers: [...]`
- MEETING: `should_convene: true, ministers: [3-5]`
- DARBAR: `should_convene: true, ministers: [18]`

---

## Edge Cases

### Test 16: Mode Persistence Through Turns
**Steps:**
1. Start in QUICK mode
2. Ask 5 questions
3. All should be in QUICK mode
4. Switch to `/mode darbar`
5. Ask 3 questions
6. Switch to `/mode meeting`
7. Ask 2 questions

**Expected Result**:
- Mode persists until switched
- Each turn uses correct mode
- No accidental reverts

---

### Test 17: Mode with Automated Simulation
**Steps:**
1. Start with `AUTOMATED_SIMULATION=1` 
2. System runs 100 turns automatically
3. Check that modes work with synthetic humans

**Expected Result**:
- Synthetic human integration works with all modes
- Episodes recorded for each mode
- Patterns extracted across all modes
- Learning signals generated

---

### Test 18: Concurrent Mode Operations
**Steps:**
1. Not applicable for single-threaded conversation
2. (Skip this test for CLI version)

---

## Regression Testing

### Test 19: Existing Features Still Work
**Steps:**
1. Verify episodic memory initialization works
2. Verify learning systems still active
3. Verify identity validator still runs
4. Verify pattern extraction still triggers at 100 turns
5. Verify MCA decision logic still functions

**Expected Result**:
- All existing learning systems work
- Mode system doesn't break existing architecture
- Learning still accumulates

---

### Test 20: Help/Documentation Commands
**Steps:**
1. Type: `help`
2. Type: `?`
3. Type: `/help`
4. Type: `/modes`

**Expected Result** (if implemented):
- Shows available commands
- Mode selection documented
- Learning system explained
- Example usage provided

---

## Integration Summary Tests

### Test 21: Full 100-Turn Cycle
**Steps:**
1. Run system for 100 turns
2. Use multiple modes throughout
3. At turn 100: Check metrics report
4. Verify pattern extraction runs
5. Verify learning signals displayed

**Expected Result**:
- All systems working end-to-end
- Metrics shown at turn 100
- Patterns extracted across all modes
- Learning signals useful

---

### Test 22: Mode Effectiveness Tracking
**Steps:**
1. Run 50 turns in QUICK mode
2. Run 50 turns in WAR mode  
3. Run 50 turns in MEETING mode
4. Check if learning signals distinguish mode effectiveness

**Future Feature**: Metrics could show success rate by mode
- "QUICK mode: 45% success rate"
- "WAR mode: 52% success rate"
- "MEETING mode: 68% success rate"

---

## Documentation Validation

### Test 23: Mode Examples Match Reality
**Steps:**
1. Read MODE_EXAMPLES.md
2. Test each example scenario with real system
3. Verify system produces similar quality/tone

**Expected Result**:
- Examples are representative
- System produces equivalent guidance
- Examples accurately show mode differences

---

### Test 24: Quick Reference Accuracy
**Steps:**
1. Check MODE_QUICK_REFERENCE.md
2. Verify all information matches implementation
3. Verify command formats work
4. Verify minister lists match code

**Expected Result**:
- All information accurate
- All commands functional
- No out-of-date descriptions

---

## Final Acceptance Tests

### Test 25: Complete User Journey
**Steps:**
1. Fresh start: `python -m persona.main`
2. See selection menu
3. Select mode (try each one)
4. Ask 5 questions in first mode
5. Switch modes 2-3 times with `/mode` command
6. Use 20+ turns total
7. Exit gracefully with `exit`

**Expected Result**: 
- ✅ System works end-to-end
- ✅ Mode selection works
- ✅ Mode switching works
- ✅ All modes produce distinctive advice
- ✅ Learning systems work in background
- ✅ No errors or crashes
- ✅ User experience is smooth

---

## Sign-Off Criteria

✅ **Pass this test to confirm Mode System is Ready**:

1. Mode selection menu displays properly
2. All 4 modes can be selected at startup
3. All 4 modes can be switched to with `/mode` command
4. Each mode produces distinctly different advice
5. QUICK mode doesn't invoke council
6. WAR/MEETING/DARBAR modes invoke correct number of ministers
7. Learning systems (episodes, metrics, patterns) work in all modes
8. No crashes or error messages (except clear error handling)
9. Documentation is accurate and helpful
10. Complete 100-turn cycle works properly

**STATUS**: Ready to commit to production when all tests pass.

---

## Test Results Log

```
Test #  | Name                          | Status | Notes
--------|-------------------------------|--------|------------------
1       | Mode Selection Menu           | [ ]    |
2       | Default Mode Selection         | [ ]    |
3       | Mode 1 - Quick Mode            | [ ]    |
4       | Mode 2 - War Mode              | [ ]    |
5       | Mode 3 - Meeting Mode          | [ ]    |
6       | Mode 4 - Darbar Mode           | [ ]    |
7       | Mode Switching Quick→War       | [ ]    |
8       | Mode Switching War→Darbar      | [ ]    |
9       | Invalid Mode Handling          | [ ]    |
10      | Mode Help/Info                 | [ ]    |
11      | Episode Recording All Modes    | [ ]    |
12      | Metrics Recording All Modes    | [ ]    |
13      | Pattern Extraction All Modes   | [ ]    |
14      | Response Time by Mode          | [ ]    |
15      | Council Invocation Traces      | [ ]    |
16      | Mode Persistence Turns         | [ ]    |
17      | Mode with Automation           | [ ]    |
19      | Existing Features Still Work   | [ ]    |
20      | Help/Documentation Commands    | [ ]    |
21      | Full 100-Turn Cycle            | [ ]    |
22      | Mode Effectiveness Tracking    | [ ]    |
23      | Mode Examples Match Reality    | [ ]    |
24      | Quick Reference Accuracy       | [ ]    |
25      | Complete User Journey          | [ ]    |
```

---

## Known Limitations / Future Work

1. **Mode Learning**: Currently all modes share learning. Future: track per-mode success
2. **Mode Recommendation**: Manual selection only. Future: auto-recommend mode
3. **Mode History**: No history of which modes were used. Future: track mode choices
4. **Mode Comparison**: Can't compare modes side-by-side
5. **Mode Hooks**: No pre/post hooks for custom mode behavior

---

**Next Step**: Run tests and fill in Status column above.
