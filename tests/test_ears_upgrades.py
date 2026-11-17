"""
tests/test_ears_upgrades.py — Unit and integration test suite for EARS next-gen upgrades:
1. Tailscale networking & endpoint generation.
2. Personal World Model (PWM) entity linking.
3. Proactive real-time coaching interventions.
4. Voiceprint enrollment and speaker label resolution.
"""
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from ears.networking.tailscale_config import get_available_endpoints, print_mobile_setup_guide
from ears.extraction.entity_linker import link_and_update_entities, load_entities
from ears.coaching.proactive_intervention import evaluate_and_trigger_coaching
from ears.speaker_recognition.voiceprint_engine import enroll_voiceprint, resolve_speaker_label
from ears.privacy.redaction import get_conversation_transcript_for_llm


# =====================================================================
# 1. TAILSCALE & NETWORKING TESTS
# =====================================================================
def test_tailscale_endpoint_generation():
    endpoints = get_available_endpoints(port=8787)
    assert "localhost" in endpoints
    assert endpoints["localhost"] == "http://127.0.0.1:8787/ingest"
    
    guide = print_mobile_setup_guide(port=8787)
    assert "EARS MOBILE COMPANION SETUP ENDPOINTS" in guide
    assert "http://127.0.0.1:8787/ingest" in guide


# =====================================================================
# 2. PWM ENTITY LINKING TESTS
# =====================================================================
def test_entity_linking_creates_and_updates_profiles(tmp_path):
    test_pwm_dir = tmp_path / "pwm"
    test_entities_file = test_pwm_dir / "entities.json"
    
    with patch("ears.extraction.entity_linker.PWM_DIR", test_pwm_dir), \
         patch("ears.extraction.entity_linker.ENTITIES_FILE", test_entities_file):
        
        sample_facts = [
            {
                "domain": "career",
                "content": "User discussed project deadline with coworker Sarah.",
                "emotional_tone": "stressed",
                "confidence": 0.90
            }
        ]
        transcript = "Self (Speaker 0): Sarah, we need to finish this report by Friday."
        
        enriched = link_and_update_entities(sample_facts, transcript)
        assert len(enriched) == 1
        assert "linked_entities" in enriched[0]
        assert "Sarah" in enriched[0]["linked_entities"] or "Coworker" in enriched[0]["linked_entities"]
        
        # Verify persistence on disk
        assert test_entities_file.exists()
        data = json.loads(test_entities_file.read_text(encoding="utf-8"))
        entities = data.get("entities", {})
        assert len(entities) > 0


# =====================================================================
# 3. PROACTIVE COACHING INTERVENTION TESTS
# =====================================================================
def test_proactive_coaching_trigger(tmp_path):
    test_log_file = tmp_path / "coaching_interventions.jsonl"
    
    with patch("ears.coaching.proactive_intervention.COACHING_LOG_FILE", test_log_file):
        anxious_episode = {
            "turn": "ambient_test",
            "domain": "career",
            "content": "User feeling acute anxiety over presentation.",
            "emotional_tone": "anxious",
            "confidence": 0.90
        }
        
        intervention = evaluate_and_trigger_coaching(anxious_episode)
        assert intervention is not None
        assert intervention["detected_tone"] == "anxious"
        assert "4-7-8 breathing" in intervention["recommended_strategy"]
        assert "coaching_intervention" in anxious_episode
        
        # Verify log file written
        assert test_log_file.exists()
        lines = test_log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1


def test_proactive_coaching_ignores_low_confidence_or_calm():
    calm_episode = {"emotional_tone": "calm", "confidence": 0.95}
    assert evaluate_and_trigger_coaching(calm_episode) is None
    
    low_conf_anxious = {"emotional_tone": "anxious", "confidence": 0.50}
    assert evaluate_and_trigger_coaching(low_conf_anxious) is None


def test_proactive_coaching_handles_malformed_confidence_strings():
    malformed_anxious = {"emotional_tone": "anxious", "confidence": "85%"}
    assert evaluate_and_trigger_coaching(malformed_anxious) is not None
    
    invalid_conf = {"emotional_tone": "anxious", "confidence": "high_certainty"}
    assert evaluate_and_trigger_coaching(invalid_conf) is None


# =====================================================================
# 4. VOICEPRINT ENROLLMENT & SPEAKER RESOLUTION TESTS
# =====================================================================
def test_voiceprint_enrollment_and_resolution(tmp_path):
    test_pwm_dir = tmp_path / "pwm"
    test_vp_file = test_pwm_dir / "voiceprints.json"
    test_ent_file = test_pwm_dir / "entities.json"
    
    with patch("ears.speaker_recognition.voiceprint_engine.PWM_DIR", test_pwm_dir), \
         patch("ears.speaker_recognition.voiceprint_engine.VOICEPRINTS_FILE", test_vp_file), \
         patch("ears.extraction.entity_linker.PWM_DIR", test_pwm_dir), \
         patch("ears.extraction.entity_linker.ENTITIES_FILE", test_ent_file):
        
        # 1. Before enrollment
        assert resolve_speaker_label("1") == "Person 1 (Around User)"
        
        # 2. Enroll Voice 1 to Alex
        enroll_voiceprint(speaker_label="1", entity_name="Alex", relationship_category="work")
        
        # 3. After enrollment
        resolved = resolve_speaker_label("1")
        assert "Alex" in resolved
        assert "Enrolled Voice #1" in resolved
        
        # 4. Verify in redaction LLM formatting
        segments = [
            {"speaker": "0", "text": "Hello Alex."},
            {"speaker": "1", "text": "Hi User, good morning.", "is_encrypted": False}
        ]
        transcript = get_conversation_transcript_for_llm(segments)
        assert "Self (Speaker 0): Hello Alex." in transcript
        assert "Alex (Enrolled Voice #1): Hi User, good morning." in transcript
