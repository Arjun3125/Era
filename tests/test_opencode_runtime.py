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
def fake_server():
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


def test_free_usage_limit_is_not_retried(fake_server):
    _FakeOpenCodeServer.generate_status = 503
    _FakeOpenCodeServer.generate_body = {"message": "Free usage limit reached. Subscribe to OpenCode Go."}
    llm = _runtime(fake_server)

    result = llm.analyze("SYSTEM", "USER")
    assert "Free usage limit" in result

    generates = [r for r in _FakeOpenCodeServer.requests if r["path"].endswith("/generate")]
    assert len(generates) == 1
