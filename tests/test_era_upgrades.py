"""Tests for ERA self-improvement upgrades — Tracks 1–9."""
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
    for cat in ["rules", "warnings", "claims"]:
        (d / f"{cat}.json").write_text(json.dumps(
            {"domain": domain, "category": cat, "entries": [], "meta": {"total_entries": 0}}
        ))
    return d


# ══════════════════════════════════════════════════════════════════════════════
# Track 1: Knowledge Reinforcement Loop
# ══════════════════════════════════════════════════════════════════════════════

def test_reinforce_entry_increments_count(tmp_path, monkeypatch):
    """reinforce_entry must increment reinforcement_count and set last_reinforced_date."""
    import sys
    for k in list(sys.modules.keys()):
        if "knowledge_engine" in k:
            del sys.modules[k]

    d = _make_minister_dir(tmp_path, "adaptation")
    monkeypatch.setenv("ERA_MINISTER_PATH", str(tmp_path / "ministers"))

    from persona.knowledge_engine import reinforce_entry
    reinforce_entry("e1", "adaptation", "principles", positive=True)

    data = json.loads((d / "principles.json").read_text())
    entry = next(e for e in data["entries"] if e["id"] == "e1")
    mem = entry.get("memory", {})
    assert mem.get("reinforcement_count", 0) >= 1, "reinforcement_count not incremented"
    assert "last_reinforced_date" in mem, "last_reinforced_date not set"


def test_penalize_entry_increments_penalty(tmp_path, monkeypatch):
    """reinforce_entry with positive=False must increment penalty_count."""
    import sys
    for k in list(sys.modules.keys()):
        if "knowledge_engine" in k:
            del sys.modules[k]

    d = _make_minister_dir(tmp_path, "risk")
    monkeypatch.setenv("ERA_MINISTER_PATH", str(tmp_path / "ministers"))

    from persona.knowledge_engine import reinforce_entry
    reinforce_entry("e2", "risk", "principles", positive=False)

    data = json.loads((d / "principles.json").read_text())
    entry = next(e for e in data["entries"] if e["id"] == "e2")
    mem = entry.get("memory", {})
    assert mem.get("penalty_count", 0) >= 1, "penalty_count not incremented"


def test_feedback_endpoint_updates_entry(tmp_path, monkeypatch):
    """POST /feedback must call reinforce_entry for each entry_id in the payload."""
    import sys
    for k in list(sys.modules.keys()):
        if "knowledge_engine" in k or "api" in k:
            del sys.modules[k]

    d = _make_minister_dir(tmp_path, "adaptation")
    monkeypatch.setenv("ERA_MINISTER_PATH", str(tmp_path / "ministers"))

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


def test_chat_response_includes_entries_used():
    """/chat response must include entries_used list so client can submit /feedback."""
    import sys
    for k in list(sys.modules.keys()):
        if "api" in k:
            del sys.modules[k]

    import api
    from fastapi.testclient import TestClient

    class FakeLLM:
        def speak(self, ctx, inp): return "advice text"
        def analyze(self, sys_p, usr_p): return "{}"

    api._components.clear()
    api._components["llm"] = FakeLLM()

    client = TestClient(api.app)
    r = client.post("/chat", json={"message": "should I quit my job", "session_id": "t1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "entries_used" in body, f"entries_used missing from response: {list(body.keys())}"
    assert isinstance(body["entries_used"], list)


# ══════════════════════════════════════════════════════════════════════════════
# Track 2: Persistent User Profile
# ══════════════════════════════════════════════════════════════════════════════

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
        def analyze(self, sys_p, usr_p): return "{}"

    api._components.clear()
    api._components["llm"] = FakeLLM()

    client = TestClient(api.app)
    r = client.post("/chat", json={
        "message": "should I change careers",
        "session_id": "sess1",
        "user_id": "user42",
    })
    assert r.status_code == 200, r.text

    from persona.user_profile import load_profile
    profile = load_profile("user42")
    assert profile is not None
    assert profile.total_turns >= 1


# ══════════════════════════════════════════════════════════════════════════════
# Track 3: Per-Minister LLM Voice
# ══════════════════════════════════════════════════════════════════════════════

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
    # When split vote, dissent_summary must be present
    if result["outcome"] in {"proceed", "reconsider"}:
        assert "dissent_summary" in result, "dissent_summary missing"


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


# ══════════════════════════════════════════════════════════════════════════════
# Track 4: Auto-Retrain Trigger
# ══════════════════════════════════════════════════════════════════════════════

def test_auto_retrain_triggers_after_threshold():
    """After sufficient failures, check_and_retrain must detect failure clusters."""
    from persona.learning.episodic_memory import EpisodicMemory, Episode
    from persona.learning.outcome_feedback import OutcomeFeedbackLoop

    mem = EpisodicMemory(storage_path=":memory:")

    # Inject 3 failure episodes in "career" domain
    for i in range(3):
        ep = Episode(
            episode_id=str(i), turn_id=i, domain="career",
            user_input="quit job?", persona_recommendation="proceed",
            confidence=0.7, minister_stance="support", council_recommendation="proceed",
            outcome="failure", regret_score=0.8,
        )
        mem.episodes[ep.episode_id] = ep

    class FakeCouncil:
        ministers = {"career": type("M", (), {})()}
        _confidence_tracker = None  # Will be set below

    from persona.learning.minister_confidence import MinisterConfidenceTracker
    tracker = MinisterConfidenceTracker()
    FakeCouncil._confidence_tracker = tracker

    loop = OutcomeFeedbackLoop(council=FakeCouncil(), episodic_memory=mem)
    loop.check_and_retrain()

    clusters = mem.detect_failure_clusters(domain="career")
    assert clusters, "No failure clusters detected — episodes not stored"
    # Verify the tracker was actually called (weight should be < 1.0 after failures)
    weight = tracker.get_weight("career", "career")
    assert weight < 1.0, f"Expected weight < 1.0 after failures, got {weight}"


# ══════════════════════════════════════════════════════════════════════════════
# Track 5: Efficiency — Single LLM Classification
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# Track 6: Domain Gap Detection
# ══════════════════════════════════════════════════════════════════════════════

def test_knowledge_gap_detected_when_domain_sparse(tmp_path, monkeypatch):
    """synthesize_knowledge must report knowledge_gaps when a domain has fewer than MIN_ENTRIES entries."""
    import sys
    for k in list(sys.modules.keys()):
        if "knowledge_engine" in k:
            del sys.modules[k]

    # Create a sparse domain with only 1 entry
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

    monkeypatch.setenv("ERA_MINISTER_PATH", str(tmp_path / "ministers"))

    from persona.knowledge_engine import synthesize_knowledge
    result = synthesize_knowledge(
        user_input="what should I do",
        active_domains=["rare_domain"],
        domain_confidence=0.8,
    )
    gaps = result.get("knowledge_gaps", [])
    assert "rare_domain" in gaps, f"Expected 'rare_domain' in knowledge_gaps, got: {gaps}"


# ══════════════════════════════════════════════════════════════════════════════
# Track 7: Domain-Aware Minister Activation
# ══════════════════════════════════════════════════════════════════════════════

def test_domain_routing_activates_only_relevant_ministers():
    """For a 'career' domain query, ministers unrelated to career must not be activated."""
    import sys
    for k in list(sys.modules.keys()):
        if "council_execution" in k:
            del sys.modules[k]

    activated = []

    class LogLLM:
        def analyze(self, sys_p, usr_p):
            import re
            m = re.search(r"You are ([\w][\w ]*) in a council", sys_p)
            if m:
                activated.append(m.group(1).lower())
            return '{"stance": "neutral", "reasoning": "ok.", "confidence": 0.5, "warning": ""}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=LogLLM())
    result = council.deliberate(
        user_input="Should I accept the promotion?",
        context={"domains": ["career"], "mode": "meeting"},
    )
    # War Mode minister should NOT appear for a career query
    assert "war mode" not in activated, f"War Mode activated for career query: {activated}"
    assert len(activated) <= 8, f"Too many ministers activated ({len(activated)}) for single domain"


# ══════════════════════════════════════════════════════════════════════════════
# Track 8: Bayesian Minister Confidence
# ══════════════════════════════════════════════════════════════════════════════

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
    """After recording successes, get_weight() must return >= 1.0."""
    from persona.learning.minister_confidence import MinisterConfidenceTracker

    tracker = MinisterConfidenceTracker(storage_path=":memory:")
    for _ in range(5):
        tracker.record_outcome(minister="grand_strategist", domain="strategy", success=True)

    weight = tracker.get_weight("grand_strategist", "strategy")
    assert weight >= 1.0, f"Consistent success should boost weight, got {weight}"


# ══════════════════════════════════════════════════════════════════════════════
# Track 9: Multi-Round Dialogue
# ══════════════════════════════════════════════════════════════════════════════

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
            if "Peer stances" in usr_p or "other ministers" in usr_p.lower() or "disagree" in usr_p.lower():
                second_round_saw_peers[0] = True
            return '{"stance": "neutral", "reasoning": "Considered.", "confidence": 0.6, "warning": ""}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=TwoRoundLLM())
    result = council.deliberate(
        user_input="Should we go to war?",
        context={"domains": ["conflict", "strategy"], "mode": "darbar"},
    )
    # With two rounds, calls should be at least double the number of ministers
    assert call_count[0] > 3, \
        f"Only {call_count[0]} calls — no second round detected"
    assert "rounds" in result, "result missing 'rounds' field"


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


def test_ministerial_inquiries_and_question_sharing():
    """Verify that ministers can formulate questions for peers and Sovereign, and that they appear in council output."""
    import sys
    for k in list(sys.modules.keys()):
        if "council_execution" in k:
            del sys.modules[k]

    class InquiryLLM:
        def analyze(self, sys_p, usr_p):
            return '{"stance": "support", "reasoning": "We should proceed if cash allows.", "advice": "Check cash reserves.", "questions": ["To Risk Minister: what is our buffer?", "To Sovereign: what is our budget cap?"], "confidence": 0.8}'

    from modules.council_execution.engine import NativeCouncil
    council = NativeCouncil(llm=InquiryLLM())
    result = council.deliberate(
        user_input="Should we invest?",
        context={"domains": ["strategy"], "mode": "darbar"},
    )
    assert "user_questions" in result, "user_questions missing from council result"
    assert len(result["user_questions"]) > 0, "No user questions captured"
    assert "MINISTERIAL INQUIRIES & CLARIFICATIONS" in result["advisory_dialogue"], "Inquiries section missing from dialogue"

