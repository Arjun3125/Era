"""
tests/test_ears_phase3.py — Automated Verification for EARS Phase 3 Upgrades.
"""
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta

import ears.memory_bridge.sleep_cycle as sc
import ears.coaching.morning_briefing as mb
import ears.speaker_recognition.auto_enrollment as ae
import ears.speaker_recognition.voiceprint_engine as ve


@pytest.fixture
def setup_phase3_env(tmp_path, monkeypatch):
    """Create isolated temporary files for Phase 3 testing."""
    test_active_mem = tmp_path / "episodes.jsonl"
    test_pwm_dir = tmp_path / "pwm"
    test_archive_dir = tmp_path / "archive"
    test_briefings = tmp_path / "morning_briefings.jsonl"

    monkeypatch.setattr(sc, "ACTIVE_MEMORY_FILE", test_active_mem)
    monkeypatch.setattr(sc, "PWM_DIR", test_pwm_dir)
    monkeypatch.setattr(sc, "CONSOLIDATED_FILE", test_pwm_dir / "consolidated_memories.json")
    monkeypatch.setattr(sc, "ARCHIVE_DIR", test_archive_dir)

    monkeypatch.setattr(mb, "BRIEFINGS_LOG_FILE", test_briefings)

    monkeypatch.setattr(ae, "PWM_DIR", test_pwm_dir)
    monkeypatch.setattr(ae, "CANDIDATES_FILE", test_pwm_dir / "voiceprint_candidates.json")

    monkeypatch.setattr(ve, "VOICEPRINTS_FILE", test_pwm_dir / "voiceprints.json")

    return {
        "active": test_active_mem,
        "pwm": test_pwm_dir,
        "archive": test_archive_dir,
        "briefings": test_briefings
    }


def test_sleep_cycle_consolidation_and_archiving(setup_phase3_env):
    """Verify that run_sleep_cycle consolidates stats and archives old episodes."""
    env = setup_phase3_env
    
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=35)).isoformat()
    recent_ts = now.isoformat()

    episodes = [
        {"turn": old_ts, "domain": "career", "emotional_tone": "stressed", "linked_entities": ["Sarah", "Alex"]},
        {"turn": recent_ts, "domain": "career", "emotional_tone": "calm", "linked_entities": ["Sarah"]},
        {"turn": recent_ts, "domain": "health", "emotional_tone": "anxious", "linked_entities": [], "coaching_intervention": "breathing"}
    ]

    with open(env["active"], "w", encoding="utf-8") as f:
        for ep in episodes:
            f.write(json.dumps(ep) + "\n")

    res = sc.run_sleep_cycle(archive_days=30, force_archive=False)
    assert res["status"] == "success"
    assert res["digest"]["total_episodes_analyzed"] == 3
    assert res["digest"]["domains_distribution"]["career"] == 2
    assert res["digest"]["coaching_interventions_count"] == 1
    assert "Sarah" in res["digest"]["top_entities_interacted"]

    # Check archiving: 1 old episode archived, 2 retained in active
    assert res["archived_episodes"] == 1
    assert res["retained_episodes"] == 2

    with open(env["active"], "r", encoding="utf-8") as f:
        retained = [json.loads(line) for line in f if line.strip()]
    assert len(retained) == 2


def test_morning_briefing_generation(setup_phase3_env):
    """Verify that generate_morning_briefing synthesizes minister statements."""
    # First run sleep cycle to create a digest
    test_sleep_cycle_consolidation_and_archiving(setup_phase3_env)

    briefing = mb.generate_morning_briefing()
    assert "briefing_id" in briefing
    assert "minister_statements" in briefing
    stmts = briefing["minister_statements"]
    
    assert "psychology_discipline" in stmts
    assert "grand_strategist" in stmts
    assert "risk_health" in stmts
    assert "career" in stmts["grand_strategist"].lower() or "sarah" in stmts["grand_strategist"].lower()


def test_self_supervised_acoustic_auto_enrollment(setup_phase3_env):
    """Verify conversational address correlation and auto-promotion."""
    # Turn sequence: Self (0) says "Hey Sarah", Speaker 5 replies
    segments = [
        {"speaker": "0", "text": "Hey Sarah, what do you think about this plan?"},
        {"speaker": "5", "text": "I think it looks really good, let's proceed."}
    ]

    # Pass 1: 25% confidence
    promoted = ae.analyze_conversational_correlations(segments, auto_promote=True)
    assert len(promoted) == 0
    cands = ae.load_candidates()["candidates"]
    assert "5_sarah" in cands
    assert cands["5_sarah"]["confidence"] == 0.25
    assert cands["5_sarah"]["status"] == "pending_correlation"

    # Pass 2 & 3: 50% -> 75% confidence (triggers auto-promote!)
    ae.analyze_conversational_correlations(segments, auto_promote=True)
    promoted = ae.analyze_conversational_correlations(segments, auto_promote=True)
    
    assert len(promoted) == 1
    assert promoted[0]["candidate_id"] == "5_sarah"
    assert promoted[0]["status"] == "promoted"

    # Check that speaker 5 was actually enrolled in voiceprints.json
    vps = ve.load_voiceprints()["voiceprints"]
    assert "5" in vps
    assert vps["5"]["entity_name"] == "Sarah"
