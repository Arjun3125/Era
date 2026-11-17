"""OpenCode server runtime — LLM access through a local `opencode serve` process.

OpenCode's free-tier models reject direct application traffic (HTTP 403
FreeTierError). The supported path is the official OpenCode server: create a
session pinned to the model and call `POST /api/session/{id}/generate`, which
runs inside the OpenCode client.

Set env vars:
  ERA_LLM_PROVIDER=opencode_server
  OPENCODE_SERVER_URL=http://127.0.0.1:9467   (required)
  OPENCODE_SERVER_PASSWORD=<server password>  (required)
  OPENCODE_MODEL=deepseek-v4.1-flash-free     (optional, has default)

Start the server with:
  $env:OPENCODE_SERVER_PASSWORD="<password>"
  opencode serve --port 9467 --hostname 127.0.0.1

Usage:
  from persona.opencode_runtime import OpenCodeRuntime
  llm = OpenCodeRuntime()
  response = llm.speak("You are a minister.", "What should I do?")
"""

import base64
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

DEFAULT_URL = "http://127.0.0.1:9467"
DEFAULT_MODEL = "deepseek-v4.1-flash-free"
DEFAULT_MODEL_PROVIDER = "opencode"
PROVIDER_NAME = "opencode_server"


class OpenCodeRuntime:
    def __init__(self, speak_model=None, analyze_model=None, base_url=None,
                 password=None, timeout=None):
        self.base_url = (base_url or os.getenv("OPENCODE_SERVER_URL", DEFAULT_URL)).rstrip("/")
        self.password = password or os.getenv("OPENCODE_SERVER_PASSWORD", "")
        if not self.password:
            raise RuntimeError(
                "OPENCODE_SERVER_PASSWORD not set. Start `opencode serve` with "
                "OPENCODE_SERVER_PASSWORD=<password> and export the same value."
            )

        self.speak_model = speak_model or os.getenv("OPENCODE_MODEL", DEFAULT_MODEL)
        self.analyze_model = analyze_model or os.getenv("OPENCODE_MODEL", DEFAULT_MODEL)
        self.model_provider = os.getenv("OPENCODE_MODEL_PROVIDER", DEFAULT_MODEL_PROVIDER)
        self.timeout = float(timeout or os.getenv("OPENCODE_TIMEOUT", "180"))
        self.messages = []
        self.max_pairs = 10

        self.fail_fast_errors = os.getenv("EVAL_FAIL_FAST_ERRORS", "0").lower() in {"1", "true", "yes"}
        self._auth = "Basic " + base64.b64encode(
            ("opencode:" + self.password).encode("utf-8")
        ).decode("ascii")

    # -- transport ---------------------------------------------------------
    def _request(self, method, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Authorization": self._auth, "Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body) if body.strip() else {}

    def _generate(self, prompt, model):
        """Create a session, run one transient generation, delete the session."""
        session = self._request(
            "POST",
            "/api/session",
            {"title": "era-runtime", "model": {"providerID": self.model_provider, "id": model}},
        )
        session_id = (session.get("data") or {}).get("id")
        if not session_id:
            raise RuntimeError("OpenCode server did not return a session id")
        try:
            result = self._request(
                "POST", f"/api/session/{session_id}/generate", {"prompt": prompt}
            )
        finally:
            try:
                self._request("DELETE", f"/api/session/{session_id}")
            except Exception:
                pass
        text = (result.get("data") or {}).get("text")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("OpenCode server returned empty text")
        return text.strip()

    @staticmethod
    def _should_retry(exc):
        text = str(exc).lower()
        if "free tier" in text or "free usage limit" in text or "http 403" in text:
            return False
        return True

    def _call(self, model, prompt):
        for attempt in range(2):
            try:
                return self._generate(prompt, model)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:300]
                err = RuntimeError(f"OpenCode server API error {exc.code}: {body}")
                if attempt == 0 and self._should_retry(err):
                    time.sleep(1.0)
                    continue
                raise err
            except Exception as exc:
                if attempt == 0 and self._should_retry(exc):
                    time.sleep(1.0)
                    continue
                raise
        return ""

    # -- public interface (matches OpenRouterRuntime) ----------------------
    def analyze(self, system_prompt, user_prompt):
        """Silent analysis handshake."""
        prompt = f"{system_prompt}\n\n{user_prompt}"
        try:
            return self._call(self.analyze_model, prompt)
        except Exception as e:
            if self.fail_fast_errors:
                raise RuntimeError(f"OpenCode analyze() failed: {e}") from e
            return f"[LLM analyze error: {e}]"

    def analyze_async(self, system_prompt, user_prompt):
        return executor.submit(self.analyze, system_prompt, user_prompt)

    def speak(self, system_context, user_input):
        """Primary speak handshake — user-visible. Blocking."""
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0]["content"] = system_context
        else:
            self.messages.insert(0, {"role": "system", "content": system_context})
        self.messages.append({"role": "user", "content": user_input})

        max_msgs = 1 + (self.max_pairs * 2)
        if len(self.messages) > max_msgs:
            self.messages = [self.messages[0]] + self.messages[-(max_msgs - 1):]

        lines = []
        for msg in self.messages[1:]:
            speaker = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{speaker}: {msg['content']}")
        prompt = f"{system_context}\n\n" + "\n\n".join(lines)

        try:
            assistant_text = self._call(self.speak_model, prompt)
        except Exception as e:
            if self.fail_fast_errors:
                raise RuntimeError(f"OpenCode speak() failed: {e}") from e
            assistant_text = f"[LLM speak error: {e}]"

        self.messages.append({"role": "assistant", "content": assistant_text})
        if len(self.messages) > max_msgs:
            self.messages = [self.messages[0]] + self.messages[-(max_msgs - 1):]

        return assistant_text

    def speak_async(self, system_context, user_input):
        return executor.submit(self.speak, system_context, user_input)
