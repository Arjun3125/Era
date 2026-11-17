"""Resume-after-quota tests: durable cache, pending turn queue, API resume."""

import pytest

from persona import llm_resume
from persona.llm_errors import QuotaExhaustedError


def test_queue_roundtrip_and_dedupe(tmp_path, monkeypatch):
    monkeypatch.setenv("ERA_LLM_QUEUE_PATH", str(tmp_path / "pending.jsonl"))

    first = llm_resume.enqueue_turn("s1", "same message", "meeting", "user1")
    duplicate = llm_resume.enqueue_turn("s1", "same message", "meeting", "user1")

    assert first["id"] == duplicate["id"]
    assert len(llm_resume.load_pending()) == 1

    llm_resume.mark_attempt(first["id"], "free usage limit")
    pending = llm_resume.load_pending()
    assert pending[0]["attempts"] == 1
    assert "free usage limit" in pending[0]["last_error"]

    removed = llm_resume.remove_turn(first["id"])
    assert removed["id"] == first["id"]
    assert llm_resume.load_pending() == []


def test_chat_quota_enqueues_turn_and_resume_completes_it(tmp_path, monkeypatch):
    monkeypatch.setenv("ERA_LLM_QUEUE_PATH", str(tmp_path / "pending.jsonl"))
    monkeypatch.setenv("ERA_RESUME_INTERVAL_SECONDS", "0")

    from fastapi.testclient import TestClient

    import api

    monkeypatch.setattr(api, "_init_components", lambda: None)
    monkeypatch.setattr(api, "_components", {"llm": object()})

    calls = {"count": 0}

    def fake_process_turn(state, user_input):
        calls["count"] += 1
        if calls["count"] == 1:
            raise QuotaExhaustedError("Free usage limit reached")
        return ("resumed answer", [], "quick")

    monkeypatch.setattr(api, "_process_turn", fake_process_turn)
    client = TestClient(api.app)

    response = client.post(
        "/chat",
        json={"message": "decide later", "mode": "quick", "session_id": "ses-quota-test"},
    )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["quota_exhausted"] is True
    assert detail["queued_job"]

    pending = llm_resume.load_pending()
    assert [job["message"] for job in pending] == ["decide later"]

    resumed = client.post("/resume")
    assert resumed.status_code == 200
    body = resumed.json()
    assert body["remaining"] == 0
    assert body["resumed"][0]["ok"] is True
    assert calls["count"] == 2
    assert llm_resume.load_pending() == []


def test_resume_stops_and_keeps_job_while_quota_still_exhausted(tmp_path, monkeypatch):
    monkeypatch.setenv("ERA_LLM_QUEUE_PATH", str(tmp_path / "pending.jsonl"))
    monkeypatch.setenv("ERA_RESUME_INTERVAL_SECONDS", "0")

    from fastapi.testclient import TestClient

    import api

    monkeypatch.setattr(api, "_init_components", lambda: None)
    monkeypatch.setattr(api, "_components", {"llm": object()})

    def always_quota(state, user_input):
        raise QuotaExhaustedError("Free usage limit reached")

    monkeypatch.setattr(api, "_process_turn", always_quota)
    client = TestClient(api.app)

    job = llm_resume.enqueue_turn("ses-still-quota", "wait", "quick", None)
    body = client.post("/resume").json()

    assert body["quota_exhausted"] is True
    assert body["remaining"] == 1
    pending = llm_resume.load_pending()
    assert pending[0]["id"] == job["id"]
    assert pending[0]["attempts"] == 1
