# ERA System - Changelog

All notable changes to the ERA (Excellent Reasoning Architecture) project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Under Development
- API reference documentation (Sphinx)
- Advanced cache management with automatic cleanup
- Full async/await pipeline error recovery testing
- Consolidated learning system (persona/learning vs ml/ merger)
- RAG storage unification (single canonical location)

---

## [1.2.0] - February 19, 2026

### Added
- ✅ **LLM Conversation Engine** (`llm_conversation.py`)
  - Interactive mode: Choose any topic for LLM dialogue
  - Demo mode: Pre-built conversation on intelligent decision systems
  - Topic mode: Specify custom topics
  - Conversation persistence (JSON format)
  - Full dialogue history with speaker labels

- ✅ **Session-Based Problem Solving** (`run_session_conversation.py`)
  - Multi-turn problem solving with auto-mode escalation
  - Domain auto-detection (15 domains, stakes/reversibility)
  - Session persistence with consequence tracking
  - Session continuity & related session discovery
  - Satisfaction assessment after each session

- ✅ **Comprehensive Documentation**
  - START_HERE.md - Quick start guide with 4 core workflows
  - CHANGELOG.md - This file, version history
  - SESSION_FEATURES_GUIDE.md - Multi-session architecture
  - MODE_QUICK_REFERENCE.md - Mode selection decision tree
  - 50+ markdown files in documentation/ folder

- ✅ **Quality Assurance**
  - Audit report generated with 12 critical issues identified
  - Path validation for data directories
  - Data integrity checks on startup
  - HSE module verification (confirmed working)
  - Doctrine YAML validation (10+ files confirmed)

### Changed
- Unified messaging around decision guidance system
- Enhanced 9-phase dialogue pipeline in system_main.py
- Refined ministerial council integration
- All documentation moved to centralized documentation/ folder
- Updated personality drift detection for persona evolution

### Fixed
- LLM Conversation script syntax issues (imports, parameters)
- Unicode encoding issues for Windows console compatibility
- OllamaRuntime parameter mismatch (model → speak_model/analyze_model)
- Import paths (llm.ollama_runtime → persona.ollama_runtime)
- Session manager initialization and persistence

### Verified Working
- ✅ HSE module (Human Simulation Engine) imports successfully
- ✅ Doctrine YAML files exist in data/doctrine/locked/ (10+ confirmed)
- ✅ Data/books directory (61 items, properly configured)
- ✅ LLM interface implementation (call_llm method fully implemented)
- ✅ 1-round demo: ~30 seconds execution
- ✅ 3-round demo: ~3-5 minutes execution
- ✅ Conversation file persistence (21.6 KB+ files confirmed)

---

## [1.1.0] - February 18, 2026

### Added
- **Ministerial Council System**
  - 19 domain-bounded ministers with voting
  - Mode-specific voting rules (QUICK/MEETING/WAR/DARBAR)
  - Intelligence minister with priority access
  - Judge (Tribunal) observing consequences

- **Knowledge Integration System (KIS)**
  - 5-factor scoring algorithm
  - 40K+ doctrine items across 19 domains
  - Domain confidence assessment
  - Type-weighted knowledge ranking

- **ML Wisdom Layer**
  - Feature extraction from decisions
  - ML judgment priors learning
  - Outcome-based training labels
  - Episodic memory integration

- **Mode Orchestration**
  - QUICK mode: Direct LLM, no council (turns 1-2)
  - MEETING mode: 3-5 ministers, balanced (turns 3-5)
  - WAR mode: 5 ministers, victory-focused (turns 6-8)
  - DARBAR mode: All 19 ministers (turns 9+)

### Changed
- Personality drift detection refined
- Session state management improved
- Episode storage format standardized
- Minister domain assignments clarified

### Removed
- Deprecated single-turn decision API
- Legacy persona session format

---

## [1.0.0] - February 10, 2026

### Added
- **Initial Release: Decision Guidance System**
  - 9-phase dialogue pipeline
  - Domain detection (15 domains)
  - Session manager with persistence
  - Prime Confident decision authority
  - User LLM feedback loop
  - Satisfaction assessment
  - Episodic memory storage
  - ML analysis pipeline

- **Persona System**
  - Interactive conversation
  - Mode awareness (QUICK/MEETING/WAR/DARBAR)
  - Doctrine-driven decision-making
  - Personality evolution tracking

- **Ingestion Pipeline (v2)**
  - Async document processing
  - Embedding generation (parallel)
  - Vector DB integration
  - RAG knowledge storage

- **Test Suite**
  - 27 test files
  - Unit tests for core systems
  - Integration tests
  - ML layer validation

- **Documentation**
  - SYSTEM_ARCHITECTURE.md
  - MODE_SELECTION_GUIDE.md
  - MODE_ORCHESTRATOR_GUIDE.md
  - HYBRID_MEMORY_ARCHITECTURE.md
  - 40+ additional guides

### Known Limitations (Version 1.0)
- Async pipeline error recovery not fully tested
- Cache management not automated
- RAG storage has two possible locations
- Some modules not fully documented (runtime/, multi_agent_sim/)

---

## [0.9.0] - January 2026

### Initial Development
- Core decision engine
- Basic minister implementation
- KIS prototype
- Session management skeleton
- Documentation framework

---

## Deprecated & Planned Removal

### Will Be Removed in v2.0.0
- Legacy persona session format (migrate to SessionManager)
- Single-turn decision API (use system_main.py instead)
- Old ingestion v1 pipeline (use v2 only)

### Modules Under Review
- **runtime/** - Potentially orphaned experimental code
- **multi_agent_sim/** - Separate from persona system, unclear relationship
- **persona/learning/** - May consolidate with ml/ module
- **Memory/** - Potentially legacy vs. ml/ episodic memory

---

## Migration Guides

### From 1.0 to 1.1
1. Update any custom minister implementations (API unchanged)
2. No database migration required
3. KIS scoring may improve decision quality automatically

### From 1.1 to 1.2
1. Optional: Use new LLM conversation engine for dialogue testing
2. Optional: Adopt SessionManager for multi-session workflows
3. Documentation moved to documentation/ folder (symbolic links created)

---

## Contributing

### Reporting Issues
Please use the AUDIT_REPORT.txt format:
- Clear title
- Reproduction steps
- Expected vs actual behavior
- Environment (Python version, OS, Ollama status)

### Code Changes
1. Create feature branch
2. Update relevant markdown files
3. Add test coverage
4. Submit with clear commit messages

---

## Support

- **Quick Start:** See [START_HERE.md](START_HERE.md)
- **Full Guide:** [SYSTEM_ARCHITECTURE.md](documentation/SYSTEM_ARCHITECTURE.md)
- **Mode Selection:** [MODE_SELECTION_GUIDE.md](documentation/MODE_SELECTION_GUIDE.md)
- **Audit Report:** [AUDIT_REPORT.txt](AUDIT_REPORT.txt)

---

## License & Attribution

**Creator:** Alfred (Stabilizing Intelligence)
**Project Motto:** "Power that costs identity is rejected."

---

## Version Tracking

| Version | Date | Status | Key Feature |
|---------|------|--------|-----------|
| 1.2.0 | Feb 19, 2026 | ✅ Current | LLM Conversations + Sessions |
| 1.1.0 | Feb 18, 2026 | ✅ Stable | Ministerial Councils + KIS |
| 1.0.0 | Feb 10, 2026 | ✅ Stable | Decision Guidance Core |
| 0.9.0 | Jan 2026 | ⚠️ Legacy | Initial Development |

---

**Last Updated:** February 19, 2026
**Maintainer:** Alfred (Stabilizing Intelligence)
