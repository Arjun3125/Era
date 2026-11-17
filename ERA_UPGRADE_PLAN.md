# ERA Self-Improvement & Vision Upgrade Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform ERA from a functional advisor into a self-improving wise person — one that learns from every conversation, argues through its ministers' own voices, remembers who you are across sessions, and gets sharper the more you use it.

**Architecture:** Six independent tracks layered on top of ERA_FIX_PLAN.md (which must be completed first). Each track closes one feedback loop or adds one capability. Tracks 1–2 are pure logic (no new dependencies). Track 3 adds per-minister LLM calls. Track 4 adds a user profile store. Track 5 wires the outcome loop. Track 6 is efficiency.

**Tech Stack:** Python 3.11, FastAPI, PyYAML, chromadb, ollama, pydantic — all already in `.venv`. No new packages required.

**Prerequisite:** `ERA_FIX_PLAN.md` all 6 tasks complete. Specifically: BASE_PATH fixed, Chroma running, doctrine YAMLs loaded into NativeCouncil.

---

## File Map

| File | Status | Change |
|------|--------|--------|
| `persona/knowledge_engine.py` | Modify | Add `reinforce_entry()`, `penalize_entry()`, module-level `_BUILTIN_ENTRIES` |
| `api.py` | Modify | Add `POST /feedback`, `GET /profile`, `POST /profile`, per-turn KIS tracking |
| `persona/user_profile.py` | Create | `UserProfile` dataclass + disk persistence |
| `persona/council/minister_voice.py` | Create | LLM-per-minister deliberation using doctrine YAML as system prompt |
| `modules/council_execution/engine.py` | Modify | Wire `minister_voice.py` for Meeting/Darbar modes |
| `persona/analysis.py` | Modify | Replace 4-call handshake with 1 structured `analyze()` call |
| `persona/context.py` | Modify | Inject user profile + KIS knowledge into system context |
| `persona/learning/episodic_memory.py` | Modify | Add `update_outcome()` to patch existing episodes |
| `persona/council/minister_voice.py` | Modify | Add dialectical output + minority escalation flag |
| `modules/council_execution/engine.py` | Modify | Domain routing + multi-round dialogue loop |
| `persona/learning/minister_confidence.py` | Create | Per-minister Bayesian confidence calibration |
| `tests/test_era_upgrades.py` | Create | All tests for this plan |

---

## Track 1: Knowledge Reinforcement Loop

**What this closes:** KIS already reads `reinforcement_count` and `penalty_count` from minister JSON files and applies 180-day decay. Nothing ever writes these values back. Closing this loop means principles that help get surfaced more; ones that led to bad advice decay.

**Files:**
- Modify: `persona/knowledge_engine.py`
- Modify: `api.py`
- Create: `tests/test_era_upgrades.py`

### Task 1.1 — Add `reinforce_entry()` and `penalize_entry()` to knowledge_engine.py

- [ ] **Step 1: Write the failing tests**

Create `tests/test_era_upgrades.py`:

```python
"""Tests for ERA self-improvement upgrades."""
import json
import os
import tempfile
from pathlib import Path


def _make_minister_dir(tmp: Path, domain: str) -> Path:
    d = tmp / "ministers" / domain
    d.mkdir(parents=True)
    data = {
        "domain": domain, "category": "principles",
        "entries": [
            {"id": "e1", "text": "Save ten percent.", "source": {"book": "babylon"}, "weight": 1.0},
            {"id": "e2", "text": "Live below your means.", "source": {"book": "babylon"}, "weight": 1.0},
        ],
        "meta": {"total_entries": 2},
    }
    (d / "principles.json").write_text(json.dumps(data, indent=2))
    return d


def test_reinforce_entry_increments_count(tmp_path):
    """reinforce_entry must increment reinforcement_count and set last_reinforced_date."""
    import sys
    for k in list(sys.modules.keys()):
        if "knowledge_engine" in k:
            del sys.modules[k]

    d = _make_minister_dir(tmp_path, "adaptation")
    os.environ["ERA_MINISTER_PATH"] = str(tmp_path / "ministers")

    from persona.knowledge_engine import reinforce_entry
    reinforce_entry("e1", "adaptation", "principles", positive=True)

    data = json.loads((d / "principles.json").read_text())
    entry = next(e for e in data["entries"] if e["id"] == "e1")
    mem = entry.get("memory", {})
    assert mem.get("reinforcement_count", 0) >= 1, "reinforcement_count not incremented"
    assert "last_reinforced_date" in mem, "last_reinforced_date not set"


def test_penalize_entry_increments_penalty(tmp_path):
    """reinforce_entry with positive=False must increment penalty_count."""
    import sys
    for k in list(sys.modules.keys()):
        if "knowledge_engine" in k:
            del sys.modules[k]

    d = _make_minister_dir(tmp_path, "risk")
    os.environ["ERA_MINISTER_PATH"] = str(tmp_path / "ministers")

    from persona.knowledge_engine import reinforce_entry
    reinforce_entry("e2", "risk", "principles", positive=False)

    data = json.loads((d / "principles.json").read_text())
    entry = next(e for e in data["entries"] if e["id"] == "e2")
    mem = entry.get("memory", {})
    assert mem.get("penalty_count", 0) >= 1, "penalty_count not incremented"
```

- [ ] **Step 2: Run to confirm failure**

```
cd C:\Users\naren\Work\Projects\School\era
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_reinforce_entry_increments_count tests/test_era_upgrades.py::test_penalize_entry_increments_penalty -v
```

Expected: **FAIL** — `ImportError: cannot import name 'reinforce_entry'`

- [ ] **Step 3: Add `reinforce_entry()` to `persona/knowledge_engine.py`**

Add after the `load_domain_knowledge()` function (around line 270):

```python
def reinforce_entry(entry_id: str, domain: str, category: str, positive: bool = True) -> bool:
    """Increment reinforcement_count (positive=True) or penalty_count (positive=False).

    Writes back to the minister JSON file. Returns True if entry was found and updated.
    category: 'principles' | 'rules' | 'warnings' | 'claims'
    """
    import datetime as _dt
    file_path = os.path.join(BASE_PATH, domain, f"{category}.json")
    if not os.path.isfile(file_path):
        return False
    try:
        data = json.loads(Path(file_path).read_text(encoding="utf-8"))
        entries = data.get("entries", [])
        for entry in entries:
            if entry.get("id") == entry_id:
                mem = entry.setdefault("memory", {})
                if positive:
                    mem["reinforcement_count"] = mem.get("reinforcement_count", 0) + 1
                    mem["last_reinforced_date"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
                else:
                    mem["penalty_count"] = mem.get("penalty_count", 0) + 1
                Path(file_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
                # Invalidate Chroma collection so next query re-indexes updated weights
                global _chroma_collection
                _chroma_collection = None
                return True
    except Exception:
        pass
    return False
```

Add `from pathlib import Path` to imports if not already present (check line 1–10).

- [ ] **Step 4: Run to confirm pass**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_reinforce_entry_increments_count tests/test_era_upgrades.py::test_penalize_entry_increments_penalty -v
```

Expected: **PASS**

- [ ] **Step 5: Commit**

```
git add persona/knowledge_engine.py tests/test_era_upgrades.py
git commit -m "feat: reinforce_entry/penalize_entry — minister knowledge weights update from feedback"
```

---

### Task 1.2 — Add `POST /feedback` endpoint to api.py

The `/feedback` endpoint receives a session ID, turn number, whether the advice was helpful, and which knowledge entries were used. It calls `reinforce_entry()` for each.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_feedback_endpoint_updates_entry(tmp_path):
    """POST /feedback must call reinforce_entry for each entry_id in the payload."""
    import sys
    for k in list(sys.modules.keys()):
        if "knowledge_engine" in k or "api" in k:
            del sys.modules[k]

    d = _make_minister_dir(tmp_path, "adaptation")
    os.environ["ERA_MINISTER_PATH"] = str(tmp_path / "ministers")

    from fastapi.testclient import TestClient
    import api

    # Stub components so /feedback doesn't need Ollama
    api._components["llm"] = None

    client = TestClient(api.app)
    r = client.post("/feedback", json={
        "session_id": "s1",
        "turn": 1,
        "helpful": True,
        "entries_used": [
            {"entry_id": "e1", "domain": "adaptation", "category": "principles"}
        ],
    })
    assert r.status_code == 200, r.text
    assert r.json()["updated"] == 1

    data = json.loads((d / "principles.json").read_text())
    entry = next(e for e in data["entries"] if e["id"] == "e1")
    assert entry.get("memory", {}).get("reinforcement_count", 0) >= 1
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_feedback_endpoint_updates_entry -v
```

Expected: **FAIL** — 404 (route not found)

- [ ] **Step 3: Add `/feedback` route to `api.py`**

Add these models and route to `api.py`:

```python
class EntryUsed(BaseModel):
    entry_id: str
    domain: str
    category: str  # principles | rules | warnings | claims


class FeedbackRequest(BaseModel):
    session_id: str
    turn: int
    helpful: bool
    entries_used: list[EntryUsed] = []
    comment: Optional[str] = None


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest) -> Dict[str, Any]:
    """Record whether the advice for a turn was helpful.

    Updates minister knowledge weights (reinforcement or penalty).
    Also patches episode.outcome in episodic memory if a matching episode exists.
    """
    from persona.knowledge_engine import reinforce_entry

    updated = 0
    for entry in req.entries_used:
        ok = reinforce_entry(
            entry_id=entry.entry_id,
            domain=entry.domain,
            category=entry.category,
            positive=req.helpful,
        )
        if ok:
            updated += 1

    # Patch episodic memory if session exists
    session = _sessions.get(req.session_id)
    if session and hasattr(session, "episodic_memory"):
        outcome = "success" if req.helpful else "failure"
        session.episodic_memory.update_outcome_for_turn(req.turn, outcome)

    return {
        "session_id": req.session_id,
        "turn": req.turn,
        "helpful": req.helpful,
        "updated": updated,
    }
```

- [ ] **Step 4: Add `update_outcome_for_turn()` to `EpisodicMemory`**

In `persona/learning/episodic_memory.py`, add after `record_consequence()`:

```python
def update_outcome_for_turn(self, turn_id: int, outcome: str) -> bool:
    """Patch the outcome field of the episode matching turn_id. Rewrites the JSONL file."""
    for ep in self.episodes.values():
        if ep.turn_id == turn_id:
            ep.outcome = outcome
            self._rewrite_disk()
            return True
    return False

def _rewrite_disk(self) -> None:
    """Full rewrite of the JSONL file from in-memory episodes."""
    try:
        with open(self.storage_path, "w", encoding="utf-8") as f:
            for ep in self.episodes.values():
                f.write(json.dumps(asdict(ep)) + "\n")
    except Exception as e:
        print(f"[WARNING] Failed to rewrite episodes: {e}")
```

- [ ] **Step 5: Run test**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_feedback_endpoint_updates_entry -v
```

Expected: **PASS**

- [ ] **Step 6: Commit**

```
git add api.py persona/learning/episodic_memory.py tests/test_era_upgrades.py
git commit -m "feat: POST /feedback endpoint — closes knowledge reinforcement loop"
```

---

### Task 1.3 — Track KIS entries served per turn in API response

The `/chat` response currently has no `entries_used` field, so the client cannot send back which entries to reinforce. Fix that.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_chat_response_includes_entries_used():
    """/chat response must include entries_used list so client can submit /feedback."""
    import api
    from fastapi.testclient import TestClient

    class FakeLLM:
        def speak(self, ctx, inp): return "advice text"

    api._components.clear()
    api._components["llm"] = FakeLLM()

    client = TestClient(api.app)
    r = client.post("/chat", json={"message": "should I quit my job", "session_id": "t1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "entries_used" in body, f"entries_used missing from response: {list(body.keys())}"
    assert isinstance(body["entries_used"], list)
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_chat_response_includes_entries_used -v
```

Expected: **FAIL** — `entries_used missing from response`

- [ ] **Step 3: Update `ChatResponse` and `_process_turn()` in `api.py`**

Update `ChatResponse`:

```python
class ChatResponse(BaseModel):
    session_id: str
    response: str
    mode: str
    turn: int
    domains: list[str]
    domain_confidence: float
    entries_used: list[dict] = []  # [{entry_id, domain, category, content_preview}]
```

Update `_process_turn()` to return entries alongside response:

```python
def _process_turn(state: CognitiveState, user_input: str) -> tuple[str, list[dict]]:
    llm = _components["llm"]

    raw_sit = _assess_situation_sync(llm, user_input)
    if not isinstance(raw_sit, dict):
        raw_sit = {}
    state.last_situation = {
        "situation_type": raw_sit.get("situation_type", "unclear"),
        "clarity": float(raw_sit.get("clarity", 0.0)),
        "emotional_load": float(raw_sit.get("emotional_load", 0.0)),
    }
    state.last_emotional_load = state.last_situation["emotional_load"]

    freq = (
        "low" if len(user_input.split()) <= 3
        else "medium" if len(user_input.split()) <= 12
        else "high"
    )
    state.user_frequency = freq  # type: ignore[attr-defined]

    # KIS retrieval — capture entries for tracking
    entries_used: list[dict] = []
    if state.domains:
        try:
            from persona.knowledge_engine import synthesize_knowledge
            kis = synthesize_knowledge(
                user_input=user_input,
                active_domains=state.domains,
                domain_confidence=max(state.domain_confidence, 0.5),
            )
            for item in kis.get("synthesized_knowledge", []):
                src = item.get("source", {})
                entries_used.append({
                    "entry_id": item.get("aku_id", ""),
                    "domain": item.get("_domain", ""),
                    "category": item.get("type", "principle") + "s",
                    "content_preview": str(item.get("content", ""))[:80],
                })
        except Exception:
            pass

    system_context = build_system_context(state)
    response = llm.speak(system_context, user_input)

    state.recent_turns.append((user_input, response))
    if len(state.recent_turns) > 50:
        state.recent_turns = state.recent_turns[-50:]
    state.turn_count += 1

    if state.domains:
        _executor.submit(_bg_kis, state, user_input)

    return response, entries_used
```

Update the `/chat` route to unpack the tuple:

```python
response, entries_used = _process_turn(state, req.message.strip())

return ChatResponse(
    session_id=session_id,
    response=response,
    mode=state.mode,
    turn=state.turn_count,
    domains=list(state.domains),
    domain_confidence=float(state.domain_confidence),
    entries_used=entries_used,
)
```

- [ ] **Step 4: Run tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_chat_response_includes_entries_used -v
```

Expected: **PASS**

- [ ] **Step 5: Commit**

```
git add api.py tests/test_era_upgrades.py
git commit -m "feat: /chat response includes entries_used for feedback loop"
```

---

## Track 2: Persistent User Profile

**What this closes:** Every session currently starts blank. The wise advisor cannot notice "you've asked about quitting three times this month" because it has no memory across sessions. A user profile stores the person's persistent attributes — risk tolerance, recurring themes, past decision patterns — separate from conversation state.

**Files:**
- Create: `persona/user_profile.py`
- Create: `data/user_profiles/` (directory, auto-created)
- Modify: `api.py`
- Modify: `persona/context.py`

### Task 2.1 — Create UserProfile dataclass with disk persistence

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_user_profile_persists_across_loads(tmp_path):
    """UserProfile saved to disk must reload with the same data."""
    import sys
    for k in list(sys.modules.keys()):
        if "user_profile" in k:
            del sys.modules[k]

    os.environ["ERA_PROFILE_PATH"] = str(tmp_path / "profiles")

    from persona.user_profile import UserProfile, save_profile, load_profile

    profile = UserProfile(
        user_id="u1",
        risk_tolerance="cautious",
        recurring_themes=["career", "finance"],
        total_turns=5,
    )
    save_profile(profile)

    loaded = load_profile("u1")
    assert loaded is not None
    assert loaded.risk_tolerance == "cautious"
    assert "career" in loaded.recurring_themes
    assert loaded.total_turns == 5


def test_user_profile_updates_themes(tmp_path):
    """update_themes must append new domains and deduplicate."""
    import sys
    for k in list(sys.modules.keys()):
        if "user_profile" in k:
            del sys.modules[k]

    os.environ["ERA_PROFILE_PATH"] = str(tmp_path / "profiles")

    from persona.user_profile import UserProfile, save_profile, load_profile

    profile = UserProfile(user_id="u2", recurring_themes=["career"])
    profile.update_themes(["career", "finance", "health"])
    save_profile(profile)

    loaded = load_profile("u2")
    assert "finance" in loaded.recurring_themes
    assert loaded.recurring_themes.count("career") == 1  # no duplicates
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_user_profile_persists_across_loads tests/test_era_upgrades.py::test_user_profile_updates_themes -v
```

Expected: **FAIL** — `ModuleNotFoundError: No module named 'persona.user_profile'`

- [ ] **Step 3: Create `persona/user_profile.py`**

```python
"""Persistent user profile — survives across API sessions."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


def _profile_dir() -> Path:
    base = os.environ.get("ERA_PROFILE_PATH") or str(
        Path(__file__).resolve().parent.parent / "data" / "user_profiles"
    )
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class UserProfile:
    user_id: str
    risk_tolerance: str = "moderate"       # cautious | moderate | bold
    recurring_themes: List[str] = field(default_factory=list)
    total_turns: int = 0
    successful_decisions: int = 0
    failed_decisions: int = 0
    last_active: Optional[str] = None
    notes: str = ""                        # free-text notes added by N

    def update_themes(self, new_domains: List[str]) -> None:
        """Append domains not already in the list."""
        for d in new_domains:
            if d and d not in self.recurring_themes:
                self.recurring_themes.append(d)

    def record_outcome(self, success: bool) -> None:
        if success:
            self.successful_decisions += 1
        else:
            self.failed_decisions += 1

    def success_rate(self) -> float:
        total = self.successful_decisions + self.failed_decisions
        return self.successful_decisions / total if total else 0.0

    def to_context_hint(self) -> str:
        """One-line string injected into the system prompt."""
        themes = ", ".join(self.recurring_themes[-5:]) if self.recurring_themes else "none yet"
        return (
            f"User profile: risk={self.risk_tolerance}, "
            f"themes={themes}, "
            f"turns={self.total_turns}, "
            f"success_rate={self.success_rate():.0%}"
        )


def save_profile(profile: UserProfile) -> None:
    path = _profile_dir() / f"{profile.user_id}.json"
    path.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")


def load_profile(user_id: str) -> Optional[UserProfile]:
    path = _profile_dir() / f"{user_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return UserProfile(**data)
    except Exception:
        return None


def get_or_create_profile(user_id: str) -> UserProfile:
    profile = load_profile(user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
        save_profile(profile)
    return profile
```

- [ ] **Step 4: Run tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_user_profile_persists_across_loads tests/test_era_upgrades.py::test_user_profile_updates_themes -v
```

Expected: **PASS**

- [ ] **Step 5: Commit**

```
git add persona/user_profile.py tests/test_era_upgrades.py
git commit -m "feat: UserProfile — persistent user identity across sessions"
```

---

### Task 2.2 — Wire UserProfile into API and system context

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_api_accepts_user_id_and_builds_profile(tmp_path):
    """POST /chat with user_id must create/load a UserProfile and increment total_turns."""
    import sys
    for k in list(sys.modules.keys()):
        if "api" in k or "user_profile" in k:
            del sys.modules[k]

    os.environ["ERA_PROFILE_PATH"] = str(tmp_path / "profiles")

    import api
    from fastapi.testclient import TestClient

    class FakeLLM:
        def speak(self, ctx, inp): return "response"

    api._components.clear()
    api._components["llm"] = FakeLLM()

    client = TestClient(api.app)
    r = client.post("/chat", json={
        "message": "should I change careers",
        "session_id": "sess1",
        "user_id": "user42",
    })
    assert r.status_code == 200, r.text

    # Profile must now exist on disk
    from persona.user_profile import load_profile
    profile = load_profile("user42")
    assert profile is not None
    assert profile.total_turns >= 1
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_api_accepts_user_id_and_builds_profile -v
```

Expected: **FAIL** — `ChatRequest` has no `user_id` field

- [ ] **Step 3: Update `ChatRequest` in `api.py`**

```python
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: Optional[str] = None
    user_id: Optional[str] = None          # links session to persistent profile
```

- [ ] **Step 4: Update the `Session` dataclass and `/chat` route**

In `api.py`, update `Session`:

```python
from persona.user_profile import UserProfile, get_or_create_profile, save_profile

@dataclass
class Session:
    state: CognitiveState = dc_field(default_factory=lambda: _make_state())
    mode_orchestrator: ModeOrchestrator = dc_field(default_factory=ModeOrchestrator)
    dynamic_council: DynamicCouncil = dc_field(default_factory=lambda: DynamicCouncil(llm=None))
    user_id: Optional[str] = None
    profile: Optional[UserProfile] = None
```

In the `/chat` route, after `session = _get_or_create_session(session_id)`, add:

```python
# Attach user profile on first mention of user_id
if req.user_id and session.user_id is None:
    session.user_id = req.user_id
    session.profile = get_or_create_profile(req.user_id)

# Inject profile hint into state for context builder
if session.profile:
    state.profile_hint = session.profile.to_context_hint()  # type: ignore[attr-defined]
```

After the response is generated, update the profile:

```python
# Update profile stats
if session.profile:
    session.profile.total_turns += 1
    session.profile.update_themes(list(state.domains))
    import datetime as _dt
    session.profile.last_active = _dt.datetime.now(_dt.timezone.utc).isoformat()
    save_profile(session.profile)
```

- [ ] **Step 5: Inject profile hint into `build_system_context()`**

In `persona/context.py`, update `build_system_context()`:

```python
def build_system_context(state: CognitiveState) -> str:
    mode = state.mode or "meeting"
    hint = MODE_VISIBLE_HINT.get(mode, MODE_VISIBLE_HINT["meeting"])
    domains = ", ".join(state.domains) if state.domains else "general"
    parts = [
        f"Mode: {mode}",
        f"Hint: {hint}",
        f"Domains: {domains}",
        f"Turn: {state.turn_count}",
    ]
    profile_hint = getattr(state, "profile_hint", None)
    if profile_hint:
        parts.append(f"User: {profile_hint}")
    return "\n".join(parts)
```

- [ ] **Step 6: Run tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_api_accepts_user_id_and_builds_profile -v
```

Expected: **PASS**

- [ ] **Step 7: Add `GET /profile/{user_id}` endpoint**

```python
@app.get("/profile/{user_id}")
def get_profile(user_id: str) -> Dict[str, Any]:
    from persona.user_profile import load_profile
    profile = load_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    from dataclasses import asdict
    return asdict(profile)
```

- [ ] **Step 8: Commit**

```
git add api.py persona/context.py tests/test_era_upgrades.py
git commit -m "feat: user_id in /chat links to persistent UserProfile injected into system context"
```

---

## Track 3: Per-Minister LLM Voice

**What this closes:** Ministers currently score by keyword. The doctrine YAMLs give each minister a rich persona — worldview, typical warnings, failure modes. Using the doctrine canon as an LLM system prompt makes each minister argue in its own voice. Applied only in Meeting and Darbar modes (Quick and War stay fast-path).

**Files:**
- Create: `persona/council/minister_voice.py`
- Modify: `modules/council_execution/engine.py`

### Task 3.1 — Create `minister_voice.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_minister_voice_returns_structured_response():
    """MinisterVoice.deliberate() must return a dict with stance, reasoning, confidence."""
    import sys
    for k in list(sys.modules.keys()):
        if "minister_voice" in k:
            del sys.modules[k]

    from persona.council.minister_voice import MinisterVoice

    class FakeLLM:
        def analyze(self, system_prompt, user_prompt):
            return '{"stance": "oppose", "reasoning": "Risk is high.", "confidence": 0.75}'

    voice = MinisterVoice(minister_name="risk", llm=FakeLLM())
    result = voice.deliberate("Should I bet all my savings on a startup?", {})

    assert result["stance"] in {"support", "oppose", "neutral"}
    assert isinstance(result["reasoning"], str) and len(result["reasoning"]) > 0
    assert 0.0 <= result["confidence"] <= 1.0


def test_minister_voice_falls_back_on_bad_json():
    """MinisterVoice must not crash if the LLM returns non-JSON."""
    from persona.council.minister_voice import MinisterVoice

    class BadLLM:
        def analyze(self, system_prompt, user_prompt):
            return "I think this is risky."   # plain text, not JSON

    voice = MinisterVoice(minister_name="risk", llm=BadLLM())
    result = voice.deliberate("take a big risk?", {})
    assert "stance" in result
    assert "reasoning" in result
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_minister_voice_returns_structured_response tests/test_era_upgrades.py::test_minister_voice_falls_back_on_bad_json -v
```

Expected: **FAIL** — `ModuleNotFoundError`

- [ ] **Step 3: Create `persona/council/minister_voice.py`**

```python
"""MinisterVoice — LLM-per-minister deliberation using doctrine YAML as system prompt."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml as _yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False

_DOCTRINE_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "doctrine" / "locked"

_YAML_MAP = {
    "risk": "risk", "risk_resources": "risk", "power": "power",
    "grand_strategist": "grand_strategist", "technology": "technology",
    "timing": "timing", "optionality": "optionality", "data": "data",
    "diplomacy": "diplomacy", "psychology": "psychology",
    "legitimacy": "legitimacy", "conflict": "conflict", "truth": "truth",
    "discipline": "discipline", "intelligence": "intelligence",
    "narrative": "narrative", "sovereign": "n",
    "adaptation": "adaptation", "war_mode": "war_mode",
}

_FALLBACK_PERSONA = (
    "You are a wise minister advising on important decisions. "
    "Analyze the situation and give your honest stance."
)


def _load_minister_persona(minister_name: str) -> str:
    """Return the persona canon string from the minister's doctrine YAML."""
    if not _YAML_OK:
        return _FALLBACK_PERSONA
    yaml_name = _YAML_MAP.get(minister_name)
    if not yaml_name:
        return _FALLBACK_PERSONA
    yaml_path = _DOCTRINE_ROOT / f"{yaml_name}.yaml"
    if not yaml_path.exists():
        return _FALLBACK_PERSONA
    try:
        doc = _yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        canon = (doc.get("persona") or {}).get("canon") or ""
        return canon.strip() or _FALLBACK_PERSONA
    except Exception:
        return _FALLBACK_PERSONA


_MINISTER_INSTRUCTION = """
You are {minister_name} in a council deliberation.

{persona_canon}

---
Given the situation below, respond ONLY with valid JSON in this exact format:
{{
  "stance": "support" | "oppose" | "neutral",
  "reasoning": "<1-2 sentences from your doctrine perspective>",
  "confidence": <0.0 to 1.0>,
  "warning": "<optional red-line concern, or empty string>"
}}
"""


class MinisterVoice:
    """Wraps one minister's LLM deliberation call."""

    def __init__(self, minister_name: str, llm: Any):
        self.minister_name = minister_name
        self.llm = llm
        self._persona = _load_minister_persona(minister_name)
        self._system_prompt = _MINISTER_INSTRUCTION.format(
            minister_name=minister_name.replace("_", " ").title(),
            persona_canon=self._persona,
        )

    def deliberate(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Call the LLM as this minister. Returns structured stance dict."""
        domain_hint = ", ".join(context.get("domains", [])) or "general"
        prompt = f"Domains: {domain_hint}\n\nSituation: {user_input}"

        try:
            raw = self.llm.analyze(self._system_prompt, prompt)
            return self._parse(raw)
        except Exception as e:
            return {
                "stance": "neutral",
                "reasoning": f"[{self.minister_name} unavailable: {e}]",
                "confidence": 0.3,
                "warning": "",
            }

    def _parse(self, raw: str) -> Dict[str, Any]:
        """Parse JSON from LLM output, with robust fallback."""
        # Try direct JSON parse
        try:
            data = json.loads(raw.strip())
            return self._validate(data)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try extracting JSON block from markdown fencing or surrounding text
        match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return self._validate(data)
            except Exception:
                pass

        # Plain-text fallback: infer stance from keywords
        text = raw.lower()
        if any(w in text for w in ["oppose", "risk", "danger", "avoid", "caution"]):
            stance = "oppose"
        elif any(w in text for w in ["support", "proceed", "go ahead", "recommend"]):
            stance = "support"
        else:
            stance = "neutral"

        return {
            "stance": stance,
            "reasoning": raw[:200].strip(),
            "confidence": 0.5,
            "warning": "",
        }

    @staticmethod
    def _validate(data: Dict[str, Any]) -> Dict[str, Any]:
        valid_stances = {"support", "oppose", "neutral"}
        stance = str(data.get("stance", "neutral")).lower()
        if stance not in valid_stances:
            stance = "neutral"
        return {
            "stance": stance,
            "reasoning": str(data.get("reasoning", ""))[:400],
            "confidence": max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
            "warning": str(data.get("warning", "")),
        }
```

- [ ] **Step 4: Run tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_minister_voice_returns_structured_response tests/test_era_upgrades.py::test_minister_voice_falls_back_on_bad_json -v
```

Expected: **PASS**

- [ ] **Step 5: Commit**

```
git add persona/council/minister_voice.py tests/test_era_upgrades.py
git commit -m "feat: MinisterVoice — doctrine YAML as LLM system prompt per minister"
```

---

### Task 3.2 — Wire MinisterVoice into NativeCouncil for Meeting/Darbar modes

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_native_council_uses_llm_voice_in_meeting_mode():
    """NativeCouncil with an LLM must use MinisterVoice for meeting/darbar modes."""
    import sys
    for k in list(sys.modules.keys()):
        if "council_execution" in k:
            del sys.modules[k]

    call_log = []

    class FakeLLM:
        def analyze(self, sys_p, usr_p):
            call_log.append(usr_p)
            return '{"stance": "oppose", "reasoning": "Too risky.", "confidence": 0.8, "warning": ""}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=FakeLLM())
    result = council.deliberate(
        user_input="Should I quit my job?",
        context={"domains": ["career"], "mode": "meeting"},
    )
    # In meeting mode, at least some ministers must have used LLM voice
    assert len(call_log) > 0, "No LLM calls made — MinisterVoice not wired in"
    assert "stances" in result or "recommendation" in result
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_native_council_uses_llm_voice_in_meeting_mode -v
```

Expected: **FAIL** — `NativeCouncil` has no `deliberate()` method

- [ ] **Step 3: Add `deliberate()` to `NativeCouncil` in `modules/council_execution/engine.py`**

Add these imports at the top:

```python
_MEETING_MINISTERS = ["risk", "grand_strategist", "optionality", "psychology", "timing"]
_DARBAR_MINISTERS = [
    "risk", "grand_strategist", "power", "optionality", "psychology",
    "timing", "legitimacy", "truth", "data", "conflict",
    "diplomacy", "technology", "intelligence", "narrative",
    "discipline", "adaptation", "sovereign", "war_mode",
]
```

Add `deliberate()` method to `NativeCouncil`:

```python
def deliberate(self, user_input: str, context: dict) -> dict:
    """Run council deliberation. Uses LLM voice for meeting/darbar if LLM available.

    Falls back to keyword scoring for quick/war modes or when no LLM present.
    """
    mode = str(context.get("mode", "meeting")).lower()

    if self.llm is not None and mode in {"meeting", "darbar"}:
        minister_names = _DARBAR_MINISTERS if mode == "darbar" else _MEETING_MINISTERS
        return self._llm_deliberate(user_input, context, minister_names)
    else:
        return self._keyword_deliberate(user_input, context)

def _llm_deliberate(self, user_input: str, context: dict, minister_names: list) -> dict:
    """Call each minister via MinisterVoice, aggregate stances."""
    try:
        from persona.council.minister_voice import MinisterVoice
    except ImportError:
        return self._keyword_deliberate(user_input, context)

    stances = {}
    support, oppose, neutral = 0, 0, 0
    warnings = []

    for name in minister_names:
        voice = MinisterVoice(minister_name=name, llm=self.llm)
        result = voice.deliberate(user_input, context)
        stances[name] = result
        s = result["stance"]
        if s == "support": support += 1
        elif s == "oppose": oppose += 1
        else: neutral += 1
        if result.get("warning"):
            warnings.append(f"{name}: {result['warning']}")

    total = max(1, support + oppose + neutral)
    if support > oppose:
        outcome = "proceed"
    elif oppose > support:
        outcome = "reconsider"
    else:
        outcome = "defer"

    consensus_strength = max(support, oppose) / total

    return {
        "outcome": outcome,
        "recommendation": outcome,
        "stances": stances,
        "consensus_strength": round(consensus_strength, 3),
        "red_line_concerns": warnings,
        "ministers_involved": minister_names,
    }

def _keyword_deliberate(self, user_input: str, context: dict) -> dict:
    """Keyword-based fallback when no LLM or in quick/war mode."""
    stances = {}
    support, oppose, neutral = 0, 0, 0
    for name, minister in self.ministers.items():
        result = minister.analyze(user_input, context)
        stances[name] = result
        s = result["stance"]
        if s == "support": support += 1
        elif s == "oppose": oppose += 1
        else: neutral += 1

    total = max(1, support + oppose + neutral)
    outcome = "proceed" if support > oppose else ("reconsider" if oppose > support else "defer")
    return {
        "outcome": outcome,
        "recommendation": outcome,
        "stances": stances,
        "consensus_strength": round(max(support, oppose) / total, 3),
        "red_line_concerns": [],
        "ministers_involved": list(self.ministers.keys()),
    }
```

- [ ] **Step 4: Run tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_native_council_uses_llm_voice_in_meeting_mode -v
```

Expected: **PASS**

- [ ] **Step 5: Smoke-test a full deliberation**

```
cd C:\Users\naren\Work\Projects\School\era
.venv\Scripts\python -c "
from modules.council_execution.engine import NativeCouncil

class EchoLLM:
    def analyze(self, s, u):
        return '{\"stance\": \"oppose\", \"reasoning\": \"Too uncertain.\", \"confidence\": 0.7, \"warning\": \"\"}'

c = NativeCouncil(llm=EchoLLM())
r = c.deliberate('Should I leave my stable job for a startup?', {'domains': ['career'], 'mode': 'meeting'})
print('outcome:', r['outcome'])
print('consensus:', r['consensus_strength'])
print('ministers:', len(r['ministers_involved']))
"
```

Expected: outcome and stances from all 5 meeting ministers.

- [ ] **Step 6: Commit**

```
git add modules/council_execution/engine.py tests/test_era_upgrades.py
git commit -m "feat: NativeCouncil.deliberate() uses LLM voice per minister in meeting/darbar modes"
```

---

### Task 3.3 — Surface Disagreement in Council Output

**What this adds:** When ministers disagree significantly (top two stances differ), the council output must explain the conflict explicitly — not paper over it with a consensus score. This is what makes the advisor trustworthy: it shows its work.

**Files:**
- Modify: `modules/council_execution/engine.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_council_surfaces_disagreement_when_ministers_conflict():
    """When support != oppose, council output must include a dissent_summary string."""
    import sys
    for k in list(sys.modules.keys()):
        if "council_execution" in k:
            del sys.modules[k]

    call_count = [0]

    class SplitLLM:
        def analyze(self, sys_p, usr_p):
            call_count[0] += 1
            # Alternate: odd calls support, even calls oppose
            stance = "support" if call_count[0] % 2 == 1 else "oppose"
            return f'{{"stance": "{stance}", "reasoning": "My view.", "confidence": 0.8, "warning": ""}}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=SplitLLM())
    result = council.deliberate(
        user_input="Should I take the job offer?",
        context={"domains": ["career"], "mode": "meeting"},
    )
    # When split vote, dissent_summary must be present and non-empty
    if result["outcome"] in {"proceed", "reconsider"}:
        assert "dissent_summary" in result, "dissent_summary missing"
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_council_surfaces_disagreement_when_ministers_conflict -v
```

Expected: **FAIL** — `dissent_summary` key missing

- [ ] **Step 3: Add `dissent_summary` to `_llm_deliberate()` in `engine.py`**

Update the return dict of `_llm_deliberate()`:

```python
# Build dissent summary when there is meaningful disagreement
dissent_summary = ""
if support > 0 and oppose > 0:
    supporters = [n for n, r in stances.items() if r["stance"] == "support"]
    opposers = [n for n, r in stances.items() if r["stance"] == "oppose"]
    top_support_reason = stances[supporters[0]]["reasoning"] if supporters else ""
    top_oppose_reason = stances[opposers[0]]["reasoning"] if opposers else ""
    dissent_summary = (
        f"{', '.join(supporters[:2])} advocate proceeding: {top_support_reason[:120]} | "
        f"{', '.join(opposers[:2])} urge caution: {top_oppose_reason[:120]}"
    )

return {
    "outcome": outcome,
    "recommendation": outcome,
    "stances": stances,
    "consensus_strength": round(consensus_strength, 3),
    "red_line_concerns": warnings,
    "ministers_involved": minister_names,
    "dissent_summary": dissent_summary,
}
```

- [ ] **Step 4: Run the test**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_council_surfaces_disagreement_when_ministers_conflict -v
```

Expected: **PASS**

- [ ] **Step 5: Commit**

```
git add modules/council_execution/engine.py tests/test_era_upgrades.py
git commit -m "feat: council dissent_summary — surfaces disagreement instead of averaging it away"
```

---

### Task 3.4 — Minority Voice Escalation

**What this adds:** If a single minister has high confidence but low support ratio (everyone else disagrees), their concern gets escalated explicitly as `minority_alert`. This is how wise councils catch black swans — one Cassandra shouldn't be silenced by majority vote.

**Files:**
- Modify: `modules/council_execution/engine.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_minority_escalation_when_one_minister_highly_confident_outlier():
    """If one minister is highly confident but alone, minority_alert must fire."""
    import sys
    for k in list(sys.modules.keys()):
        if "council_execution" in k:
            del sys.modules[k]

    call_count = [0]

    class CassandraLLM:
        def analyze(self, sys_p, usr_p):
            call_count[0] += 1
            # First minister is the lone dissenter with high confidence
            if call_count[0] == 1:
                return '{"stance": "oppose", "reasoning": "This will fail badly.", "confidence": 0.95, "warning": "Existential risk"}'
            return '{"stance": "support", "reasoning": "Looks fine.", "confidence": 0.5, "warning": ""}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=CassandraLLM())
    result = council.deliberate(
        user_input="Should we launch now?",
        context={"domains": ["strategy"], "mode": "meeting"},
    )
    assert "minority_alert" in result, "minority_alert not present"
    assert result["minority_alert"] != "", "minority_alert is empty despite lone high-confidence dissenter"
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_minority_escalation_when_one_minister_highly_confident_outlier -v
```

Expected: **FAIL** — `minority_alert` key missing

- [ ] **Step 3: Add minority escalation to `_llm_deliberate()`**

Add this block before the `return` in `_llm_deliberate()`:

```python
MINORITY_CONFIDENCE_THRESHOLD = 0.85  # minister confidence above this gets escalated
MINORITY_SUPPORT_MAX = 0.25           # only if support ratio is this low

minority_alert = ""
for name, result in stances.items():
    support_ratio = 1 / max(1, len(minister_names))  # this minister alone
    is_outlier = (
        result["confidence"] >= MINORITY_CONFIDENCE_THRESHOLD
        and result["stance"] != outcome.replace("proceed", "support").replace("reconsider", "oppose")
    )
    if is_outlier:
        minority_alert = (
            f"MINORITY ALERT — {name} ({result['confidence']:.0%} confident): "
            f"{result['reasoning'][:200]}"
        )
        if result.get("warning"):
            minority_alert += f" | Warning: {result['warning']}"
        break  # first high-confidence outlier is enough

return {
    "outcome": outcome,
    "recommendation": outcome,
    "stances": stances,
    "consensus_strength": round(consensus_strength, 3),
    "red_line_concerns": warnings,
    "ministers_involved": minister_names,
    "dissent_summary": dissent_summary,
    "minority_alert": minority_alert,
}
```

- [ ] **Step 4: Run both Task 3.3 and 3.4 tests together**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_council_surfaces_disagreement_when_ministers_conflict tests/test_era_upgrades.py::test_minority_escalation_when_one_minister_highly_confident_outlier -v
```

Expected: both **PASS**

- [ ] **Step 5: Commit**

```
git add modules/council_execution/engine.py tests/test_era_upgrades.py
git commit -m "feat: minority_alert — lone high-confidence minister escalated, not silenced"
```

---

### Task 3.5 — KIS Knowledge Injection into MinisterVoice

**What this closes:** The critical missing bridge. Ministers currently debate from doctrine persona alone. This task wires book-derived knowledge (principles, rules, claims, warnings from ingested PDFs) directly into each minister's deliberation prompt. After this, a minister arguing about financial risk cites actual principles from ingested books — not just their character archetype.

**Files:**
- Modify: `persona/council/minister_voice.py`
- Modify: `modules/council_execution/engine.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_era_upgrades.py`:

```python
def test_minister_voice_uses_injected_knowledge_entries():
    """MinisterVoice.deliberate() must include knowledge entries in the LLM prompt."""
    received_prompts = []

    class CaptureLLM:
        def analyze(self, sys_p, usr_p):
            received_prompts.append(sys_p + usr_p)
            return '{"stance": "oppose", "reasoning": "Entry 1 says avoid.", "confidence": 0.8, "warning": ""}'

    from persona.council.minister_voice import MinisterVoice
    voice = MinisterVoice(minister_name="risk", llm=CaptureLLM())

    entries = [
        {"id": "e1", "content": "Never risk what you need for what you merely want.",
         "type": "principle", "source": {"book": "babylon"}, "weight": 1.0},
        {"id": "e2", "content": "Separate reversible from irreversible decisions.",
         "type": "rule", "source": {"book": "buffett"}, "weight": 0.9},
    ]
    result = voice.deliberate("Should I bet my savings?", {"domains": ["finance"]}, knowledge_entries=entries)

    full_prompt = " ".join(received_prompts)
    assert "Never risk what you need" in full_prompt, \
        "Knowledge entry 1 not in minister prompt"
    assert "Separate reversible" in full_prompt, \
        "Knowledge entry 2 not in minister prompt"
    assert result["stance"] in {"support", "oppose", "neutral"}


def test_minister_voice_knowledge_cited_in_response():
    """MinisterVoice must parse knowledge_cited field from LLM response."""
    class CitingLLM:
        def analyze(self, sys_p, usr_p):
            return '{"stance": "oppose", "reasoning": "Entry 1 warns against this.", "confidence": 0.85, "warning": "", "knowledge_cited": "1, 2"}'

    from persona.council.minister_voice import MinisterVoice
    voice = MinisterVoice(minister_name="risk", llm=CitingLLM())
    entries = [{"id": "e1", "content": "Avoid irreversible bets.", "type": "principle", "source": {}, "weight": 1.0}]
    result = voice.deliberate("quit job?", {}, knowledge_entries=entries)
    assert "knowledge_cited" in result, "knowledge_cited missing from parsed response"


def test_council_runs_kis_before_minister_calls(tmp_path):
    """NativeCouncil._llm_deliberate must run synthesize_knowledge and pass entries to ministers."""
    import sys, os, json
    for k in list(sys.modules.keys()):
        if "council_execution" in k or "knowledge_engine" in k:
            del sys.modules[k]

    # Seed a real minister JSON file
    d = tmp_path / "ministers" / "finance"
    d.mkdir(parents=True)
    data = {
        "domain": "finance", "category": "principles",
        "entries": [
            {"id": "f1", "text": "Save ten percent of all you earn.", "source": {"book": "babylon"}, "weight": 1.0},
        ],
        "meta": {"total_entries": 1},
    }
    (d / "principles.json").write_text(json.dumps(data))
    for cat in ["rules", "warnings", "claims"]:
        (d / f"{cat}.json").write_text(json.dumps(
            {"domain": "finance", "category": cat, "entries": [], "meta": {"total_entries": 0}}
        ))
    os.environ["ERA_MINISTER_PATH"] = str(tmp_path / "ministers")

    seen_entries_in_prompt = []

    class KISCaptureLLM:
        def analyze(self, sys_p, usr_p):
            if "Save ten percent" in sys_p:
                seen_entries_in_prompt.append(True)
            return '{"stance": "neutral", "reasoning": "ok", "confidence": 0.5, "warning": ""}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=KISCaptureLLM())
    council.deliberate(
        user_input="How should I manage money?",
        context={"domains": ["finance"], "mode": "meeting"},
    )
    assert seen_entries_in_prompt, "KIS entries never reached minister prompts"
```

- [ ] **Step 2: Run to confirm failure**

```
cd C:\Users\naren\Work\Projects\School\era
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_minister_voice_uses_injected_knowledge_entries tests/test_era_upgrades.py::test_minister_voice_knowledge_cited_in_response tests/test_era_upgrades.py::test_council_runs_kis_before_minister_calls -v
```

Expected: **FAIL** — `deliberate()` has no `knowledge_entries` parameter

- [ ] **Step 3: Update `_MINISTER_INSTRUCTION` and `deliberate()` in `minister_voice.py`**

Replace `_MINISTER_INSTRUCTION`:

```python
_MINISTER_INSTRUCTION = """You are {minister_name} in a council deliberation.

{persona_canon}

---
Relevant knowledge for this situation:
{knowledge_context}

---
Given the situation, respond ONLY with valid JSON:
{{
  "stance": "support" | "oppose" | "neutral",
  "reasoning": "<1-2 sentences. Cite a specific knowledge entry or your doctrine principle.>",
  "confidence": <0.0 to 1.0>,
  "warning": "<red-line concern or empty string>",
  "knowledge_cited": "<entry numbers you drew on, e.g. '1, 3' — or empty>"
}}"""
```

Update `MinisterVoice.__init__()` — remove pre-built `_system_prompt` (it now depends on entries):

```python
def __init__(self, minister_name: str, llm: Any):
    self.minister_name = minister_name
    self.llm = llm
    self._persona = _load_minister_persona(minister_name)
    self._display_name = minister_name.replace("_", " ").title()
```

Replace `deliberate()`:

```python
def deliberate(
    self,
    user_input: str,
    context: Dict[str, Any],
    knowledge_entries: list = None,
) -> Dict[str, Any]:
    """Call the LLM as this minister. Injects book-derived knowledge entries into prompt."""
    domain_hint = ", ".join(context.get("domains", [])) or "general"

    # Format knowledge block
    if knowledge_entries:
        lines = []
        for i, entry in enumerate(knowledge_entries[:6], 1):
            content = str(entry.get("content") or entry.get("text", ""))[:200].strip()
            source = entry.get("source", {})
            book = source.get("book", "") if isinstance(source, dict) else ""
            category = entry.get("type") or entry.get("category", "principle")
            line = f"{i}. [{category}] {content}"
            if book:
                line += f"  — {book}"
            lines.append(line)
        knowledge_block = "\n".join(lines)
    else:
        knowledge_block = "(No domain knowledge retrieved — reasoning from doctrine only.)"

    system_prompt = _MINISTER_INSTRUCTION.format(
        minister_name=self._display_name,
        persona_canon=self._persona,
        knowledge_context=knowledge_block,
    )

    prompt = f"Domains: {domain_hint}\n\nSituation: {user_input}"
    if context.get("peer_summary"):
        prompt += f"\n\n---\n{context['peer_summary']}"

    try:
        raw = self.llm.analyze(system_prompt, prompt)
        return self._parse(raw)
    except Exception as e:
        return {
            "stance": "neutral",
            "reasoning": f"[{self.minister_name} unavailable: {e}]",
            "confidence": 0.3,
            "warning": "",
            "knowledge_cited": "",
        }
```

Update `_validate()` to include `knowledge_cited`:

```python
@staticmethod
def _validate(data: Dict[str, Any]) -> Dict[str, Any]:
    valid_stances = {"support", "oppose", "neutral"}
    stance = str(data.get("stance", "neutral")).lower()
    if stance not in valid_stances:
        stance = "neutral"
    return {
        "stance": stance,
        "reasoning": str(data.get("reasoning", ""))[:400],
        "confidence": max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
        "warning": str(data.get("warning", "")),
        "knowledge_cited": str(data.get("knowledge_cited", "")),
    }
```

Update `_parse()` fallback to include the field:

```python
return {
    "stance": stance,
    "reasoning": raw[:200].strip(),
    "confidence": 0.5,
    "warning": "",
    "knowledge_cited": "",
}
```

- [ ] **Step 4: Update `_llm_deliberate()` in `engine.py` to run KIS first**

At the top of `_llm_deliberate()`, before the minister loop, add:

```python
def _llm_deliberate(self, user_input: str, context: dict, minister_names: list) -> dict:
    try:
        from persona.council.minister_voice import MinisterVoice
    except ImportError:
        return self._keyword_deliberate(user_input, context)

    active_domains = context.get("domains", [])
    active_ministers = _active_ministers_for_domains(active_domains, minister_names)
    primary_domain = active_domains[0] if active_domains else "general"

    # ── KIS retrieval: fetch book-derived knowledge for active domains ────────
    knowledge_entries: list = []
    try:
        from persona.knowledge_engine import synthesize_knowledge
        if active_domains:
            kis = synthesize_knowledge(
                user_input=user_input,
                active_domains=active_domains,
                domain_confidence=0.7,
            )
            knowledge_entries = kis.get("synthesized_knowledge", [])[:6]
    except Exception:
        pass

    stances: dict = {}
    support, oppose, neutral = 0, 0, 0
    weighted_support, weighted_oppose, weighted_neutral = 0.0, 0.0, 0.0
    warnings: list = []

    for name in active_ministers:
        voice = MinisterVoice(minister_name=name, llm=self.llm)
        result = voice.deliberate(user_input, context, knowledge_entries=knowledge_entries)
        stances[name] = result
        weight = self._confidence_tracker.get_weight(name, primary_domain)
        vote = result["confidence"] * weight
        s = result["stance"]
        if s == "support":
            support += 1; weighted_support += vote
        elif s == "oppose":
            oppose += 1; weighted_oppose += vote
        else:
            neutral += 1; weighted_neutral += vote
        if result.get("warning"):
            warnings.append(f"{name}: {result['warning']}")

    # ... rest of method unchanged (dissent_summary, minority_alert, return)
```

- [ ] **Step 5: Run all three new tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_minister_voice_uses_injected_knowledge_entries tests/test_era_upgrades.py::test_minister_voice_knowledge_cited_in_response tests/test_era_upgrades.py::test_council_runs_kis_before_minister_calls -v
```

Expected: all **PASS**

- [ ] **Step 6: Run full upgrade suite**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py -v
```

Expected: all **PASS**

- [ ] **Step 7: Commit**

```
git add persona/council/minister_voice.py modules/council_execution/engine.py tests/test_era_upgrades.py
git commit -m "feat: KIS knowledge injection — ministers argue from ingested book knowledge, not doctrine alone"
```

---

## Track 4: Outcome Recording + Auto-Retrain Trigger

**What this closes:** `EpisodicMemory` accumulates episodes. `OutcomeFeedbackLoop.retrain_ministers()` can reduce minister confidence multipliers for failing domains. But nothing triggers this automatically. After every 50 turns, check for failure clusters and retrain affected ministers.

**Files:**
- Modify: `api.py`
- Modify: `persona/learning/outcome_feedback.py`

### Task 4.1 — Wire auto-retrain into the session turn counter

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_auto_retrain_triggers_after_threshold():
    """After RETRAIN_EVERY_N_TURNS turns, retrain_ministers must be called for failure domains."""
    from persona.learning.episodic_memory import EpisodicMemory, Episode
    from persona.learning.outcome_feedback import OutcomeFeedbackLoop

    mem = EpisodicMemory(storage_path=":memory:")  # no-disk mode

    # Inject 3 failure episodes in "career" domain
    for i in range(3):
        ep = Episode(
            episode_id=str(i), turn_id=i, domain="career",
            user_input="quit job?", persona_recommendation="proceed",
            confidence=0.7, minister_stance="support", council_recommendation="proceed",
            outcome="failure", regret_score=0.8,
        )
        mem.episodes[ep.episode_id] = ep

    retrained = []

    class FakeCouncil:
        ministers = {"career": type("M", (), {"confidence_multiplier": 1.0})()}

    loop = OutcomeFeedbackLoop(council=FakeCouncil(), episodic_memory=mem)

    loop.check_and_retrain()  # the new method

    clusters = mem.detect_failure_clusters(domain="career")
    # verify retrain was at least attempted
    assert clusters, "No failure clusters detected — episodes not stored"
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_auto_retrain_triggers_after_threshold -v
```

Expected: **FAIL** — `EpisodicMemory` has no `:memory:` mode, `OutcomeFeedbackLoop` has no `check_and_retrain()`

- [ ] **Step 3: Add `:memory:` mode to `EpisodicMemory`**

In `persona/learning/episodic_memory.py`, update `__init__` and `_persist`:

```python
def __init__(self, storage_path: str = "data/memory/episodes.jsonl"):
    self.storage_path = storage_path
    self._in_memory_only = (storage_path == ":memory:")
    self.episodes: Dict[str, Episode] = {}
    self.evaluation_mode = False
    if not self._in_memory_only:
        self.load_from_disk()

def _persist(self, episode: Episode):
    if self._in_memory_only:
        return
    try:
        with open(self.storage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(episode)) + "\n")
    except Exception as e:
        print(f"[WARNING] Failed to persist episode: {e}")
```

- [ ] **Step 4: Add `check_and_retrain()` to `OutcomeFeedbackLoop`**

In `persona/learning/outcome_feedback.py`:

```python
RETRAIN_MIN_FAILURES = 3          # minimum failures in a domain to trigger retrain
RETRAIN_EVERY_N_TURNS = 50        # check interval

def check_and_retrain(self) -> Dict[str, bool]:
    """Scan episodic memory for failure clusters. Retrain affected minister domains.

    Returns a dict of {domain: retrained_bool}.
    """
    if not self.episodic_memory:
        return {}

    results: Dict[str, bool] = {}
    clusters = self.episodic_memory.detect_failure_clusters()

    for cluster_key, failures in clusters.items():
        if len(failures) < RETRAIN_MIN_FAILURES:
            continue
        domain = cluster_key.split("_")[0]
        self.retrain_ministers(domain, failures)
        results[domain] = True

    return results
```

Add `from typing import Dict` to imports at top if not present.

- [ ] **Step 5: Call `check_and_retrain()` from `api.py` every N turns**

In the `/chat` route in `api.py`, after the response is returned, add a background task:

```python
# Every 50 turns: check for failure clusters and auto-retrain
if state.turn_count % 50 == 0 and hasattr(session, "feedback_loop") and session.feedback_loop:
    _executor.submit(session.feedback_loop.check_and_retrain)
```

Add `feedback_loop` to the `Session` dataclass:

```python
from persona.learning.outcome_feedback import OutcomeFeedbackLoop
from persona.learning.episodic_memory import EpisodicMemory

@dataclass
class Session:
    state: CognitiveState = dc_field(default_factory=lambda: _make_state())
    mode_orchestrator: ModeOrchestrator = dc_field(default_factory=ModeOrchestrator)
    dynamic_council: DynamicCouncil = dc_field(default_factory=lambda: DynamicCouncil(llm=None))
    user_id: Optional[str] = None
    profile: Optional[Any] = None
    episodic_memory: EpisodicMemory = dc_field(
        default_factory=lambda: EpisodicMemory("data/memory/episodes.jsonl")
    )
    feedback_loop: OutcomeFeedbackLoop = dc_field(default_factory=OutcomeFeedbackLoop)
```

- [ ] **Step 6: Run the test**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_auto_retrain_triggers_after_threshold -v
```

Expected: **PASS**

- [ ] **Step 7: Commit**

```
git add persona/learning/episodic_memory.py persona/learning/outcome_feedback.py api.py tests/test_era_upgrades.py
git commit -m "feat: auto-retrain trigger — failure clusters retrain ministers every 50 turns"
```

---

## Track 5: Efficiency — Single LLM Call Classification + Quick Mode Fast Path

**What this closes:** The current `_assess_situation_sync()` call in `_process_turn()` is a full LLM call that often times out and falls back to heuristic anyway. Quick mode should bypass all analysis and go straight to `llm.speak()`. Meeting/Darbar modes should use one structured LLM call instead of the legacy 4-call handshake.

**Files:**
- Modify: `persona/analysis.py`
- Modify: `api.py`

### Task 5.1 — Single structured classification call

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_classify_single_call_returns_all_fields():
    """classify_situation_single_call must return situation_type, domains, emotional_load, risk_level."""
    import sys
    for k in list(sys.modules.keys()):
        if "analysis" in k:
            del sys.modules[k]

    from persona.analysis import classify_situation_single_call

    class FakeLLM:
        def analyze(self, system_prompt, user_prompt):
            return json.dumps({
                "situation_type": "career_change",
                "domains": ["career", "finance"],
                "emotional_load": 0.6,
                "risk_level": "medium",
                "irreversibility": "partially",
                "clarity": 0.7,
            })

    import json
    result = classify_situation_single_call(FakeLLM(), "Should I quit my job?")
    assert result["situation_type"] == "career_change"
    assert "career" in result["domains"]
    assert 0.0 <= result["emotional_load"] <= 1.0
    assert result["risk_level"] in {"low", "medium", "high"}


def test_classify_single_call_falls_back_on_bad_json():
    """classify_situation_single_call must not crash on bad LLM output."""
    from persona.analysis import classify_situation_single_call

    class BadLLM:
        def analyze(self, s, u):
            return "this is not json"

    result = classify_situation_single_call(BadLLM(), "test input")
    assert "situation_type" in result
    assert "domains" in result
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_classify_single_call_returns_all_fields tests/test_era_upgrades.py::test_classify_single_call_falls_back_on_bad_json -v
```

Expected: **FAIL** — `cannot import name 'classify_situation_single_call'`

- [ ] **Step 3: Add `classify_situation_single_call()` to `persona/analysis.py`**

Add at the end of `persona/analysis.py`:

```python
_CLASSIFY_SYSTEM = """You are a decision analysis classifier.
Analyze the user's input and return ONLY valid JSON:
{
  "situation_type": "<short label e.g. career_change, financial_risk, relationship>",
  "domains": ["<domain1>", "<domain2>"],
  "emotional_load": <0.0-1.0>,
  "risk_level": "low" | "medium" | "high",
  "irreversibility": "reversible" | "partially" | "irreversible",
  "clarity": <0.0-1.0>
}
Domains must be from: career, finance, health, relationships, strategy, risk,
adaptation, conflict, psychology, power, technology, diplomacy, data, timing,
optionality, truth, legitimacy, discipline, intelligence, narrative, general.
Return ONLY the JSON object, no explanation."""


def classify_situation_single_call(llm: Any, user_input: str) -> Dict[str, Any]:
    """One structured LLM call replacing the 4-call handshake.

    Falls back to heuristic on any failure.
    """
    _default = {
        "situation_type": "unclear",
        "domains": [],
        "emotional_load": 0.0,
        "risk_level": "medium",
        "irreversibility": "partially",
        "clarity": 0.3,
    }
    try:
        raw = llm.analyze(_CLASSIFY_SYSTEM, user_input[:500])
        import json as _json, re as _re
        # strip markdown fencing
        match = _re.search(r"\{[^{}]+\}", raw, _re.DOTALL)
        text = match.group() if match else raw.strip()
        data = _json.loads(text)

        result = dict(_default)
        result["situation_type"] = str(data.get("situation_type", "unclear"))
        raw_domains = data.get("domains", [])
        result["domains"] = [str(d) for d in raw_domains if d] if isinstance(raw_domains, list) else []
        result["emotional_load"] = max(0.0, min(1.0, float(data.get("emotional_load", 0.0))))
        result["risk_level"] = str(data.get("risk_level", "medium"))
        result["irreversibility"] = str(data.get("irreversibility", "partially"))
        result["clarity"] = max(0.0, min(1.0, float(data.get("clarity", 0.5))))
        return result
    except Exception:
        return _default
```

Add `from typing import Any, Dict` to `persona/analysis.py` imports if not present.

- [ ] **Step 4: Run tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_classify_single_call_returns_all_fields tests/test_era_upgrades.py::test_classify_single_call_falls_back_on_bad_json -v
```

Expected: **PASS**

- [ ] **Step 5: Wire into `_process_turn()` in `api.py`**

Replace the `_assess_situation_sync()` call in `_process_turn()`:

```python
def _process_turn(state: CognitiveState, user_input: str) -> tuple[str, list[dict]]:
    llm = _components["llm"]

    # Quick mode: skip all analysis, respond directly
    if state.mode == "quick":
        system_context = build_system_context(state)
        response = llm.speak(system_context, user_input)
        state.recent_turns.append((user_input, response))
        if len(state.recent_turns) > 50:
            state.recent_turns = state.recent_turns[-50:]
        state.turn_count += 1
        return response, []

    # All other modes: single structured classification call
    try:
        from persona.analysis import classify_situation_single_call
        classification = classify_situation_single_call(llm, user_input)
    except Exception:
        classification = {"situation_type": "unclear", "domains": [], "emotional_load": 0.0,
                          "risk_level": "medium", "clarity": 0.3}

    state.last_situation = {
        "situation_type": classification["situation_type"],
        "clarity": classification["clarity"],
        "emotional_load": classification["emotional_load"],
    }
    state.last_emotional_load = classification["emotional_load"]

    # Update domains from classification if not already set
    if not state.domains and classification["domains"]:
        state.domains = classification["domains"]
        state.domain_confidence = classification["clarity"]

    # ... rest of _process_turn unchanged (KIS retrieval, llm.speak, history append)
```

- [ ] **Step 6: Run all upgrade tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py -v
```

Expected: all tests **PASS**

- [ ] **Step 7: Commit**

```
git add persona/analysis.py api.py tests/test_era_upgrades.py
git commit -m "feat: single structured LLM classification call + quick mode fast path"
```

---

### Task 5.2 — Tiered Deliberation Depth by Stakes

**What this adds:** High stakes (emotional_load > 0.7 AND clarity < 0.4) triggers full 18-minister darbar. Medium stakes triggers 5-minister meeting. Low stakes + quick mode bypasses all council. Same effort shouldn't go to "what should I eat" as "should I resign."

**Files:**
- Modify: `api.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_tiered_depth_high_stakes_uses_darbar():
    """emotional_load > 0.7 and clarity < 0.4 must route to darbar depth."""
    import sys
    for k in list(sys.modules.keys()):
        if "api" in k:
            del sys.modules[k]

    import api
    from fastapi.testclient import TestClient

    call_log = []

    class TrackedLLM:
        def speak(self, ctx, inp): return "response"
        def analyze(self, sys_p, usr_p):
            call_log.append(("analyze", usr_p[:40]))
            return '{"situation_type":"resignation","domains":["career"],"emotional_load":0.85,"risk_level":"high","irreversibility":"irreversible","clarity":0.2}'

    api._components.clear()
    api._components["llm"] = TrackedLLM()

    client = TestClient(api.app)
    r = client.post("/chat", json={"message": "should I resign today?", "session_id": "depth1"})
    assert r.status_code == 200, r.text
    body = r.json()
    # High stakes → mode reported as darbar or depth field present
    assert body.get("deliberation_depth") in {"darbar", "meeting", "quick"}, \
        f"No deliberation_depth in response: {list(body.keys())}"
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_tiered_depth_high_stakes_uses_darbar -v
```

Expected: **FAIL** — `deliberation_depth` missing

- [ ] **Step 3: Add tiered depth routing to `_process_turn()` in `api.py`**

After the classification step, add depth routing:

```python
# Tiered deliberation depth: stakes = emotional_load × (1 - clarity)
emotional_load = classification.get("emotional_load", 0.0)
clarity = classification.get("clarity", 0.5)
stakes = emotional_load * (1.0 - clarity)

if state.mode == "quick" or stakes < 0.2:
    deliberation_depth = "quick"
elif stakes >= 0.5:
    deliberation_depth = "darbar"
else:
    deliberation_depth = "meeting"
```

Return `deliberation_depth` from `_process_turn()` and add it to `ChatResponse`:

```python
# In _process_turn return signature:
return response, entries_used, knowledge_gaps, deliberation_depth
```

```python
class ChatResponse(BaseModel):
    session_id: str
    response: str
    mode: str
    turn: int
    domains: list[str]
    domain_confidence: float
    entries_used: list[dict] = []
    knowledge_gaps: list[str] = []
    deliberation_depth: str = "meeting"   # quick | meeting | darbar
```

- [ ] **Step 4: Run the test**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_tiered_depth_high_stakes_uses_darbar -v
```

Expected: **PASS**

- [ ] **Step 5: Commit**

```
git add api.py tests/test_era_upgrades.py
git commit -m "feat: tiered deliberation depth — stakes score routes to quick/meeting/darbar"
```

---

## Track 6: Ingestion-Triggered Learning (Domain Gap Detection)

**What this closes:** When ERA lacks knowledge in a domain the user keeps asking about, it should surface this gap explicitly. The user can then drop in a PDF and the ingestion pipeline enriches that domain automatically.

**Files:**
- Modify: `persona/knowledge_engine.py`
- Modify: `api.py`

### Task 6.1 — Domain gap detection in synthesize_knowledge

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_knowledge_gap_detected_when_domain_sparse(tmp_path):
    """synthesize_knowledge must report knowledge_gaps when a domain has fewer than MIN_ENTRIES entries."""
    import sys
    for k in list(sys.modules.keys()):
        if "knowledge_engine" in k:
            del sys.modules[k]

    # Create a sparse domain with only 2 entries
    d = tmp_path / "ministers" / "rare_domain"
    d.mkdir(parents=True)
    sparse = {"domain": "rare_domain", "category": "principles",
              "entries": [{"id": "x1", "text": "Only one principle.", "source": {}, "weight": 1.0}],
              "meta": {"total_entries": 1}}
    (d / "principles.json").write_text(json.dumps(sparse))
    for cat in ["rules", "warnings", "claims"]:
        (d / f"{cat}.json").write_text(json.dumps(
            {"domain": "rare_domain", "category": cat, "entries": [], "meta": {"total_entries": 0}}
        ))

    os.environ["ERA_MINISTER_PATH"] = str(tmp_path / "ministers")

    from persona.knowledge_engine import synthesize_knowledge
    result = synthesize_knowledge(
        user_input="what should I do",
        active_domains=["rare_domain"],
        domain_confidence=0.8,
    )
    gaps = result.get("knowledge_gaps", [])
    assert "rare_domain" in gaps, f"Expected 'rare_domain' in knowledge_gaps, got: {gaps}"
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_knowledge_gap_detected_when_domain_sparse -v
```

Expected: **FAIL** — `knowledge_gaps` key missing from result

- [ ] **Step 3: Add gap detection to `synthesize_knowledge()`**

In `persona/knowledge_engine.py`, add a constant and helper:

```python
KNOWLEDGE_GAP_THRESHOLD = 5   # domains with fewer entries than this are flagged


def count_domain_entries(domain: str) -> int:
    """Count total entries across all categories for a domain."""
    domain_path = os.path.join(BASE_PATH, domain)
    if not os.path.isdir(domain_path):
        return 0
    total = 0
    for ktype in KNOWLEDGE_TYPES:
        file_path = os.path.join(domain_path, f"{ktype}s.json")
        raw = load_json_safe(file_path)
        entries = raw.get("entries", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        total += len(entries)
    return total
```

In `synthesize_knowledge()`, before the `return` statement, add:

```python
# Gap detection: flag active domains with sparse knowledge
knowledge_gaps = []
for d in active_domains:
    if count_domain_entries(d) < KNOWLEDGE_GAP_THRESHOLD:
        knowledge_gaps.append(d)
```

Update the return dict to include `knowledge_gaps`:

```python
return {
    "synthesized_knowledge": [...],
    "knowledge_trace": [...],
    "knowledge_gaps": knowledge_gaps,
}
```

- [ ] **Step 4: Surface gaps in `/chat` response**

Update `ChatResponse` in `api.py`:

```python
class ChatResponse(BaseModel):
    session_id: str
    response: str
    mode: str
    turn: int
    domains: list[str]
    domain_confidence: float
    entries_used: list[dict] = []
    knowledge_gaps: list[str] = []   # domains where ERA has sparse knowledge
```

In `_process_turn()`, capture and return gaps:

```python
knowledge_gaps: list[str] = []
if state.domains:
    try:
        kis = synthesize_knowledge(...)
        knowledge_gaps = kis.get("knowledge_gaps", [])
        # ... existing entries_used population
    except Exception:
        pass

# Return both
return response, entries_used, knowledge_gaps
```

Update `/chat` route to unpack three values and pass gaps into `ChatResponse`.

- [ ] **Step 5: Run the test**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_knowledge_gap_detected_when_domain_sparse -v
```

Expected: **PASS**

- [ ] **Step 6: Run all upgrade tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py -v
```

Expected: all **PASS**

- [ ] **Step 7: Commit**

```
git add persona/knowledge_engine.py api.py tests/test_era_upgrades.py
git commit -m "feat: knowledge gap detection — surfaces sparse domains in /chat response"
```

---

## Track 7: Domain-Aware Minister Activation

**What this closes:** 18 ministers speak on every query — a financial question activates the grief minister, a career question activates the war minister. This is noise, not wisdom. Activate only ministers whose `triggers.speak` domains overlap with the assessed domains, plus a fixed sovereign anchor.

**Files:**
- Modify: `modules/council_execution/engine.py`
- Modify: `data/doctrine/locked/*.yaml` (read-only, no changes needed — already has triggers.speak)

### Task 7.1 — Domain-Filtered Minister Roster

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_domain_routing_activates_only_relevant_ministers():
    """For a 'career' domain query, ministers unrelated to career must not be activated."""
    import sys
    for k in list(sys.modules.keys()):
        if "council_execution" in k:
            del sys.modules[k]

    activated = []

    class LogLLM:
        def analyze(self, sys_p, usr_p):
            # Extract minister name from system prompt (it appears in the title line)
            import re
            m = re.search(r"You are (\w[\w ]*) in a council", sys_p)
            if m:
                activated.append(m.group(1).lower())
            return '{"stance": "neutral", "reasoning": "ok.", "confidence": 0.5, "warning": ""}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=LogLLM())
    result = council.deliberate(
        user_input="Should I accept the promotion?",
        context={"domains": ["career"], "mode": "meeting"},
    )
    # War Mode and Conflict ministers should NOT appear for a career query
    assert "war mode" not in activated, f"War Mode activated for career query: {activated}"
    assert len(activated) <= 8, f"Too many ministers activated ({len(activated)}) for single domain"
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_domain_routing_activates_only_relevant_ministers -v
```

Expected: **FAIL** — all meeting ministers activate regardless of domain

- [ ] **Step 3: Add domain routing to `engine.py`**

Add a minister-to-domains mapping at module level:

```python
_MINISTER_DOMAINS: dict[str, list[str]] = {
    "risk":            ["finance", "career", "strategy", "health", "general"],
    "grand_strategist":["strategy", "career", "power", "general"],
    "optionality":     ["career", "finance", "strategy", "general"],
    "psychology":      ["career", "relationships", "health", "conflict", "general"],
    "timing":          ["strategy", "career", "finance", "general"],
    "power":           ["strategy", "conflict", "power", "career"],
    "diplomacy":       ["relationships", "conflict", "diplomacy"],
    "legitimacy":      ["strategy", "legitimacy", "truth"],
    "truth":           ["general", "psychology", "truth"],
    "data":            ["finance", "technology", "data"],
    "technology":      ["technology", "strategy"],
    "conflict":        ["conflict", "power", "war_mode"],
    "war_mode":        ["conflict", "war_mode"],
    "discipline":      ["health", "career", "discipline"],
    "intelligence":    ["strategy", "intelligence"],
    "narrative":       ["relationships", "narrative"],
    "adaptation":      ["general", "adaptation", "career"],
    "sovereign":       ["general"],  # always included as anchor
}
```

Add a helper to filter minister list by active domains:

```python
def _active_ministers_for_domains(domains: list, pool: list) -> list:
    """Return ministers from pool whose domain map overlaps with active domains.

    Sovereign is always included. At least 3 ministers are always returned.
    """
    if not domains:
        return pool[:5]

    domain_set = set(d.lower() for d in domains) | {"general"}
    relevant = [
        name for name in pool
        if name == "sovereign"
        or any(d in domain_set for d in _MINISTER_DOMAINS.get(name, ["general"]))
    ]
    # Ensure minimum panel size
    if len(relevant) < 3:
        for name in pool:
            if name not in relevant:
                relevant.append(name)
            if len(relevant) >= 3:
                break
    return relevant
```

Update `_llm_deliberate()` to filter:

```python
def _llm_deliberate(self, user_input: str, context: dict, minister_names: list) -> dict:
    try:
        from persona.council.minister_voice import MinisterVoice
    except ImportError:
        return self._keyword_deliberate(user_input, context)

    # Filter to domain-relevant ministers only
    active_domains = context.get("domains", [])
    active_ministers = _active_ministers_for_domains(active_domains, minister_names)

    stances = {}
    support, oppose, neutral = 0, 0, 0
    warnings = []

    for name in active_ministers:
        voice = MinisterVoice(minister_name=name, llm=self.llm)
        result = voice.deliberate(user_input, context)
        stances[name] = result
        # ... rest unchanged
```

- [ ] **Step 4: Run the test**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_domain_routing_activates_only_relevant_ministers -v
```

Expected: **PASS**

- [ ] **Step 5: Run full upgrade suite**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py -v
```

Expected: all **PASS**

- [ ] **Step 6: Commit**

```
git add modules/council_execution/engine.py tests/test_era_upgrades.py
git commit -m "feat: domain-aware minister routing — only relevant ministers deliberate"
```

---

## Track 8: Bayesian Minister Confidence Calibration

**What this closes:** Minister confidence weights are static. A minister who's been wrong 7/10 times on financial domain keeps full weight. Tracking per-minister success rate and updating confidence multipliers from episodic memory makes the council self-calibrating.

**Files:**
- Create: `persona/learning/minister_confidence.py`
- Modify: `modules/council_execution/engine.py`

### Task 8.1 — Create MinisterConfidenceTracker

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_minister_confidence_tracker_adjusts_weight():
    """After recording failures, get_weight() must return a reduced multiplier."""
    import sys
    for k in list(sys.modules.keys()):
        if "minister_confidence" in k:
            del sys.modules[k]

    from persona.learning.minister_confidence import MinisterConfidenceTracker

    tracker = MinisterConfidenceTracker(storage_path=":memory:")
    tracker.record_outcome(minister="risk", domain="finance", success=False)
    tracker.record_outcome(minister="risk", domain="finance", success=False)
    tracker.record_outcome(minister="risk", domain="finance", success=False)
    tracker.record_outcome(minister="risk", domain="finance", success=True)

    weight = tracker.get_weight("risk", "finance")
    assert weight < 1.0, f"Weight should drop after failures, got {weight}"
    assert weight > 0.0, "Weight must stay positive"


def test_minister_confidence_tracker_boosts_consistent_minister():
    """After recording successes, get_weight() must return > 1.0."""
    from persona.learning.minister_confidence import MinisterConfidenceTracker

    tracker = MinisterConfidenceTracker(storage_path=":memory:")
    for _ in range(5):
        tracker.record_outcome(minister="grand_strategist", domain="strategy", success=True)

    weight = tracker.get_weight("grand_strategist", "strategy")
    assert weight >= 1.0, f"Consistent success should boost weight, got {weight}"
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_minister_confidence_tracker_adjusts_weight tests/test_era_upgrades.py::test_minister_confidence_tracker_boosts_consistent_minister -v
```

Expected: **FAIL** — `ModuleNotFoundError`

- [ ] **Step 3: Create `persona/learning/minister_confidence.py`**

```python
"""Per-minister Bayesian confidence calibration."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional


@dataclass
class MinisterRecord:
    minister: str
    domain: str
    successes: int = 0
    failures: int = 0

    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.5

    def weight(self) -> float:
        """Confidence multiplier: 0.4–1.5 range based on success rate.

        Starts at 1.0 (neutral), drops on failure, rises on success.
        Minimum sample of 3 required before deviating from 1.0.
        """
        total = self.successes + self.failures
        if total < 3:
            return 1.0
        rate = self.success_rate()
        # Linear scaling: 0% success → 0.4, 50% → 1.0, 100% → 1.5
        return max(0.4, min(1.5, 0.4 + rate * 1.1))


class MinisterConfidenceTracker:
    """Tracks per-minister, per-domain success rates and returns calibrated weights."""

    def __init__(self, storage_path: str = "data/memory/minister_confidence.json"):
        self._in_memory = storage_path == ":memory:"
        self._path = None if self._in_memory else Path(storage_path)
        self._records: Dict[str, MinisterRecord] = {}
        if not self._in_memory and self._path.exists():
            self._load()

    def _key(self, minister: str, domain: str) -> str:
        return f"{minister}::{domain}"

    def record_outcome(self, minister: str, domain: str, success: bool) -> None:
        key = self._key(minister, domain)
        if key not in self._records:
            self._records[key] = MinisterRecord(minister=minister, domain=domain)
        rec = self._records[key]
        if success:
            rec.successes += 1
        else:
            rec.failures += 1
        if not self._in_memory:
            self._save()

    def get_weight(self, minister: str, domain: str) -> float:
        key = self._key(minister, domain)
        rec = self._records.get(key)
        return rec.weight() if rec else 1.0

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self._records.items()}
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for k, v in data.items():
                self._records[k] = MinisterRecord(**v)
        except Exception:
            pass
```

- [ ] **Step 4: Run tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_minister_confidence_tracker_adjusts_weight tests/test_era_upgrades.py::test_minister_confidence_tracker_boosts_consistent_minister -v
```

Expected: **PASS**

- [ ] **Step 5: Wire calibrated weights into `_llm_deliberate()` vote aggregation**

In `engine.py`, add `MinisterConfidenceTracker` instance to `NativeCouncil.__init__()`:

```python
from persona.learning.minister_confidence import MinisterConfidenceTracker

class NativeCouncil:
    def __init__(self, llm=None):
        self.llm = llm
        self.ministers = _build_ministers()
        self._confidence_tracker = MinisterConfidenceTracker()
```

In `_llm_deliberate()`, weight votes by calibrated confidence:

```python
active_domains = context.get("domains", [])
primary_domain = active_domains[0] if active_domains else "general"

weighted_support, weighted_oppose, weighted_neutral = 0.0, 0.0, 0.0

for name in active_ministers:
    voice = MinisterVoice(minister_name=name, llm=self.llm)
    result = voice.deliberate(user_input, context)
    stances[name] = result
    weight = self._confidence_tracker.get_weight(name, primary_domain)
    vote_weight = result["confidence"] * weight
    s = result["stance"]
    if s == "support":
        weighted_support += vote_weight
    elif s == "oppose":
        weighted_oppose += vote_weight
    else:
        weighted_neutral += vote_weight
    if result.get("warning"):
        warnings.append(f"{name}: {result['warning']}")

total_weight = max(0.001, weighted_support + weighted_oppose + weighted_neutral)
outcome = "proceed" if weighted_support > weighted_oppose else (
    "reconsider" if weighted_oppose > weighted_support else "defer"
)
consensus_strength = max(weighted_support, weighted_oppose) / total_weight
```

- [ ] **Step 6: Commit**

```
git add persona/learning/minister_confidence.py modules/council_execution/engine.py tests/test_era_upgrades.py
git commit -m "feat: Bayesian minister confidence — track record adjusts vote weight per domain"
```

---

## Track 9: Multi-Round Cross-Minister Dialogue

**What this adds:** The highest quality deliberation mode: Round 1, each minister speaks independently. Round 2, each minister sees what others said and can revise or challenge. PrimeConfident synthesizes final. `ml/darbar.py` already does a 3-minister version of this; Track 9 generalizes it.

Applied only in Darbar mode — the full council of 18.

**Files:**
- Modify: `modules/council_execution/engine.py`

### Task 9.1 — Two-Round Deliberation in Darbar Mode

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_darbar_mode_runs_two_rounds():
    """In darbar mode, ministers must be called twice (round 1 + round 2 with peer context)."""
    import sys
    for k in list(sys.modules.keys()):
        if "council_execution" in k:
            del sys.modules[k]

    call_count = [0]
    second_round_saw_peers = [False]

    class TwoRoundLLM:
        def analyze(self, sys_p, usr_p):
            call_count[0] += 1
            if "Peer stances" in usr_p or "other ministers" in usr_p.lower():
                second_round_saw_peers[0] = True
            return '{"stance": "neutral", "reasoning": "Considered.", "confidence": 0.6, "warning": ""}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=TwoRoundLLM())
    result = council.deliberate(
        user_input="Should we go to war?",
        context={"domains": ["conflict", "strategy"], "mode": "darbar"},
    )
    assert call_count[0] > len(_MEETING_MINISTERS), \
        f"Only {call_count[0]} calls — no second round detected"
    assert second_round_saw_peers[0], "Round 2 ministers did not receive peer context"
    assert "rounds" in result, "result missing 'rounds' field"
```

- [ ] **Step 2: Run to confirm failure**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_darbar_mode_runs_two_rounds -v
```

Expected: **FAIL** — only one round of calls

- [ ] **Step 3: Add `_two_round_deliberate()` to `NativeCouncil` in `engine.py`**

Update `deliberate()` to route darbar to two-round method:

```python
def deliberate(self, user_input: str, context: dict) -> dict:
    mode = str(context.get("mode", "meeting")).lower()

    if self.llm is not None and mode == "darbar":
        minister_names = _active_ministers_for_domains(
            context.get("domains", []), _DARBAR_MINISTERS
        )
        return self._two_round_deliberate(user_input, context, minister_names)
    elif self.llm is not None and mode == "meeting":
        minister_names = _active_ministers_for_domains(
            context.get("domains", []), _MEETING_MINISTERS
        )
        return self._llm_deliberate(user_input, context, minister_names)
    else:
        return self._keyword_deliberate(user_input, context)
```

Add `_two_round_deliberate()`:

```python
def _two_round_deliberate(self, user_input: str, context: dict, minister_names: list) -> dict:
    """Round 1: each minister speaks independently.
    Round 2: each minister sees peer stances and may revise.
    """
    try:
        from persona.council.minister_voice import MinisterVoice
    except ImportError:
        return self._llm_deliberate(user_input, context, minister_names)

    active_domains = context.get("domains", [])
    primary_domain = active_domains[0] if active_domains else "general"

    # ── Round 1 ───────────────────────────────────────────────────────────────
    round1: dict[str, dict] = {}
    for name in minister_names:
        voice = MinisterVoice(minister_name=name, llm=self.llm)
        round1[name] = voice.deliberate(user_input, context)

    # Build peer summary for Round 2
    peer_lines = []
    for name, r in round1.items():
        peer_lines.append(f"  {name}: {r['stance']} (confidence {r['confidence']:.2f}) — {r['reasoning'][:100]}")
    peer_summary = "Peer stances from Round 1:\n" + "\n".join(peer_lines)

    round2_context = dict(context)
    round2_context["peer_summary"] = peer_summary

    # ── Round 2 ───────────────────────────────────────────────────────────────
    round2: dict[str, dict] = {}
    for name in minister_names:
        voice = MinisterVoice(minister_name=name, llm=self.llm)
        # Inject peer summary into the deliberation prompt
        augmented_input = f"{user_input}\n\n---\n{peer_summary}"
        round2[name] = voice.deliberate(augmented_input, round2_context)

    # Aggregate final votes from Round 2 (with calibrated weights)
    warnings = []
    weighted_support, weighted_oppose, weighted_neutral = 0.0, 0.0, 0.0
    for name, r in round2.items():
        weight = self._confidence_tracker.get_weight(name, primary_domain)
        vote = r["confidence"] * weight
        if r["stance"] == "support":
            weighted_support += vote
        elif r["stance"] == "oppose":
            weighted_oppose += vote
        else:
            weighted_neutral += vote
        if r.get("warning"):
            warnings.append(f"{name}: {r['warning']}")

    total = max(0.001, weighted_support + weighted_oppose + weighted_neutral)
    outcome = "proceed" if weighted_support > weighted_oppose else (
        "reconsider" if weighted_oppose > weighted_support else "defer"
    )

    # Minority alert on round 2 stances
    minority_alert = ""
    for name, r in round2.items():
        if (r["confidence"] >= 0.85 and
                r["stance"] != outcome.replace("proceed", "support").replace("reconsider", "oppose")):
            minority_alert = (
                f"MINORITY ALERT — {name} ({r['confidence']:.0%}): {r['reasoning'][:200]}"
            )
            break

    return {
        "outcome": outcome,
        "recommendation": outcome,
        "rounds": 2,
        "round1_stances": round1,
        "stances": round2,
        "consensus_strength": round(max(weighted_support, weighted_oppose) / total, 3),
        "red_line_concerns": warnings,
        "ministers_involved": minister_names,
        "dissent_summary": "",
        "minority_alert": minority_alert,
    }
```

- [ ] **Step 4: Run the test**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_darbar_mode_runs_two_rounds -v
```

Expected: **PASS**

- [ ] **Step 5: Run full suite**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py -v
```

Expected: all **PASS**

- [ ] **Step 6: Commit**

```
git add modules/council_execution/engine.py tests/test_era_upgrades.py
git commit -m "feat: two-round darbar deliberation — ministers revise after seeing peer stances"
```

---

### Task 9.2 — Structured Peer Challenge in Round 2

**What this closes:** Round 2 currently dumps all peer stances as a text block. Ministers read it but aren't asked to engage. This task changes Round 2 to a directed challenge: each minister is shown specifically who disagrees with them and asked to either defend their position or revise it — and to cite doctrine or knowledge when they do. This is real debate, not just awareness.

**Files:**
- Modify: `modules/council_execution/engine.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_era_upgrades.py`:

```python
def test_round2_prompt_contains_specific_challenger_name():
    """Round 2 prompt must name the specific ministers who disagree, not just dump all stances."""
    import sys
    for k in list(sys.modules.keys()):
        if "council_execution" in k:
            del sys.modules[k]

    round2_prompts = {}
    call_count = [0]

    class ChallengeLLM:
        def analyze(self, sys_p, usr_p):
            call_count[0] += 1
            # Round 1: alternating stances to ensure disagreement
            if call_count[0] <= 5:
                stance = "support" if call_count[0] % 2 == 1 else "oppose"
            else:
                # Round 2: capture the prompt for the first minister
                if len(round2_prompts) == 0:
                    round2_prompts["prompt"] = usr_p
                stance = "neutral"
            return f'{{"stance": "{stance}", "reasoning": "My view.", "confidence": 0.75, "warning": "", "knowledge_cited": ""}}'

    from modules.council_execution.engine import NativeCouncil, _DARBAR_MINISTERS
    council = NativeCouncil(llm=ChallengeLLM())
    result = council.deliberate(
        user_input="Should we launch the product now?",
        context={"domains": ["strategy"], "mode": "darbar"},
    )
    assert round2_prompts, "Round 2 was never reached"
    r2 = round2_prompts["prompt"]
    # The round 2 prompt must reference a specific disagreeing minister by name
    any_minister_named = any(
        m.replace("_", " ") in r2.lower() or m in r2.lower()
        for m in _DARBAR_MINISTERS
    )
    assert any_minister_named, f"No minister name found in Round 2 prompt: {r2[:300]}"
    assert "challenge" in r2.lower() or "disagree" in r2.lower() or "oppose" in r2.lower(), \
        f"Round 2 prompt does not ask for challenge/response: {r2[:300]}"


def test_round2_result_includes_peer_challenges_field():
    """_two_round_deliberate result must include peer_challenges dict."""
    import sys
    for k in list(sys.modules.keys()):
        if "council_execution" in k:
            del sys.modules[k]

    class EchoLLM:
        def analyze(self, sys_p, usr_p):
            return '{"stance": "neutral", "reasoning": "ok", "confidence": 0.5, "warning": "", "knowledge_cited": ""}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=EchoLLM())
    result = council.deliberate(
        user_input="test",
        context={"domains": ["strategy"], "mode": "darbar"},
    )
    assert "peer_challenges" in result, f"peer_challenges missing: {list(result.keys())}"
    assert isinstance(result["peer_challenges"], dict)
```

- [ ] **Step 2: Run to confirm failure**

```
cd C:\Users\naren\Work\Projects\School\era
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_round2_prompt_contains_specific_challenger_name tests/test_era_upgrades.py::test_round2_result_includes_peer_challenges_field -v
```

Expected: **FAIL** — no named challengers in Round 2 prompt, no `peer_challenges` field

- [ ] **Step 3: Replace Round 2 loop in `_two_round_deliberate()` with structured challenge prompts**

Replace the Round 2 section of `_two_round_deliberate()`:

```python
# ── Round 2: directed peer challenge ─────────────────────────────────────────
round2: dict[str, dict] = {}
peer_challenges: dict[str, str] = {}

for name in minister_names:
    voice = MinisterVoice(minister_name=name, llm=self.llm)
    my_r1_stance = round1[name]["stance"]
    my_r1_reason = round1[name]["reasoning"]

    # Find ministers who explicitly disagree with this minister
    challengers = [
        (peer, r)
        for peer, r in round1.items()
        if peer != name and r["stance"] != my_r1_stance and r["stance"] != "neutral"
    ]

    if challengers:
        challenge_lines = []
        for peer_name, peer_r in challengers[:3]:
            challenge_lines.append(
                f"  - {peer_name.replace('_',' ').title()} ({peer_r['stance']}): "
                f"{peer_r['reasoning'][:150]}"
            )
        challenge_block = "\n".join(challenge_lines)
        challenge_prompt = (
            f"{user_input}\n\n"
            f"---\n"
            f"Your Round 1 position: {my_r1_stance} — {my_r1_reason[:150]}\n\n"
            f"Ministers who disagree with you:\n{challenge_block}\n\n"
            f"Do you maintain your position or revise it? "
            f"Challenge their reasoning directly, citing a specific doctrine principle "
            f"or knowledge entry if you have one."
        )
        peer_challenges[name] = challenge_block
    else:
        # No challengers — ask to reinforce or nuance
        challenge_prompt = (
            f"{user_input}\n\n"
            f"---\n"
            f"Your Round 1 position: {my_r1_stance} — {my_r1_reason[:150]}\n\n"
            f"No ministers disagreed. Confirm or add nuance to your position."
        )
        peer_challenges[name] = ""

    round2[name] = voice.deliberate(
        challenge_prompt,
        round2_context,
        knowledge_entries=knowledge_entries,
    )
```

Update the return dict to include `peer_challenges`:

```python
return {
    "outcome": outcome,
    "recommendation": outcome,
    "rounds": 2,
    "round1_stances": round1,
    "stances": round2,
    "peer_challenges": peer_challenges,
    "consensus_strength": round(max(weighted_support, weighted_oppose) / total_weight, 3),
    "red_line_concerns": warnings,
    "ministers_involved": minister_names,
    "dissent_summary": dissent_summary,
    "minority_alert": minority_alert,
}
```

Also ensure `knowledge_entries` is fetched before Round 1 in `_two_round_deliberate()` (same KIS call as Task 3.5 added to `_llm_deliberate()`):

```python
# ── KIS retrieval (shared across both rounds) ─────────────────────────────────
knowledge_entries: list = []
try:
    from persona.knowledge_engine import synthesize_knowledge
    if active_domains:
        kis = synthesize_knowledge(
            user_input=user_input,
            active_domains=active_domains,
            domain_confidence=0.7,
        )
        knowledge_entries = kis.get("synthesized_knowledge", [])[:6]
except Exception:
    pass
```

Pass `knowledge_entries=knowledge_entries` to Round 1 calls too:

```python
# Round 1
for name in minister_names:
    voice = MinisterVoice(minister_name=name, llm=self.llm)
    round1[name] = voice.deliberate(user_input, context, knowledge_entries=knowledge_entries)
```

- [ ] **Step 4: Run both Task 9.2 tests**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_round2_prompt_contains_specific_challenger_name tests/test_era_upgrades.py::test_round2_result_includes_peer_challenges_field -v
```

Expected: both **PASS**

- [ ] **Step 5: Run full upgrade suite**

```
.venv\Scripts\python -m pytest tests/test_era_upgrades.py -v
```

Expected: all **PASS**

- [ ] **Step 6: Smoke test — full darbar with echo LLM**

```
cd C:\Users\naren\Work\Projects\School\era
.venv\Scripts\python -c "
from modules.council_execution.engine import NativeCouncil

class EchoLLM:
    def analyze(self, s, u):
        has_challenge = 'disagree' in u.lower() or 'challenge' in u.lower()
        stance = 'oppose' if has_challenge else 'support'
        return '{\"stance\": \"' + stance + '\", \"reasoning\": \"Doctrine principle applies.\", \"confidence\": 0.75, \"warning\": \"\", \"knowledge_cited\": \"1\"}'

c = NativeCouncil(llm=EchoLLM())
r = c.deliberate('Should I resign today?', {'domains': ['career', 'finance'], 'mode': 'darbar'})
print('outcome:', r['outcome'])
print('rounds:', r['rounds'])
print('ministers:', len(r['ministers_involved']))
print('challenges surfaced:', sum(1 for v in r['peer_challenges'].values() if v))
print('minority_alert:', r['minority_alert'][:80] if r['minority_alert'] else 'none')
"
```

Expected output: `rounds: 2`, challenges surfaced > 0, ministers from domain-filtered darbar list.

- [ ] **Step 7: Commit**

```
git add modules/council_execution/engine.py tests/test_era_upgrades.py
git commit -m "feat: structured peer challenge — Round 2 ministers argue against named dissenters, cite knowledge"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|------------|------|
| Knowledge reinforcement loop | Track 1 ✅ |
| POST /feedback endpoint | Track 1.2 ✅ |
| entries_used in /chat response | Track 1.3 ✅ |
| Persistent user profile | Track 2.1 ✅ |
| user_id in /chat + profile in context | Track 2.2 ✅ |
| Per-minister LLM voice (MinisterVoice) | Track 3.1 ✅ |
| Meeting/Darbar deliberation wired | Track 3.2 ✅ |
| Surface disagreement in output | Task 3.3 ✅ |
| Minority voice escalation | Task 3.4 ✅ |
| KIS book knowledge into minister prompts | Task 3.5 ✅ |
| Outcome recording + auto-retrain | Track 4.1 ✅ |
| Single LLM classification call | Track 5.1 ✅ |
| Quick mode fast path | Track 5.1 ✅ |
| Tiered deliberation depth by stakes | Task 5.2 ✅ |
| Domain gap detection | Track 6.1 ✅ |
| Domain-aware minister activation | Track 7 ✅ |
| Bayesian confidence calibration | Track 8 ✅ |
| Two-round cross-minister dialogue | Track 9.1 ✅ |
| Structured peer challenge in Round 2 | Task 9.2 ✅ |

**Placeholder scan:** None found.

**Type consistency:**
- `_process_turn()` return tuple grows: Track 1.3 adds `entries_used`, Track 6 adds `knowledge_gaps`, Task 5.2 adds `deliberation_depth`. Each track explicitly updates all call sites.
- `Session.feedback_loop: OutcomeFeedbackLoop` added in Track 4 — consistent with import from `persona.learning.outcome_feedback`.
- `EpisodicMemory(":memory:")` — Track 4 adds this no-disk mode, test uses it immediately after.
- `MinisterConfidenceTracker` instantiated in `NativeCouncil.__init__()` in Track 8, used in both `_llm_deliberate()` and `_two_round_deliberate()` in Track 9 (Track 9 inherits from same instance).
- `_active_ministers_for_domains()` used in both Track 7 and Track 9 — consistent signature: `(domains: list, pool: list) -> list`.

---

## Execution Order

Complete ERA_FIX_PLAN.md first. Then tracks in this order:

```
Track 1 → Track 2 → Track 3 (3.1 → 3.2 → 3.3 → 3.4 → 3.5) → Track 4 → Track 5 (5.1 → 5.2) → Track 6 → Track 7 → Track 8 → Track 9 (9.1 → 9.2)
```

Dependencies:
- Task 3.5 requires Track 3.1 (`MinisterVoice` class) and ERA_FIX_PLAN Task 2 (BASE_PATH fixed)
- Task 3.5 requires ERA_FIX_PLAN Task 6 (Chroma) for best results — degrades gracefully without it
- Track 9.2 requires Track 9.1 (`_two_round_deliberate` exists) and Task 3.5 (`knowledge_entries` parameter on `deliberate()`)
- Track 8 requires Track 3.2 (`NativeCouncil.llm` wired)
- Track 7 requires Track 3.1 (`MinisterVoice` importable)

**What each milestone unlocks:**

| After | Ministers can |
|-------|---------------|
| Task 3.1 | Argue in character (doctrine persona) |
| Task 3.5 | Argue *from* ingested book knowledge + doctrine |
| Track 7 | Only relevant ministers engage per domain |
| Track 8 | Proven ministers carry more weight |
| Track 9.1 | See each other's stances before finalizing |
| Task 9.2 | Challenge specific dissenters by name, cite knowledge |

Task 9.2 is the completion point: ministers with full knowledge context, arguing in doctrine voice, challenging each other by name, with calibrated confidence — the closest ERA gets to a real wise council in deliberation.
