"""
ears/privacy/redaction.py — The privacy gate and encryption engine.
Every transcript segment from the STT provider passes through here BEFORE
fact extraction or memory writing ever sees it.

In SOLO mode, instead of dropping speech from friends, coworkers, or family
members, their verbatim text is encrypted using symmetric encryption (Fernet).
In memory, the conversation is decrypted ONLY for the local LLM to analyze the
person-to-person context around the user. On disk or logs, third-party speech
remains encrypted.
"""
import os
from typing import List, Dict
from cryptography.fernet import Fernet
from ears.config import SELF_SPEAKER_LABEL, EARS_STATE_DIR
from ears.privacy.consent_state import is_third_party_storage_allowed
from ears.speaker_recognition.voiceprint_engine import resolve_speaker_label

_fernet_instance = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        EARS_STATE_DIR.mkdir(parents=True, exist_ok=True)
        key_path = EARS_STATE_DIR / "privacy.key"
        if not key_path.exists():
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
        else:
            with open(key_path, "rb") as f:
                key = f.read()
        _fernet_instance = Fernet(key)
    return _fernet_instance


def encrypt_text(text: str) -> str:
    if not text:
        return ""
    f = _get_fernet()
    return f.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_text(encrypted_text: str) -> str:
    if not encrypted_text:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        return "[DECRYPTION_FAILED]"


def filter_segments(segments: List[Dict]) -> List[Dict]:
    """
    Returns all segments, but protects third-party speech:
      - Segments spoken by you (SELF_SPEAKER_LABEL): kept unencrypted
      - Segments spoken by others in ANNOUNCED_RECORDING mode: kept unencrypted
      - Segments spoken by others in SOLO mode: verbatim text is encrypted!
        The raw text is replaced with '[ENCRYPTED_THIRD_PARTY_SPEECH]' and the
        ciphertext is stored in 'text_encrypted'.
    """
    third_party_ok = is_third_party_storage_allowed()
    kept = []
    for seg in segments:
        is_self = str(seg.get("speaker")) == str(SELF_SPEAKER_LABEL)
        if is_self:
            seg["third_party_present"] = False
            seg["is_encrypted"] = False
            kept.append(seg)
        elif third_party_ok:
            seg["third_party_present"] = True
            seg["is_encrypted"] = False
            kept.append(seg)
        else:
            # SOLO mode: encrypt third-party speech!
            raw_text = seg.get("text", "")
            seg["text_encrypted"] = encrypt_text(raw_text)
            seg["text"] = "[ENCRYPTED_THIRD_PARTY_SPEECH]"
            seg["third_party_present"] = True
            seg["is_encrypted"] = True
            kept.append(seg)
    return kept


def get_conversation_transcript_for_llm(segments: List[Dict]) -> str:
    """
    Builds an in-memory, decrypted person-to-person conversation transcript
    for the local LLM (Ollama) so it can understand the user's situation,
    social dynamics, and the people around them.
    """
    lines = []
    for seg in segments:
        if seg.get("is_encrypted") and seg.get("text_encrypted"):
            text = decrypt_text(seg["text_encrypted"])
        else:
            text = seg.get("text", "")
        
        speaker_label = resolve_speaker_label(seg.get("speaker", "1"))
        lines.append(f"{speaker_label}: {text}")
    return "\n".join(lines)


def summarize_context_only(segments: List[Dict]) -> str:
    """
    Produces a summary metadata note about third parties present in the conversation.
    """
    others_present = any(str(s.get("speaker")) != str(SELF_SPEAKER_LABEL) for s in segments)
    return "User was in conversation with friends, coworkers, or family during this segment." if others_present else ""

