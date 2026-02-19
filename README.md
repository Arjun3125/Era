# ERA - Excellent Reasoning Architecture

**A sovereign decision governance system with ministerial councils, ML wisdom, and interactive dialogue engines.**

---

## 🚀 Quick Start

### Installation (5 minutes)

```bash
# 1. Clone or navigate to ERA directory
cd c:\era

# 2. (Optional) Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Ollama (separate terminal)
ollama serve

# 5. Pull LLM models (one-time)
ollama pull deepseek-r1:8b
ollama pull qwen3:14b
```

### Run ERA (Choose Your Path)

**Path 1: LLM Dialogue Engine** (Easiest - 30 seconds)
```bash
python llm_conversation.py --mode demo --rounds 1
```

**Path 2: Decision Guidance System** (10-20 minutes)
```bash
python system_main.py
```

**Path 3: Multi-Session Problem Solving** (Variable)
```bash
python run_session_conversation.py
```

**Path 4: Ministerial Council Simulation** (Variable)
```bash
python sovereign_main.py
```

---

## 📚 What is ERA?

ERA is a **Ministerial Cognitive Architecture (MCA)** that combines:

| Component | Purpose |
|-----------|---------|
| **Mode Orchestrator** | Routes decisions through 4 complexity levels (QUICK → MEETING → WAR → DARBAR) |
| **19 Ministers** | Domain-bounded advisors giving perspectives (Risk, Data, Diplomacy, etc.) |
| **KIS Engine** | Knowledge Integration System scoring knowledge across 5 factors |
| **ML Wisdom** | Learns from episodes to improve future decisions |
| **LLM Integration** | Direct dialogue with deepseek-r1:8b and qwen3:14b models |
| **Session Management** | Multi-turn problem solving with automatic escalation |

---

## 🎯 Core Features

### ✅ 1. LLM Conversation Engine
- Interactive (choose any topic)
- Demo mode (pre-built conversations)
- Topic mode (specify custom topics)
- Full persistence (JSON transcripts)

### ✅ 2. Decision Guidance System  
- 9-phase dialogue pipeline
- Auto-domain detection (15 domains)
- 3 rounds of clarifying questions
- Council of relevant ministers
- Prime Confident final decision authority
- User feedback loop
- Satisfaction assessment

### ✅ 3. Session-Based Problem Solving
- Multi-session continuity
- Auto-mode escalation (QUICK → DARBAR)
- Consequence tracking
- Related session discovery
- Session statistics

### ✅ 4. Ministerial Council
- 19 domain specialists
- Mode-specific voting (QUICK/MEETING/WAR/DARBAR)
- KIS-driven recommendations
- Judge observing outcomes

### ✅ 5. Machine Learning Wisdom
- Judgment priors from past decisions
- Feature extraction from decision state
- KIS scoring (5-factor: domain × type × memory × context × goal)
- Episodic memory persistence

### ✅ 6. System Simulation
- Synthetic human generation
- Multi-agent scenarios
- Crisis simulation
- Population dynamics

---

## 📁 Project Structure

```
C:\era\
├── llm_conversation.py           # LLM dialogue engine
├── system_main.py                # Decision guidance system  
├── run_session_conversation.py    # Session-based problem solving
├── sovereign_main.py              # Ministerial council simulation
├── requirements.txt               # Python dependencies
├── START_HERE.md                  # Installation guide
├── README.md                      # This file
├── CHANGELOG.md                   # Version history
├── DEPENDENCIES.md                # System requirements
│
├── persona/                       # Interactive persona system
│   ├── main.py
│   ├── modes/                     # Mode orchestration
│   ├── ministers/                 # Individual minister implementations
│   ├── knowledge_engine.py        # KIS (Knowledge Integration System)
│   ├── domain_detector.py         # Auto-detect problem domains
│   ├── session_manager.py         # Session lifecycle management
│   ├── cache_manager.py           # Automatic cache cleanup
│   └── ... (15+ submodules)
│
├── sovereign/                     # Ministerial council system
│   ├── ministers/                 # 19 domain specialists
│   ├── dynamic_council.py         # Council selection logic
│   ├── prime_confident.py         # Decision authority
│   └── minister_factory.py        # Minister instantiation
│
├── ml/                            # Machine learning wisdom layer
│   ├── llm_handshakes/            # LLM interface (structured calls)
│   ├── kis/                       # Knowledge Integration System
│   ├── judgment_priors.py         # ML judgment learning
│   ├── ml_orchestrator.py         # ML pipeline
│   └── ... (learning components)
│
├── hse/                           # Human Simulation Engine
│   ├── population_manager.py      # Synthetic human generation
│   ├── human_profile.py           # Individual profiles
│   ├── crisis_injector.py         # Stress/crisis scenarios
│   └── analytics_server.py        # Performance tracking
│
├── ingestion/                     # Knowledge ingestion pipeline
│   ├── v2/                        # Async ingestion pipeline
│   │   └── run_all_v2_ingest.py   # Process PDFs to embeddings
│   └── ... (v1 legacy)
│
├── data/                          # All data storage
│   ├── doctrine/                  # Minister decision rules (YAML)
│   ├── books/                     # Ingested knowledge (61 PDFs)
│   ├── sessions/                  # Session records
│   ├── conversations/             # LLM dialogue transcripts
│   ├── memory/                    # Episodic learning storage
│   └── ... (RAG, memory, etc.)
│
├── tests/                         # Test suite (27 test files)
├── documentation/                 # 50+ comprehensive guides
├── archive/                       # Deprecated modules
│   ├── integrations_old/          # (Archived: unused)
│   └── runtime_old/               # (Archived: experimental)
└── logs/                          # Runtime logs
```

---

## 🔧 Configuration

### Environment Variables (.env)

Create `.env` file in `C:\era\`:

```env
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_USER=deepseek-r1:8b
OLLAMA_MODEL_PROGRAM=qwen3:14b
OLLAMA_TIMEOUT=300

# System Paths
ERA_ROOT=c:\era
DATA_ROOT=c:\era\data

# Logging
LOG_LEVEL=INFO

# ML Configuration
ML_BATCH_SIZE=32
ML_LEARNING_RATE=0.001
```

See `.env.example` for all options.

---

## 📖 Documentation

### Getting Started
- **[START_HERE.md](START_HERE.md)** - Installation & quick start (5 min)
- **[DEPENDENCIES.md](DEPENDENCIES.md)** - System requirements (2 min)

### Understanding the System
- **[SYSTEM_ARCHITECTURE.md](documentation/SYSTEM_ARCHITECTURE.md)** - Full architecture (20 min)
- **[MODE_SELECTION_GUIDE.md](documentation/MODE_SELECTION_GUIDE.md)** - When to use which mode (5 min)
- **[SESSION_FEATURES_GUIDE.md](documentation/SESSION_FEATURES_GUIDE.md)** - Multi-session workflows (10 min)

### Reference
- **[CHANGELOG.md](CHANGELOG.md)** - Version history
- **[DEAD_ENDS_RESOLUTION.md](DEAD_ENDS_RESOLUTION.md)** - Cleanup decisions
- **[documentation/](documentation/)** - 50+ comprehensive guides

---

## 🎓 Learning Paths

### For New Users (30 minutes)
1. Read [START_HERE.md](START_HERE.md)
2. Install dependencies
3. Run: `python llm_conversation.py --mode demo --rounds 1`

### For Decision Makers (1-2 hours)
1. Read [MODE_SELECTION_GUIDE.md](documentation/MODE_SELECTION_GUIDE.md)
2. Run: `python system_main.py`
3. Try different scenarios

### For Developers (2-4 hours)
1. Read [SYSTEM_ARCHITECTURE.md](documentation/SYSTEM_ARCHITECTURE.md)
2. Study `persona/`, `sovereign/`, `ml/` modules
3. Review test suite in `tests/`

### For System Administrators
1. Check [DEPENDENCIES.md](DEPENDENCIES.md)
2. Run: `python persona/cache_manager.py`
3. Monitor logs in `logs/`

---

## 🚀 Common Workflows

### Workflow 1: Quick LLM Dialogue
```bash
python llm_conversation.py --mode demo --rounds 2
```
⏱️ **Time:** 1-2 minutes | 💬 **Output:** Conversation transcript

### Workflow 2: Get Decision Guidance
```bash
python system_main.py
```
⏱️ **Time:** 10-20 minutes | 📋 **Output:** 9-phase guidance with council input

### Workflow 3: Multi-Session Problem Solving
```bash
python run_session_conversation.py
```
⏱️ **Time:** Variable | 🔄 **Output:** Multiple sessions with continuity

### Workflow 4: Run Ministerial Simulation
```bash
python sovereign_main.py
```
⏱️ **Time:** Variable | 🎭 **Output:** Full council voting & outcomes

### Workflow 5: Cleanup Cache
```bash
python persona/cache_manager.py
```
⏱️ **Time:** 1 second | 🧹 **Output:** Cache report & cleanup

---

## ⚙️ System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 4 GB | 8+ GB |
| **Disk** | 5 GB | 10+ GB |
| **Python** | 3.10 | 3.12+ |
| **Ollama** | Latest | Latest |

---

## 🧠 Decision Modes

| Mode | Use Case | Ministers | Speed |
|------|----------|-----------|-------|
| **QUICK** | Mentoring, direct advice | None (LLM only) | Fast |
| **MEETING** | Balanced perspective | 3-5 relevant | Medium |
| **WAR** | Victory-focused strategy | 5 specific | Medium |
| **DARBAR** | Full wisdom council | All 19 | Slow |

Auto-escalates: QUICK (1-2) → MEETING (3-5) → WAR (6-8) → DARBAR (9+)

---

## 🛠️ Troubleshooting

### "Ollama not running"
```bash
ollama serve  # In separate terminal
```

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Connection refused"
```bash
# Check Ollama is running on port 11434
netstat -ano | findstr :11434
```

### Cache taking too much space
```bash
python persona/cache_manager.py
```

See [DEPENDENCIES.md](DEPENDENCIES.md) for more troubleshooting.

---

## 📊 System Status

**Last Updated:** February 19, 2026  
**Version:** 1.2.0  
**Status:** ✅ OPERATIONAL

All systems verified and tested:
- ✅ LLM integration (deepseek-r1:8b + qwen3:14b)
- ✅ Decision guidance (9-phase pipeline)
- ✅ Ministerial councils (19 ministers)
- ✅ ML learning (judgment priors)
- ✅ Session management (multi-turn)
- ✅ Cache cleanup (automatic)
- ✅ Documentation (50+ guides)

---

## 🤝 Contributing

### Reporting Issues
Use [DEAD_ENDS_RESOLUTION.md](DEAD_ENDS_RESOLUTION.md) format for cleanup issues.

### Code Changes
1. Create feature branch
2. Update relevant tests
3. Run: `pytest tests/ -v`
4. Update documentation

---

## 📜 License & Attribution

**Creator:** Alfred (Stabilizing Intelligence)  
**Project Motto:** "Power that costs identity is rejected."  
**License:** Internal use (Detailed terms in LICENSE if applicable)

---

## 🔗 Quick Links

| What | Where |
|------|-------|
| Installation | [START_HERE.md](START_HERE.md) |
| Architecture | [documentation/SYSTEM_ARCHITECTURE.md](documentation/SYSTEM_ARCHITECTURE.md) |
| Mode Guide | [documentation/MODE_SELECTION_GUIDE.md](documentation/MODE_SELECTION_GUIDE.md) |
| Sessions | [documentation/SESSION_FEATURES_GUIDE.md](documentation/SESSION_FEATURES_GUIDE.md) |
| Requirements | [DEPENDENCIES.md](DEPENDENCIES.md) |
| Changes | [CHANGELOG.md](CHANGELOG.md) |
| Cleanup | [DEAD_ENDS_RESOLUTION.md](DEAD_ENDS_RESOLUTION.md) |

---

**Status:** ✅ Ready to Use  
**Next Step:** Read [START_HERE.md](START_HERE.md)  
**Questions?** Check [documentation/](documentation/) folder (50+ guides)
