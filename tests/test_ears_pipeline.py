"""
tests/test_ears_pipeline.py — Comprehensive unit tests, edge case verification,
and stress testing for EARS (Ambient Sensory Memory Module).

Covers:
1. Encryption & Decryption roundtrips (Unicode, Hinglish, emojis, corrupt ciphertext).
2. Privacy gate filtering in SOLO vs ANNOUNCED modes.
3. Multi-speaker conversation formatting for LLM (in-memory decryption).
4. Fact extraction resilience against empty strings, network timeouts, and malformed JSON.
5. Stress testing dual-write episodic storage under concurrent/rapid load.
6. Native schema integration with Era's core EpisodicMemory loading engine.
"""
import json
import pytest
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

from ears.config import SELF_SPEAKER_LABEL
from ears.privacy.redaction import (
    encrypt_text,
    decrypt_text,
    filter_segments,
    get_conversation_transcript_for_llm,
    summarize_context_only,
)
from ears.extraction.fact_extractor import extract_facts
from ears.memory_bridge.episodic_writer import write_episode
from persona.learning.episodic_memory import EpisodicMemory


# =====================================================================
# 1. ENCRYPTION & DECRYPTION EDGE CASES
# =====================================================================
def test_encryption_decryption_roundtrip():
    texts = [
        "Hello, this is a standard English sentence.",
        "Yaar aaj office me bohot stress tha, deadline kal hai! 😭",
        "Mala aaj khup kaam ahe, boss ne navin project dila.",
        "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
        "A" * 5000,  # Very long string
    ]
    for text in texts:
        encrypted = encrypt_text(text)
        assert encrypted != text
        assert len(encrypted) > 0
        decrypted = decrypt_text(encrypted)
        assert decrypted == text


def test_encryption_empty_and_corrupt_strings():
    assert encrypt_text("") == ""
    assert decrypt_text("") == ""
    assert decrypt_text(None) == ""
    # Corrupt ciphertext should fail gracefully without raising an unhandled exception
    assert decrypt_text("invalid_base64_fernet_string!") == "[DECRYPTION_FAILED]"


# =====================================================================
# 2. PRIVACY GATE & MULTI-SPEAKER FORMATTING EDGE CASES
# =====================================================================
@patch("ears.privacy.redaction.is_third_party_storage_allowed")
def test_filter_segments_solo_mode(mock_allowed):
    mock_allowed.return_value = False  # SOLO mode
    segments = [
        {"speaker": SELF_SPEAKER_LABEL, "text": "I need to finish this report.", "start": 0.0, "end": 2.0},
        {"speaker": "1", "text": "Don't worry, I will help you.", "start": 2.5, "end": 4.0},
        {"speaker": "2", "text": "Let's grab lunch after.", "start": 4.5, "end": 6.0},
    ]
    filtered = filter_segments(segments)
    assert len(filtered) == 3

    # Self speech should remain unencrypted
    assert filtered[0]["text"] == "I need to finish this report."
    assert filtered[0]["is_encrypted"] is False
    assert filtered[0]["third_party_present"] is False

    # Third-party speech should be encrypted on disk/in dictionary
    for i in [1, 2]:
        assert filtered[i]["text"] == "[ENCRYPTED_THIRD_PARTY_SPEECH]"
        assert filtered[i]["is_encrypted"] is True
        assert filtered[i]["third_party_present"] is True
        assert "text_encrypted" in filtered[i]
        assert decrypt_text(filtered[i]["text_encrypted"]) != "[DECRYPTION_FAILED]"


@patch("ears.privacy.redaction.is_third_party_storage_allowed")
def test_filter_segments_announced_mode(mock_allowed):
    mock_allowed.return_value = True  # ANNOUNCED_RECORDING mode
    segments = [
        {"speaker": SELF_SPEAKER_LABEL, "text": "We are recording this meeting."},
        {"speaker": "1", "text": "Understood, my consent is given."},
    ]
    filtered = filter_segments(segments)
    assert len(filtered) == 2
    assert filtered[1]["text"] == "Understood, my consent is given."
    assert filtered[1]["is_encrypted"] is False
    assert filtered[1]["third_party_present"] is True


@patch("ears.privacy.redaction.is_third_party_storage_allowed")
def test_get_conversation_transcript_for_llm_formatting(mock_allowed):
    mock_allowed.return_value = False  # SOLO mode
    segments = [
        {"speaker": "0", "text": "Yaar aaj bohot kaam hai."},
        {"speaker": "1", "text": "Don't worry bhai, mai help karunga."},
    ]
    filtered = filter_segments(segments)
    transcript = get_conversation_transcript_for_llm(filtered)

    assert "Self (Speaker 0): Yaar aaj bohot kaam hai." in transcript
    assert "Person 1 (Around User): Don't worry bhai, mai help karunga." in transcript
    assert "[ENCRYPTED_THIRD_PARTY_SPEECH]" not in transcript


def test_empty_segments_handling():
    assert filter_segments([]) == []
    assert get_conversation_transcript_for_llm([]) == ""
    assert summarize_context_only([]) == ""


# =====================================================================
# 3. FACT EXTRACTION RESILIENCE & EDGE CASES
# =====================================================================
def test_extract_facts_empty_transcript():
    assert extract_facts("") == []
    assert extract_facts("   \n\t  ") == []


@patch("requests.post")
def test_extract_facts_network_failure_fails_closed(mock_post):
    mock_post.side_effect = Exception("Ollama connection refused / timeout")
    facts = extract_facts("Self (Speaker 0): I am testing error handling.")
    assert facts == []  # Fails closed without crashing daemon


@patch("requests.post")
def test_extract_facts_malformed_json_from_llm(mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "Here are your facts:\n```json\nINVALID_JSON_HERE\n```"}
    mock_post.return_value = mock_resp

    facts = extract_facts("Self (Speaker 0): I am testing malformed JSON.")
    assert facts == []  # Should catch JSONDecodeError and return empty list


@patch("requests.post")
def test_extract_facts_success_mapping(mock_post):
    mock_llm_output = [
        {
            "domain": "career",
            "content": "User is feeling anxious about a deadline but receiving help from coworker.",
            "emotional_tone": "anxious",
            "non_verbal_cues": "Speaker exhibited hesitation (umm) and sighs.",
            "confidence": 0.95,
        }
    ]
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": json.dumps(mock_llm_output)}
    mock_post.return_value = mock_resp

    transcript = "Self (Speaker 0): Umm... deadline kal hai... sigh.\nPerson 1 (Around User): I will help you."
    facts = extract_facts(transcript, context_note="User was in conversation with coworkers.")

    assert len(facts) == 1
    f = facts[0]
    assert f["domain"] == "career"
    assert f["emotional_tone"] == "anxious"
    assert "hesitation" in f["non_verbal_cues"]
    assert f["confidence"] == 0.95
    assert f["third_party_present"] is True
    assert f["third_party_content_stored"] == "encrypted"


# =====================================================================
# 4. STRESS TESTING DUAL-WRITE EPISODIC STORAGE & CONCURRENCY
# =====================================================================
def test_write_episode_and_concurrent_stress(tmp_path):
    # Patch memory paths to use a temporary directory during stress testing
    test_active_memory = tmp_path / "episodes.jsonl"
    test_daily_dir = tmp_path / "Memory"
    test_daily_dir.mkdir()

    with patch("ears.memory_bridge.episodic_writer.ACTIVE_MEMORY_FILE", test_active_memory), \
         patch("ears.memory_bridge.episodic_writer.MEMORY_DIR", test_daily_dir):

        # 1. Single write verification
        sample_fact = {
            "turn": "ambient_test_1",
            "source": "ears_module",
            "domain": "health",
            "content": "User drank 2 liters of water today.",
            "emotional_tone": "calm",
            "non_verbal_cues": "None detected",
            "confidence": 0.90,
        }
        write_episode(sample_fact)
        assert test_active_memory.exists()
        with open(test_active_memory, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["content"] == "User drank 2 liters of water today."

        # 2. Concurrency stress test (50 threads writing simultaneously)
        num_threads = 50
        threads = []

        def worker(idx):
            write_episode({
                "turn": f"ambient_stress_{idx}",
                "source": "ears_module",
                "domain": "career",
                "content": f"Concurrent stress observation #{idx}",
                "confidence": 0.85,
            })

        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        with open(test_active_memory, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            # 1 initial + 50 concurrent = 51 total lines
            assert len(all_lines) == 51
            # Verify every single line is valid JSON without corruption/interleaving
            for line in all_lines:
                obj = json.loads(line)
                assert "content" in obj


# =====================================================================
# 5. INTEGRATION WITH ERA CORE EPISODIC MEMORY ENGINE
# =====================================================================
def test_episodic_memory_loads_ambient_episodes_without_error(tmp_path):
    test_memory_dir = tmp_path / "data" / "memory"
    test_memory_dir.mkdir(parents=True)
    test_episodes_file = test_memory_dir / "episodes.jsonl"

    # Write multiple ambient observations representing real-world speech
    ambient_records = [
        {
            "turn": "ambient_1",
            "source": "ears_module",
            "domain": "career",
            "type": "ambient_observation",
            "content": "User expressed frustration about project deadlines.",
            "emotional_tone": "frustrated",
            "non_verbal_cues": "Rapid speech and sighing.",
            "confidence": 0.95,
            "speaker": "self",
            "third_party_present": True,
            "third_party_content_stored": "encrypted",
        },
        {
            "turn": "ambient_2",
            "source": "ears_module",
            "domain": "health",
            "type": "ambient_observation",
            "content": "User went for a 5km morning run.",
            "emotional_tone": "enthusiastic",
            "non_verbal_cues": "Energetic tone.",
            "confidence": 0.90,
            "speaker": "self",
            "third_party_present": False,
            "third_party_content_stored": False,
        },
    ]

    with open(test_episodes_file, "w", encoding="utf-8") as f:
        for r in ambient_records:
            f.write(json.dumps(r) + "\n")

    # Initialize Era's EpisodicMemory pointing to our test file
    mem = EpisodicMemory(storage_path=str(test_episodes_file))
    assert len(mem.episodes) == 2

    # Verify attributes were loaded cleanly with defaults applied
    ep1 = list(mem.episodes.values())[0]
    assert ep1.domain == "career"
    assert ep1.user_input == "User expressed frustration about project deadlines."
    assert ep1.minister_stance == "ambient"
    assert ep1.confidence == 0.95
