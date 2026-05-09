"""ERA Web API — HTTP wrapper around the persona decision system.

Run with:
    python -m uvicorn api:app --reload --port 8765

Or from project root:
    .venv/Scripts/python -m uvicorn api:app --reload --port 8765
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from persona.state import CognitiveState
from persona.context import build_system_context
from persona.analysis import assess_situation, assess_situation_heuristic
from persona.brain import PersonaBrain
from persona.knowledge_engine import synthesize_knowledge
from persona.council import CouncilAggregator
from persona.modes.mode_orchestrator import ModeOrchestrator
from persona.council.dynamic_council import DynamicCouncil
from sovereign.prime_confident import PrimeConfident
from modules.decision_pipeline import DecisionPipelineEngine
from modules.prime_decision import PrimeDecisionEngine


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="ERA — Emergent Reasoning Architecture", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup: initialise ERA components once ───────────────────────────────────

import threading
from dataclasses import dataclass, field as dc_field

_executor = ThreadPoolExecutor(max_workers=4)
_components: Dict[str, Any] = {}
_init_error: Optional[str] = None
_init_lock = threading.Lock()


def _init_components() -> None:
    global _init_error
    if _components:          # fast path, no lock needed (dict reads are atomic in CPython)
        return
    with _init_lock:
        if _components:      # re-check inside lock
            return
        try:
            from persona.ollama_runtime import OllamaRuntime
            llm = OllamaRuntime()
        except Exception:
            try:
                from sovereign.llm_adapter import OllamaAdapter  # type: ignore[import]
                llm = OllamaAdapter()
            except Exception as e:
                _init_error = str(e)
                raise RuntimeError(f"No LLM runtime available: {e}")

        prime = PrimeConfident(risk_threshold=0.7)
        council = CouncilAggregator(llm=llm)
        prime_engine = PrimeDecisionEngine(prime_decider=prime)
        decision_pipeline = DecisionPipelineEngine.create(llm=llm, prime_decider=prime, risk_threshold=0.7)
        brain = PersonaBrain()

        _components.update(
            llm=llm,
            prime=prime,
            council=council,
            prime_engine=prime_engine,
            decision_pipeline=decision_pipeline,
            brain=brain,
        )
        _init_error = None


# ── Session store ──────────────────────────────────────────────────────────────

@dataclass
class Session:
    state: CognitiveState = dc_field(default_factory=lambda: _make_state())
    mode_orchestrator: ModeOrchestrator = dc_field(default_factory=ModeOrchestrator)
    dynamic_council: DynamicCouncil = dc_field(default_factory=lambda: DynamicCouncil(llm=None))

def _make_state() -> CognitiveState:
    s = CognitiveState()
    s.mode = "meeting"
    return s

_sessions: Dict[str, Session] = {}

def _get_or_create_session(session_id: str) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session()
    return _sessions[session_id]


# ── Request / response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: Optional[str] = None  # override mode for this session


class ChatResponse(BaseModel):
    session_id: str
    response: str
    mode: str
    turn: int
    domains: list[str]
    domain_confidence: float


class ModeRequest(BaseModel):
    session_id: str
    mode: str  # quick | war | meeting | darbar


class SessionInfo(BaseModel):
    session_id: str
    mode: str
    turn: int
    domains: list[str]
    domain_confidence: float
    recent_turns: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assess_situation_sync(llm: Any, user_input: str) -> Dict[str, Any]:
    try:
        future = _executor.submit(assess_situation, llm, user_input)
        return future.result(timeout=1.0)
    except TimeoutError:
        return assess_situation_heuristic(user_input)
    except Exception:
        return assess_situation_heuristic(user_input)


def _process_turn(state: CognitiveState, user_input: str) -> str:
    llm = _components["llm"]

    # Situation assessment
    raw_sit = _assess_situation_sync(llm, user_input)
    if not isinstance(raw_sit, dict):
        raw_sit = {}
    state.last_situation = {
        "situation_type": raw_sit.get("situation_type", "unclear"),
        "clarity": float(raw_sit.get("clarity", 0.0)),
        "emotional_load": float(raw_sit.get("emotional_load", 0.0)),
    }
    state.last_emotional_load = state.last_situation["emotional_load"]

    freq = (
        "low" if len(user_input.split()) <= 3
        else "medium" if len(user_input.split()) <= 12
        else "high"
    )
    state.user_frequency = freq  # type: ignore[attr-defined]

    system_context = build_system_context(state)
    response = llm.speak(system_context, user_input)

    state.recent_turns.append((user_input, response))
    if len(state.recent_turns) > 50:
        state.recent_turns = state.recent_turns[-50:]
    state.turn_count += 1

    display = response

    # Background: KIS synthesis (fire-and-forget, don't block)
    if state.domains:
        try:
            _executor.submit(
                _bg_kis, state, user_input
            )
        except Exception:
            pass

    return display


def _bg_kis(state: CognitiveState, user_input: str) -> None:
    try:
        kis = synthesize_knowledge(
            user_input=user_input,
            active_domains=state.domains,
            domain_confidence=max(state.domain_confidence, 0.5),
        )
        state.background_knowledge = kis  # type: ignore[assignment]
    except Exception:
        pass


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> Dict[str, str]:
    if _components:
        return {"status": "ok", "llm": type(_components["llm"]).__name__}
    if _init_error:
        return {"status": "degraded", "error": _init_error}
    return {"status": "starting"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")
    try:
        _init_components()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    session_id = req.session_id or str(uuid.uuid4())
    session = _get_or_create_session(session_id)
    state = session.state
    mo = session.mode_orchestrator
    dc = session.dynamic_council

    if req.mode:
        if mo.set_mode(req.mode):
            dc.set_mode(req.mode)
            state.mode = req.mode
        else:
            raise HTTPException(status_code=400, detail=f"Unknown mode '{req.mode}'. Valid: {mo.list_modes()}")

    response = _process_turn(state, req.message.strip())

    return ChatResponse(
        session_id=session_id,
        response=response,
        mode=state.mode,
        turn=state.turn_count,
        domains=list(state.domains),
        domain_confidence=float(state.domain_confidence),
    )


@app.post("/mode")
def set_mode(req: ModeRequest) -> Dict[str, str]:
    try:
        _init_components()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    session = _get_or_create_session(req.session_id)
    mo = session.mode_orchestrator
    dc = session.dynamic_council

    if not mo.set_mode(req.mode):
        raise HTTPException(status_code=400, detail=f"Unknown mode '{req.mode}'. Valid: {mo.list_modes()}")

    dc.set_mode(req.mode)
    session.state.mode = req.mode
    return {"session_id": req.session_id, "mode": req.mode, "status": "ok"}


@app.get("/session/{session_id}", response_model=SessionInfo)
def session_info(session_id: str) -> SessionInfo:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[session_id]
    state = session.state
    return SessionInfo(
        session_id=session_id,
        mode=state.mode,
        turn=state.turn_count,
        domains=list(state.domains),
        domain_confidence=float(state.domain_confidence),
        recent_turns=len(state.recent_turns),
    )


@app.delete("/session/{session_id}")
def reset_session(session_id: str) -> Dict[str, str]:
    _sessions.pop(session_id, None)
    return {"session_id": session_id, "status": "reset"}


@app.get("/sessions")
def list_sessions() -> Dict[str, Any]:
    return {
        "count": len(_sessions),
        "sessions": [
            {"session_id": sid, "mode": s.state.mode, "turns": s.state.turn_count}
            for sid, s in _sessions.items()
        ],
    }
