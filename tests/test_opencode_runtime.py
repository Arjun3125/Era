"""Unit tests for the OpenCode server runtime adapter (no live server needed)."""

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from persona.opencode_runtime import OpenCodeRuntime


class _FakeOpenCodeServer(BaseHTTPRequestHandler):
    requests = []
    generate_status = 200
    generate_body = None

    def log_message(self, *args):  # silence test output
        pass

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        return json.loads(raw) if raw else {}

    def _send(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = self._read_body()
        type(self).requests.append(
            {"method": "POST", "path": self.path, "body": body,
             "auth": self.headers.get("Authorization")}
        )
        if self.path == "/api/session":
            self._send(200, {"data": {"id": "ses_test"}})
            return
        if self.path.endswith("/generate"):
            status = type(self).generate_status
            payload = type(self).generate_body or {"data": {"text": "OK"}}
            self._send(status, payload)
            return
        self._send(404, {"message": "not found"})

    def do_DELETE(self):
        type(self).requests.append({"method": "DELETE", "path": self.path})
        self._send(204, {})


@pytest.fixture()
def fake_server(tmp_path, monkeypatch):
    monkeypatch.setenv("ERA_LLM_CACHE_PATH", str(tmp_path / "cache.jsonl"))
    _FakeOpenCodeServer.requests = []
    _FakeOpenCodeServer.generate_status = 200
    _FakeOpenCodeServer.generate_body = None
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOpenCodeServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def _runtime(url):
    return OpenCodeRuntime(base_url=url, password="pw", timeout=10)


def test_analyze_pins_model_and_flattens_prompt(fake_server):
    llm = _runtime(fake_server)
    assert llm.analyze("SYSTEM", "USER") == "OK"

    session = next(r for r in _FakeOpenCodeServer.requests if r["path"] == "/api/session")
    assert session["body"]["model"] == {"providerID": "opencode", "id": "deepseek-v4.1-flash-free"}
    expected = "Basic " + base64.b64encode(b"opencode:pw").decode()
    assert session["auth"] == expected

    generate = next(r for r in _FakeOpenCodeServer.requests if r["path"].endswith("/generate"))
    assert "SYSTEM" in generate["body"]["prompt"]
    assert "USER" in generate["body"]["prompt"]
    assert any(r["method"] == "DELETE" for r in _FakeOpenCodeServer.requests)


def test_speak_keeps_history(fake_server):
    llm = _runtime(fake_server)
    llm.speak("SYSTEM", "first question")
    _FakeOpenCodeServer.requests = []
    llm.speak("SYSTEM", "second question")

    generate = next(r for r in _FakeOpenCodeServer.requests if r["path"].endswith("/generate"))
    prompt = generate["body"]["prompt"]
    assert "first question" in prompt
    assert "second question" in prompt


def test_free_usage_limit_raises_quota_error_without_retry(fake_server):
    from persona.llm_errors import QuotaExhaustedError

    _FakeOpenCodeServer.generate_status = 503
    _FakeOpenCodeServer.generate_body = {"message": "Free usage limit reached. Subscribe to OpenCode Go."}
    llm = _runtime(fake_server)

    with pytest.raises(QuotaExhaustedError, match="Free usage limit"):
        llm.analyze("SYSTEM", "USER")

    generates = [r for r in _FakeOpenCodeServer.requests if r["path"].endswith("/generate")]
    assert len(generates) == 1


def test_completed_calls_are_reused_after_quota_failure(fake_server, tmp_path, monkeypatch):
    from persona.llm_errors import QuotaExhaustedError

    monkeypatch.setenv("ERA_LLM_CACHE_TTL_SECONDS", "3600")
    llm = _runtime(fake_server)

    assert llm.analyze("SYSTEM", "FIRST") == "OK"
    assert llm.analyze("SYSTEM", "FIRST") == "OK"
    assert len([r for r in _FakeOpenCodeServer.requests if r["path"].endswith("/generate")]) == 1

    _FakeOpenCodeServer.generate_status = 503
    _FakeOpenCodeServer.generate_body = {"message": "Free usage limit reached."}
    with pytest.raises(QuotaExhaustedError):
        llm.analyze("SYSTEM", "SECOND")

    _FakeOpenCodeServer.generate_status = 200
    _FakeOpenCodeServer.generate_body = None
    assert llm.analyze("SYSTEM", "SECOND") == "OK"
    assert llm.analyze("SYSTEM", "FIRST") == "OK"

    generates = [r for r in _FakeOpenCodeServer.requests if r["path"].endswith("/generate")]
    assert len(generates) == 3
