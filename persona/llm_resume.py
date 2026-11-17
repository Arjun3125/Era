"""Durable LLM response cache and pending-turn queue for quota recovery.

When the free-tier quota runs out mid-council, completed LLM calls are already
on disk. The failed turn is queued in ``data/llm_queue/pending_turns.jsonl``;
replaying it after the quota resets reuses every cached prompt and only calls
the model for work that never finished.

Env:
  ERA_LLM_CACHE_PATH          response cache file (default data/llm_cache/llm_responses.jsonl)
  ERA_LLM_CACHE_TTL_SECONDS   cache lifetime (default 86400, <=0 disables)
  ERA_LLM_QUEUE_PATH          pending turn file (default data/llm_queue/pending_turns.jsonl)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOCK = threading.Lock()
_CACHE_BY_PATH: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # torn append — keep the rest
    except OSError:
        return []
    return rows


def _atomic_write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


# -- response cache ---------------------------------------------------------

def cache_path() -> Path:
    raw = os.getenv("ERA_LLM_CACHE_PATH")
    return Path(raw) if raw else _PROJECT_ROOT / "data" / "llm_cache" / "llm_responses.jsonl"


def cache_ttl_seconds() -> int:
    try:
        return int(os.getenv("ERA_LLM_CACHE_TTL_SECONDS", "86400"))
    except ValueError:
        return 86400


def cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}\n{prompt}".encode("utf-8")).hexdigest()


def _cache_index(path: Path) -> Dict[str, Dict[str, Any]]:
    key = str(path)
    if key not in _CACHE_BY_PATH:
        index: Dict[str, Dict[str, Any]] = {}
        for row in _read_jsonl(path):
            if isinstance(row.get("key"), str) and isinstance(row.get("text"), str):
                index[row["key"]] = {"ts": float(row.get("ts", 0)), "text": row["text"]}
        _CACHE_BY_PATH[key] = index
    return _CACHE_BY_PATH[key]


def cache_get(model: str, prompt: str) -> Optional[str]:
    ttl = cache_ttl_seconds()
    if ttl <= 0:
        return None
    path = cache_path()
    with _LOCK:
        entry = _cache_index(path).get(cache_key(model, prompt))
    if not entry:
        return None
    if time.time() - entry["ts"] > ttl:
        return None
    return entry["text"]


def cache_put(model: str, prompt: str, text: str) -> None:
    if cache_ttl_seconds() <= 0 or not text:
        return
    path = cache_path()
    key = cache_key(model, prompt)
    stamp = time.time()
    with _LOCK:
        _cache_index(path)[key] = {"ts": stamp, "text": text}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"key": key, "ts": stamp, "text": text}, ensure_ascii=False) + "\n")
        except OSError:
            pass  # cache is an optimization; never fail the call


# -- pending turn queue -----------------------------------------------------

def queue_path() -> Path:
    raw = os.getenv("ERA_LLM_QUEUE_PATH")
    return Path(raw) if raw else _PROJECT_ROOT / "data" / "llm_queue" / "pending_turns.jsonl"


def load_pending() -> list[dict]:
    return _read_jsonl(queue_path())


def save_pending(jobs: list[dict]) -> None:
    _atomic_write_jsonl(queue_path(), jobs)


def enqueue_turn(session_id: str, message: str, mode: Optional[str] = None,
                 user_id: Optional[str] = None) -> dict:
    """Queue a failed turn. Same session + message returns the existing job."""
    with _LOCK:
        jobs = load_pending()
        for job in jobs:
            if job.get("session_id") == session_id and job.get("message") == message:
                return job
        job = {
            "id": uuid.uuid4().hex[:12],
            "session_id": session_id,
            "message": message,
            "mode": mode,
            "user_id": user_id,
            "created_at": _now_iso(),
            "attempts": 0,
            "last_attempt": None,
            "last_error": None,
        }
        jobs.append(job)
        save_pending(jobs)
        return job


def remove_turn(job_id: str) -> Optional[dict]:
    with _LOCK:
        jobs = load_pending()
        removed = next((job for job in jobs if job.get("id") == job_id), None)
        if removed is not None:
            save_pending([job for job in jobs if job.get("id") != job_id])
        return removed


def mark_attempt(job_id: str, error: str = "") -> None:
    with _LOCK:
        jobs = load_pending()
        for job in jobs:
            if job.get("id") == job_id:
                job["attempts"] = int(job.get("attempts", 0)) + 1
                job["last_attempt"] = _now_iso()
                job["last_error"] = error or None
        save_pending(jobs)
