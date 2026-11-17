"""ERA Web API — HTTP wrapper around the persona decision system.

Run with:
    python -m uvicorn api:app --reload --port 8765

Or from project root:
    .venv/Scripts/python -m uvicorn api:app --reload --port 8765
"""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from persona.state import CognitiveState
from persona.context import build_system_context
from persona.analysis import assess_situation, assess_situation_heuristic, classify_situation_single_call
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
        # Try LLM runtimes: OpenRouter (cloud) → sovereign adapter
        llm = None

        # 1. OpenRouter (cloud) — if API key is set
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                from persona.openrouter_runtime import OpenRouterRuntime
                llm = OpenRouterRuntime()
                print(f"[ERA] Using OpenRouter: {llm.speak_model}")
            except Exception as e:
                print(f"[ERA] OpenRouter unavailable: {e}")

        # 2. Sovereign adapter (fallback)
        if llm is None:
            try:
                from sovereign.llm_adapter import OllamaAdapter  # type: ignore[import]
                llm = OllamaAdapter()
            except Exception as e:
                _init_error = str(e)
                raise RuntimeError(f"No LLM runtime available: {e}")

        prime = PrimeConfident(risk_threshold=0.7)
        try:
            from modules.council_execution.engine import NativeCouncil
            council = NativeCouncil(llm=llm)
        except Exception:
            council = CouncilAggregator(llm=llm)
        prime_engine = PrimeDecisionEngine(prime_decider=prime)
        decision_pipeline = DecisionPipelineEngine.create(llm=llm, prime_decider=prime, risk_threshold=0.7)
        brain = PersonaBrain()

        try:
            from ml.ml_orchestrator import MLWisdomOrchestrator
            ml_orchestrator = MLWisdomOrchestrator(cache_dir="ml/cache")
        except Exception:
            ml_orchestrator = None

        _components.update(
            llm=llm,
            prime=prime,
            council=council,
            prime_engine=prime_engine,
            decision_pipeline=decision_pipeline,
            brain=brain,
            ml_orchestrator=ml_orchestrator,
        )
        _init_error = None


# ── Session store ──────────────────────────────────────────────────────────────

def _make_feedback_loop() -> Any:
    try:
        from persona.learning.episodic_memory import EpisodicMemory
        from persona.learning.outcome_feedback import OutcomeFeedbackLoop
        mem = _components.get("episodic_memory")
        if mem is None:
            mem = EpisodicMemory(storage_path=":memory:")
            _components["episodic_memory"] = mem
        council = _components.get("council")
        return OutcomeFeedbackLoop(council=council, episodic_memory=mem)
    except Exception:
        return None


@dataclass
class Session:
    state: CognitiveState = dc_field(default_factory=lambda: _make_state())
    mode_orchestrator: ModeOrchestrator = dc_field(default_factory=ModeOrchestrator)
    dynamic_council: DynamicCouncil = dc_field(default_factory=lambda: DynamicCouncil(llm=None))
    user_id: Optional[str] = None
    profile: Optional[Any] = None
    feedback_loop: Optional[Any] = dc_field(default_factory=_make_feedback_loop)
    session_manager: Optional[Any] = dc_field(default=None)
    pm_session: Optional[Any] = dc_field(default=None)

def _make_state() -> CognitiveState:
    s = CognitiveState()
    s.mode = "meeting"
    return s

_sessions: Dict[str, Session] = {}

def _get_or_create_session(session_id: str) -> Session:
    if session_id not in _sessions:
        try:
            from persona.session_manager import SessionManager
            sm = SessionManager(storage_dir="data/sessions")
        except Exception:
            sm = None
        _sessions[session_id] = Session(session_manager=sm)
    return _sessions[session_id]


# ── Request / response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    mode: str
    turn: int
    domains: list[str]
    domain_confidence: float
    entries_used: list[dict] = []
    deliberation_depth: str = "meeting"  # quick | meeting | darbar


class EntryUsed(BaseModel):
    entry_id: str
    domain: str
    category: str


class FeedbackRequest(BaseModel):
    session_id: str
    turn: int
    helpful: bool
    entries_used: list[EntryUsed] = []
    comment: Optional[str] = None


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
        return classify_situation_single_call(llm, user_input)
    except Exception:
        pass
    try:
        future = _executor.submit(assess_situation, llm, user_input)
        return future.result(timeout=1.0)
    except TimeoutError:
        return assess_situation_heuristic(user_input)
    except Exception:
        return assess_situation_heuristic(user_input)


def _process_turn(state: CognitiveState, user_input: str) -> tuple[str, list[dict], str]:
    """Process a user turn through the 11-stage DecisionPipelineEngine."""
    llm = _components["llm"]
    pipeline = _components.get("decision_pipeline")
    fallback_notices: list[str] = []

    # ── Run the 11-stage pipeline ──────────────────────────────────────────
    if pipeline is not None:
        try:
            result = pipeline.run(
                user_input=user_input,
                requested_mode=state.mode if state.mode != "meeting" else None,
                routing_context={"domains": list(state.domains) if state.domains else []},
                metadata={"session_state": "active"},
            )

            # Extract response from pipeline result
            response = _extract_response_from_pipeline(result, llm, state, user_input)
            deliberation_depth = result.mode_resolution.mode if result.mode_resolution else state.mode
            domains = result.domain_analysis_contract.domains if result.domain_analysis_contract else list(state.domains)
            domain_confidence = result.domain_analysis_contract.domain_confidence if result.domain_analysis_contract else 0.0
            entries_used = _extract_entries_from_pipeline(result)

            # Update state from pipeline results
            if domains:
                state.domains = domains
            state.domain_confidence = domain_confidence
            state.last_situation = {
                "situation_type": "pipeline_resolved",
                "clarity": float(domain_confidence),
                "emotional_load": 0.0,
            }

            # Collect fallback notices from pipeline errors
            if result.pipeline_issues:
                for issue in result.pipeline_issues:
                    if hasattr(issue, "message"):
                        fallback_notices.append(str(issue.message))

        except Exception as e:
            # Pipeline failed — fall through to legacy path
            fallback_notices.append(f"Pipeline failed ({type(e).__name__}: {e}); using legacy path.")
            response, entries_used, deliberation_depth = _process_turn_legacy(state, user_input)
    else:
        # No pipeline — legacy path
        response, entries_used, deliberation_depth = _process_turn_legacy(state, user_input)

    # ── Append fallback notices ─────────────────────────────────────────────
    if fallback_notices:
        unique_notices = sorted(list(set(fallback_notices)))
        response += "\n\n⚠️ **[SYSTEM NOTICE]**: " + "; ".join(unique_notices)

    # ── Update state ────────────────────────────────────────────────────────
    state.recent_turns.append((user_input, response))
    if len(state.recent_turns) > 50:
        state.recent_turns = state.recent_turns[-50:]
    state.turn_count += 1

    # ── Background: episodic memory + pattern feedback ──────────────────────
    try:
        from persona.learning.episodic_memory import EpisodicMemory, Episode
        mem = _components.get("episodic_memory")
        if mem is None:
            mem = EpisodicMemory(storage_path=":memory:")
            _components["episodic_memory"] = mem
        ep = Episode(
            episode_id=None,
            turn_id=state.turn_count,
            domain=(state.domains[0] if state.domains else "general"),
            user_input=user_input[:200],
            persona_recommendation=str(response)[:200],
            confidence=float(state.domain_confidence or 0.5),
            minister_stance=deliberation_depth,
            council_recommendation=deliberation_depth,
        )
        mem.store_episode(ep)
        _executor.submit(_bg_pattern_feedback, mem)
    except Exception:
        pass

    # ── Background: ML recording ────────────────────────────────────────────
    ml_orch = _components.get("ml_orchestrator")
    if ml_orch is not None:
        try:
            _executor.submit(ml_orch.process_decision, user_input)
        except Exception:
            pass

    return response, entries_used, deliberation_depth


def _extract_response_from_pipeline(result, llm, state, user_input: str) -> str:
    """Extract the final response text from a DecisionPipelineResult."""
    # Priority 1: decision_package has a response or advisory_dialogue
    if result.decision_package:
        resp = result.decision_package.get("response") or result.decision_package.get("advisory_dialogue")
        if resp:
            return str(resp)

    # Priority 2: council_result has advisory_dialogue
    if result.council_result:
        resp = result.council_result.get("advisory_dialogue")
        if resp:
            return str(resp)

    # Priority 3: final_decision has recommendation text
    if result.final_decision:
        resp = result.final_decision.get("recommendation")
        if resp and resp != "defer":
            return str(resp)

    # Priority 4: If council was invoked and has minister outputs, synthesize a response
    if result.council_result and result.council_result.get("minister_outputs"):
        ministers = result.council_result["minister_outputs"]
        outcome = result.council_result.get("outcome", "deadlocked")
        consensus = result.council_result.get("consensus_strength", 0.0)
        # Build a brief summary of minister positions
        parts = []
        for name, output in ministers.items():
            if isinstance(output, dict):
                stance = output.get("stance", "neutral")
                reasoning = output.get("reasoning", "")
                if reasoning:
                    parts.append(f"**{name}** ({stance}): {str(reasoning)[:200]}")
        if parts:
            header = f"**Council deliberation** — outcome: {outcome}, consensus: {consensus:.0%}\n\n"
            return header + "\n\n".join(parts)

    # Fallback: direct LLM speak with system context
    system_context = build_system_context(state)
    return llm.speak(system_context, user_input)


def _extract_entries_from_pipeline(result) -> list[dict]:
    """Extract knowledge entries used from pipeline result."""
    entries: list[dict] = []
    if result.knowledge_contract and result.knowledge_contract.synthesized_items:
        for item in result.knowledge_contract.synthesized_items:
            if isinstance(item, dict):
                entries.append({
                    "entry_id": item.get("aku_id", ""),
                    "domain": item.get("_domain", ""),
                    "category": (item.get("type", "principle") or "principle") + "s",
                    "content_preview": str(item.get("content", ""))[:80],
                })
    return entries


def _process_turn_legacy(state: CognitiveState, user_input: str) -> tuple[str, list[dict], str]:
    """Legacy ad-hoc pipeline (fallback when DecisionPipelineEngine is unavailable)."""
    llm = _components["llm"]

    raw_sit = _assess_situation_sync(llm, user_input)
    if not isinstance(raw_sit, dict):
        raw_sit = {}
    state.last_situation = {
        "situation_type": raw_sit.get("situation_type", "unclear"),
        "clarity": float(raw_sit.get("clarity", 0.0)),
        "emotional_load": float(raw_sit.get("emotional_load", 0.0)),
    }
    state.last_emotional_load = state.last_situation["emotional_load"]

    emotional_load = float(raw_sit.get("emotional_load", 0.0))
    clarity = float(raw_sit.get("clarity", 0.5))
    stakes = emotional_load * (1.0 - clarity)
    if state.mode == "quick" or stakes < 0.2:
        deliberation_depth = "quick"
    elif stakes >= 0.5:
        deliberation_depth = "darbar"
    else:
        deliberation_depth = "meeting"

    freq = (
        "low" if len(user_input.split()) <= 3
        else "medium" if len(user_input.split()) <= 12
        else "high"
    )
    state.user_frequency = freq  # type: ignore[attr-defined]

    kis: dict = {}
    entries_used: list[dict] = []
    if state.domains:
        try:
            kis = synthesize_knowledge(
                user_input=user_input,
                active_domains=state.domains,
                domain_confidence=max(state.domain_confidence, 0.5),
            )
            for item in kis.get("synthesized_knowledge", []):
                entries_used.append({
                    "entry_id": item.get("aku_id", ""),
                    "domain": item.get("_domain", ""),
                    "category": (item.get("type", "principle") or "principle") + "s",
                    "content_preview": str(item.get("content", ""))[:80],
                })
        except Exception:
            pass

    system_context = build_system_context(state)
    council = _components.get("council")
    c_res: dict = {}

    if deliberation_depth in ("meeting", "darbar") and council is not None:
        try:
            c_res = council.deliberate(user_input, {"domains": state.domains or ["general"], "mode": deliberation_depth})
            if isinstance(c_res, dict) and c_res.get("advisory_dialogue"):
                response = c_res["advisory_dialogue"]
            else:
                response = llm.speak(system_context, user_input)
        except Exception as e:
            response = llm.speak(system_context, user_input)
    else:
        response = llm.speak(system_context, user_input)

    return response, entries_used, deliberation_depth


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


def _bg_pattern_feedback(mem) -> None:
    """Extract patterns from episodic memory and feed weak domains back into minister confidence."""
    try:
        from ml.pattern_extraction import PatternExtractor
        from persona.learning.minister_confidence import MinisterConfidenceTracker

        extractor = PatternExtractor(episodic_memory=mem)
        extractor.extract_patterns(num_episodes=100)
        signals = extractor.generate_learning_signals()

        weak_domains = signals.get("weak_domains", [])
        if not weak_domains:
            return

        tracker = MinisterConfidenceTracker(storage_path="data/memory/minister_confidence.json")
        ministers = ["risk", "grand_strategist", "optionality", "psychology", "timing"]

        for weak in weak_domains:
            domain = weak.get("domain", "")
            success_rate = weak.get("success_rate", 1.0)
            if success_rate >= 0.5:
                continue
            # Penalize all ministers for this weak domain
            for minister in ministers:
                tracker.record_outcome(minister, domain, success=False)

        # Save patterns for diagnostics
        extractor.save_patterns("ml/cache/extracted_patterns.json")
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

    # Attach user profile on first mention of user_id
    if req.user_id and session.user_id is None:
        session.user_id = req.user_id
        try:
            from persona.user_profile import get_or_create_profile
            session.profile = get_or_create_profile(req.user_id)
            state.profile_hint = session.profile.to_context_hint()  # type: ignore[attr-defined]
        except Exception:
            pass

    response, entries_used, deliberation_depth = _process_turn(state, req.message.strip())

    # Periodic retrain check every 5 turns (background, non-blocking)
    if session.feedback_loop is not None and state.turn_count % 5 == 0:
        try:
            _executor.submit(session.feedback_loop.check_and_retrain)
        except Exception:
            pass

    # Update profile stats after response
    if session.profile is not None:
        try:
            import datetime as _dt
            from persona.user_profile import save_profile
            session.profile.total_turns += 1
            session.profile.update_themes(list(state.domains))
            session.profile.last_active = _dt.datetime.now(_dt.timezone.utc).isoformat()
            save_profile(session.profile)
        except Exception:
            pass

    # SessionManager — start session on first turn, record each turn
    if session.session_manager is not None:
        try:
            if session.pm_session is None:
                session.pm_session = session.session_manager.start_session(
                    problem_statement=req.message.strip()[:500],
                    domains=list(state.domains),
                    domain_confidence=float(state.domain_confidence),
                    stakes="medium",
                    reversibility="partially_reversible",
                )
            session.session_manager.add_turn(
                mode=state.mode,
                user_input=req.message.strip()[:200],
                council_positions=[deliberation_depth],
                prime_decision=response[:200],
                kis_items=[e.get("entry_id", "") for e in entries_used],
                confidence=float(state.domain_confidence),
            )
        except Exception:
            pass

    return ChatResponse(
        session_id=session_id,
        response=response,
        mode=state.mode,
        turn=state.turn_count,
        domains=list(state.domains),
        domain_confidence=float(state.domain_confidence),
        entries_used=entries_used,
        deliberation_depth=deliberation_depth,
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


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest) -> Dict[str, Any]:
    """Record whether advice for a turn was helpful. Updates minister knowledge weights."""
    from persona.knowledge_engine import reinforce_entry

    updated = 0
    for entry in req.entries_used:
        ok = reinforce_entry(
            entry_id=entry.entry_id,
            domain=entry.domain,
            category=entry.category,
            positive=req.helpful,
        )
        if ok:
            updated += 1

    session = _sessions.get(req.session_id)
    mem = _components.get("episodic_memory")
    if mem:
        try:
            mem.update_outcome_for_turn(req.turn, "success" if req.helpful else "failure")
        except Exception:
            pass

    # Record outcome into MinisterConfidenceTracker for each domain in this turn
    try:
        _ct_mod = __import__("persona.learning.minister_confidence", fromlist=["MinisterConfidenceTracker"])
        tracker = _ct_mod.MinisterConfidenceTracker(storage_path="data/memory/minister_confidence.json")
        seen_domains: set = set()
        for entry in req.entries_used:
            domain = entry.domain or "general"
            if domain not in seen_domains:
                # Record outcome for every minister that deliberated on this domain
                for minister in ["risk", "grand_strategist", "optionality", "psychology", "timing"]:
                    tracker.record_outcome(minister, domain, success=req.helpful)
                seen_domains.add(domain)
    except Exception:
        pass

    return {
        "session_id": req.session_id,
        "turn": req.turn,
        "helpful": req.helpful,
        "updated": updated,
    }


@app.get("/profile/{user_id}")
def get_profile(user_id: str) -> Dict[str, Any]:
    from persona.user_profile import load_profile
    from dataclasses import asdict
    profile = load_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return asdict(profile)


class ObsidianExportRequest(BaseModel):
    vault_path: Optional[str] = None  # overrides ERA_OBSIDIAN_VAULT env var
    episodes_path: str = "data/memory/episodes.jsonl"
    profiles_dir: str = "data/user_profiles"
    confidence_path: str = "data/memory/minister_confidence.json"


@app.post("/export/obsidian")
def export_obsidian(req: ObsidianExportRequest) -> Dict[str, Any]:
    """Export ERA memory to an Obsidian vault as Markdown notes.

    Set the ERA_OBSIDIAN_VAULT environment variable to your vault path,
    or pass vault_path in the request body.

    Creates:
      ERA/ERA_Dashboard.md          — summary with Dataview queries
      ERA/Episodes/turn_NNNN_*.md  — one note per episode
      ERA/Profiles/{user_id}.md    — user profile notes
      ERA/Learning/failure_clusters.md
      ERA/Learning/knowledge_gaps.md
      ERA/Learning/minister_confidence.md
    """
    from persona.obsidian_exporter import export_to_obsidian

    # Collect current knowledge gaps from last KIS call if available
    gaps: list[str] = []
    for sess in _sessions.values():
        bg = getattr(sess.state, "background_knowledge", None)
        if isinstance(bg, dict):
            gaps.extend(bg.get("knowledge_gaps", []))
    gaps = list(set(gaps))

    try:
        result = export_to_obsidian(
            vault_path=req.vault_path or None,
            episodes_path=req.episodes_path,
            profiles_dir=req.profiles_dir,
            confidence_path=req.confidence_path,
            knowledge_gaps=gaps,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    return result


class SimulateRequest(BaseModel):
    problem: str
    turns: int = 5
    user_id: Optional[str] = None


@app.post("/simulate")
def simulate(req: SimulateRequest) -> Dict[str, Any]:
    """Run a multi-turn HSE simulation: synthetic human vs persona advisor."""
    try:
        _init_components()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        from hse.human_profile import SyntheticHuman
        from hse.simulation.synthetic_human_sim import SyntheticHumanSimulation
        from persona.state import CognitiveState
        from persona.context import build_system_context
        from persona.analysis import classify_situation_single_call

        llm = _components["llm"]
        human = SyntheticHuman(name="Test Subject", age=32, seed=42)
        sim = SyntheticHumanSimulation(human, user_llm=llm)

        state = CognitiveState()
        state.mode = "meeting"
        conversation: list[dict] = []

        user_input = req.problem
        for turn in range(req.turns):
            classified = classify_situation_single_call(llm, user_input)
            state.domains = classified.get("domains", ["general"])
            state.domain_confidence = classified.get("domain_confidence", 0.5)

            system_context = build_system_context(state)
            response = llm.speak(system_context, user_input)

            conversation.append({"turn": turn + 1, "human": user_input, "persona": response})

            user_input = sim.generate_next_input(response, {"domains": state.domains})

        return {
            "problem": req.problem,
            "turns_run": len(conversation),
            "conversation": conversation,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")
