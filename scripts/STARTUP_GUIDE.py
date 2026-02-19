"""
===================================================================
🚀 ML-INTEGRATED CONVERSATION SYSTEM - COMPLETE STARTUP GUIDE
===================================================================

This is your complete LLM-to-LLM conversation system with integrated
machine learning for continuous improvement.

WHAT YOU HAVE:
  ✅ User LLM (deepseek-r1:8b) - generates authentic user problems
  ✅ Persona Prime (qwen3:14b) - provides wise guidance  
  ✅ Domain Detection - analyzes problems automatically
  ✅ Session Management - tracks conversation lifecycle
  ✅ Episodic Memory - stores experiences for learning
  ✅ ML Orchestration - analyzes patterns and improves
  ✅ Full Integration - all components working together

===================================================================
QUICK START (3 STEPS)
===================================================================

1. Ensure Ollama is running:
   
   ollama serve

2. Run the system:
   
   python ml_integrated_conversation.py

3. Watch it run:
   
   Session 1 → Dialogue with ML analysis → Session 2 improved → ...
   Press Ctrl+C to stop

===================================================================
WHAT HAPPENS DURING EXECUTION
===================================================================

Each Session:

  [Phase 1] Generate Problem
    • User LLM creates realistic problem
    • Example: "Should I change careers?"
  
  [Phase 2] Analyze Problem  
    • Domain detection: career, finance, health, etc.
    • Stakes: low/medium/high
    • Reversibility: reversible/partially/irreversible
  
  [Phase 3] Start Session Management
    • SessionManager tracks start time, problem, domains
    • Creates unique session ID
  
  [Phase 4] Run Dialogue
    TURN 1:
      Persona Prime: "Let me understand your situation..."
      User LLM: "Here's what's happening..."
      [Satisfaction check]
    
    TURN 2+:
      Persona Prime: "Can you tell me more about..."
      User LLM: "Yes, specifically..."
      [Satisfaction check]
    
    Until: User LLM is SATISFIED or max turns reached
  
  [Phase 5] Store & ML Analysis
    • Save conversation to JSON
    • Store episode in episodic memory
    • Record performance metrics
    • 🧠 ML analyzes outcomes
      ├─ Extract domain effectiveness
      ├─ Assess conversation quality
      ├─ Identify weak domains
      └─ Generate recommendations
  
  [Phase 6] Session Complete
    • Record satisfaction level
    • Print learning summary
    • Ready for next session

===================================================================
OUTPUT YOU'LL SEE
===================================================================

Session starts:

  ========================================================================
  SESSION 1 - ML-Integrated Conversation
  ========================================================================

  [Phase 1] Generating user problem...
  [PROBLEM]
  I've been offered a job promotion that requires relocating...

  [Phase 2] Analyzing problem for domains...
  Domains: career, lifestyle
  Stakes: high

  [Phase 3] Starting session management...
  [Phase 4] Running dialogue with ML integration...

    [TURN 1]
      [Persona Prime] Thinking...
      [Response] Understanding your situation. Let me ask...
      [User LLM] Reacting...
      [User] Yes, and my family is concerned about...
      [Evaluating] Satisfaction check...
      ⚠️ Partial satisfaction, continuing...

    [TURN 2]
      [Persona Prime] Thinking...
      ...continues...

After dialogue completes:

  ========================================================================
  ML LEARNING ANALYSIS
  ========================================================================

  [Metrics]
    • Turns: 3
    • Satisfied: YES  
    • Confidence: 87%
    • Domains: career, lifecycle

  [Analysis]
    • Conversation Depth: 6 exchanges
    • Satisfaction Indicator: high
    • Pattern: Quick resolution (efficient)

  Learning persisted to:
    → data/memory/episodes.jsonl
    → data/memory/metrics.jsonl

  [Status] Session 1 complete. Starting session 2...


After all sessions (press Ctrl+C):

  ========================================================================
  SESSIONS COMPLETE
  ========================================================================

  Total sessions: 5
  Total turns: 23
  Avg turns/session: 4.6
  Learning records: 5
  Satisfied sessions: 4/5 (80%)

  [Data Stored]
    • Conversations: data/conversations/
    • Episodes: data/memory/episodes.jsonl
    • Metrics: data/memory/metrics.jsonl
    • Sessions: data/sessions/

===================================================================
HOW ML LEARNING IMPROVES THE SYSTEM
===================================================================

Session 1 (Career):
  Problem: "Should I change jobs?"
  Result: SATISFIED in 3 turns, 87% confidence
  Learning: "Career domain responds well to structured questions"

Session 2 (Psychology):
  Problem: "How do I handle family conflict?"
  Result: UNSATISFIED after 5 turns, 65% confidence
  Learning: "Psychology is complex - needs different approach"
  Flagged: Weak domain

Session 3 (Career again):
  Problem: "Should I freelance or stay employed?"
  ML Access: "We know this domain works well"
  Applied: Same successful pattern from Session 1
  Result: SATISFIED in 3 turns, 88% confidence
  Improvement: ✅ System used learned pattern

Session 4 (Psychology again):
  Problem: "Should I set boundaries with family?"
  ML Access: "This domain is weak - use different approach"
  Tried: Extended dialogue + extra perspective
  Result: PARTIAL SATISFIED in 4 turns, 72% confidence
  Improvement: ✅ Used different approach, got improvement

PATTERN: Sessions 3+ improve because system learns from 1-2


===================================================================
SYSTEM ARCHITECTURE
===================================================================

User Problem Generation
        ↓
Domain Analysis (15 domains detected)
        ↓
Session Initialization
        ├─ Problem statement
        ├─ Detected domains
        ├─ Stakes level
        └─ Reversibility
        ↓
Conversation Loop
  ├─ Persona Prime asks clarifying questions
  ├─ User LLM provides authentic responses
  ├─ Satisfaction check after each turn
  └─ Repeat until satisfied or max turns
        ↓
Episode Storage (Episodic Memory)
        ├─ User input
        ├─ Recommendation
        ├─ Confidence level
        ├─ Outcome
        └─ Regret score
        ↓
Metrics Recording (Performance Metrics)
        ├─ Turns needed
        ├─ Domain
        ├─ Confidence
        ├─ Outcome
        └─ Success indicator
        ↓
ML Analysis Pipeline
        ├─ Extract metrics
        ├─ Analyze domain effectiveness
        ├─ Assess conversation quality
        ├─ Identify weak domains (system-wide)
        └─ Generate recommendations for next session
        ↓
Learning Insights Saved
        ├─ learning-insights.jsonl (cumulative)
        └─ weak-domains.json (summary)
        ↓
Next Session Uses Learned Patterns → System Improves


===================================================================
DATA STORAGE LOCATIONS
===================================================================

Generated during execution:

  data/conversations/
    └─ uc_<timestamp>_s<num>.json
       Full conversation transcripts with dialogue

  data/sessions/
    ├─ completed/
    │   └─ session_<id>.json
    │       Session metadata, problem, domains
    └─ consequences.jsonl
        Follow-up outcomes, learning integration

  data/memory/
    ├─ episodes.jsonl
    │   Episode objects: decisions, outcomes, consequences
    └─ metrics.jsonl
        Performance metrics: turns, confidence, success rates

  ml/cache/
    ├─ outcomes/
    │   Outcome recording and analysis
    └─ training_datasets/
        ML training data extracted from conversations


===================================================================
KEY FEATURES
===================================================================

✅ Automatic Domain Detection
   15 domains: career, finance, health, relationships, psychology,
   education, legal, ethical, technical, creative, family, personal,
   spiritual, community, lifestyle

✅ Intelligent Conversation Flow
   • Clarifying questions in turn 1
   • Context-aware responses in turns 2+
   • Satisfaction checks after each turn
   • Optional final synthesis

✅ Multi-LLM Orchestration
   • User LLM: Generates authentic human responses
   • Persona Prime: Provides wise, consistent guidance
   • Independent reasoning, collaborative outcomes

✅ Episodic Learning System
   • Every conversation stored as episode
   • Decisions tracked with outcomes
   • Consequences recorded over time
   • Used for pattern extraction and improvement

✅ Performance Metrics
   • Success rate per domain
   • Average turns needed
   • Confidence levels achieved
   • Weak domain identification

✅ ML Wisdom Integration
   • Pattern analysis from conversations
   • Domain effectiveness tracking
   • Recommendation quality assessment
   • System-wide weak domain detection


===================================================================
TROUBLESHOOTING
===================================================================

ISSUE: "Ollama not reachable"
SOLUTION: 
  Start Ollama: ollama serve
  Models needed: deepseek-r1:8b, qwen3:14b
  Check: ollama list

ISSUE: "Module not found"
SOLUTION:
  Check all imports work: python quick_test_ml.py
  Ensure persona/ and ml/ folders exist
  Verify __init__.py files present

ISSUE: "Session manager error"
SOLUTION:
  Create directories: mkdir -p data/sessions data/memory
  Check file permissions
  Verify session_manager.py accessible

ISSUE: "ML analysis fails"
SOLUTION:
  Check ml/cache/ exists
  Verify episodic_memory.py working
  Run quick_test_ml.py to diagnose


===================================================================
NEXT STEPS
===================================================================

1. START THE SYSTEM
   
   python ml_integrated_conversation.py

2. MONITOR LEARNING
   
   Watch learning summaries after each conversation
   Look for weak domain patterns

3. ANALYZE DATA
   
   # View weak domains
   cat data/learning_insights/weak-domains.json
   
   # View episodes
   tail -5 data/memory/episodes.jsonl
   
   # View metrics
   tail -5 data/memory/metrics.jsonl

4. OBSERVE IMPROVEMENT
   
   Sessions 1-2: Establish baselines
   Sessions 3-5: See improvement as patterns emerge
   Sessions 5+: System increasingly effective


===================================================================
VERIFICATION
===================================================================

Quick test (before running full system):

  python quick_test_ml.py

Shows:
  ✅ All imports working
  ✅ System initializes
  ✅ Components verified
  ✅ Ready to use


===================================================================
STATUS: READY TO USE ✅
===================================================================

All components integrated and verified.

Run: python ml_integrated_conversation.py

Watch the system learn and improve through conversation!

===================================================================
"""

if __name__ == "__main__":
    print(__doc__)
