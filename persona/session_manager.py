"""
Session Manager

Manages multi-turn problem-solving sessions with:
- Session lifecycle (start, track, conclude)
- Consequence tracking (follow-up on previous outcomes)
- Session replay (context from similar problems)
- Problem continuity (related problems, follow-ups)
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import hashlib
import math


_VALID_STAKES = {"low", "medium", "high"}
_VALID_REVERSIBILITY = {
    "fully_reversible",
    "partially_reversible",
    "irreversible",
    "reversible",  # legacy alias (normalized below)
}


@dataclass
class SessionTurn:
    """Single turn in a session"""
    turn_num: int
    mode: str
    user_input: str
    council_positions: List[str]
    prime_decision: str
    kis_items: List[str]
    user_satisfaction: Optional[bool] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """Complete problem-solving session"""
    session_id: str
    started_at: str
    problem_statement: str
    domains: List[str]
    domain_confidence: float
    stakes: str
    reversibility: str
    turns: List[SessionTurn]
    final_conclusion: Optional[str] = None
    final_satisfaction: Optional[bool] = None
    final_confidence: Optional[float] = None
    ended_at: Optional[str] = None
    parent_session_id: Optional[str] = None  # For follow-ups
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "problem_statement": self.problem_statement,
            "domains": self.domains,
            "domain_confidence": self.domain_confidence,
            "stakes": self.stakes,
            "reversibility": self.reversibility,
            "turns": [asdict(t) for t in self.turns],
            "final_conclusion": self.final_conclusion,
            "final_satisfaction": self.final_satisfaction,
            "final_confidence": self.final_confidence,
            "ended_at": self.ended_at,
            "parent_session_id": self.parent_session_id,
            "turn_count": len(self.turns)
        }


class SessionManager:
    def __init__(self, storage_dir: str = "data/sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        
        self.current_session: Optional[Session] = None
        self.session_history: List[Session] = []
        
        # Consequence tracking file
        self.consequences_file = self.storage_dir / "consequences.jsonl"
        self.problems_file = self.storage_dir / "problems.jsonl"
        
        self._load_history()
    
    def _load_history(self):
        """Load all previous sessions from disk"""
        self.session_history = []
        sessions_dir = self.storage_dir / "completed"
        sessions_dir.mkdir(exist_ok=True, parents=True)
        
        for session_file in sorted(sessions_dir.glob("session_*.json")):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                    # Convert to Session object (simplified)
                    session = Session(
                        session_id=str(session_data.get("session_id", "")),
                        started_at=str(session_data.get("started_at", "")),
                        problem_statement=str(session_data.get("problem_statement", "")),
                        domains=self._normalize_domains(session_data.get("domains", [])),
                        domain_confidence=self._normalize_confidence(
                            session_data.get("domain_confidence", 0.5),
                            default=0.5,
                        ),
                        stakes=self._normalize_stakes(session_data.get("stakes", "medium")),
                        reversibility=self._normalize_reversibility(
                            session_data.get("reversibility", "partially_reversible")
                        ),
                        turns=self._parse_turns(session_data.get("turns", []) or []),
                        final_conclusion=str(session_data.get("final_conclusion", "")) or None,
                        final_satisfaction=session_data.get("final_satisfaction"),
                        final_confidence=self._normalize_confidence(
                            session_data.get("final_confidence", 0.5),
                            default=0.5,
                        ),
                        ended_at=str(session_data.get("ended_at", "")) or None,
                        parent_session_id=str(session_data.get("parent_session_id", "")) or None,
                    )
                    self.session_history.append(session)
            except Exception as e:
                print(f"[SessionManager] Error loading session {session_file}: {e}")
    
    def start_session(
        self,
        problem_statement: str,
        domains: List[str],
        domain_confidence: float,
        stakes: str = "medium",
        reversibility: str = "partially_reversible",
        parent_session_id: Optional[str] = None
    ) -> Session:
        """
        Start a new problem-solving session.
        
        Args:
            problem_statement: The user's problem
            domains: Auto-detected active domains
            domain_confidence: Confidence in domain detection
            stakes: "low", "medium", or "high"
            reversibility: "fully_reversible", "partially_reversible", or "irreversible"
            parent_session_id: If this is a follow-up to a previous session
        """
        normalized_problem = str(problem_statement or "").strip() or "unspecified_problem"
        normalized_domains = self._normalize_domains(domains)
        if not normalized_domains:
            normalized_domains = ["strategy"]
        normalized_confidence = self._normalize_confidence(domain_confidence, default=0.5)
        normalized_stakes = self._normalize_stakes(stakes)
        normalized_reversibility = self._normalize_reversibility(reversibility)
        session_id = self._generate_session_id(normalized_problem)
        
        self.current_session = Session(
            session_id=session_id,
            started_at=self._utc_now_iso(),
            problem_statement=normalized_problem,
            domains=normalized_domains,
            domain_confidence=normalized_confidence,
            stakes=normalized_stakes,
            reversibility=normalized_reversibility,
            turns=[],
            parent_session_id=parent_session_id
        )
        
        print(f"\n[Session {session_id[-8:]}] Started")
        print(f"  Problem: {normalized_problem[:80]}...")
        print(f"  Domains: {', '.join(normalized_domains)}")
        print(f"  Stakes: {normalized_stakes}")
        
        return self.current_session
    
    def add_turn(
        self,
        mode: str,
        user_input: str,
        council_positions: List[str],
        prime_decision: str,
        kis_items: List[str],
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionTurn:
        """
        Record a turn in the current session.
        """
        if not self.current_session:
            raise ValueError("No active session. Call start_session() first.")
        
        normalized_mode = self._normalize_mode(mode)
        normalized_confidence = self._normalize_confidence(confidence, default=0.5)
        turn = SessionTurn(
            turn_num=len(self.current_session.turns) + 1,
            mode=normalized_mode,
            user_input=str(user_input or ""),
            council_positions=list(council_positions or []),
            prime_decision=str(prime_decision),
            kis_items=list(kis_items or []),
            confidence=normalized_confidence,
            metadata=self._to_jsonable(dict(metadata or {})),
        )
        
        self.current_session.turns.append(turn)
        return turn

    def add_structured_turn(
        self,
        *,
        mode: str,
        user_input: str,
        council_result: Optional[Dict[str, Any]] = None,
        prime_decision: Optional[Dict[str, Any]] = None,
        knowledge_result: Optional[Dict[str, Any]] = None,
        domain_analysis: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionTurn:
        """Record a turn using structured pipeline payloads."""
        council_payload = dict(council_result or {})
        prime_payload = dict(prime_decision or {})
        knowledge_payload = dict(knowledge_result or {})
        domain_payload = dict(domain_analysis or {})

        council_positions = self._normalize_council_positions(
            council_payload.get("council_positions", []) or []
        )
        prime_outcome = str(prime_payload.get("final_outcome", "defer"))
        prime_reason = str(prime_payload.get("reason", "unknown"))
        prime_decision_text = f"{prime_outcome}:{prime_reason}"
        kis_items = list(knowledge_payload.get("synthesized_knowledge", []) or [])

        structured_meta = {
            "structured": True,
            "domain_analysis": domain_payload,
            "council": {
                "outcome": council_payload.get("outcome"),
                "recommendation": council_payload.get("recommendation"),
                "consensus_strength": council_payload.get("consensus_strength"),
                "red_line_concerns": council_payload.get("red_line_concerns", []),
            },
            "prime": prime_payload,
            "knowledge_quality": knowledge_payload.get("knowledge_quality", {}),
        }
        if metadata:
            structured_meta.update(dict(metadata))
        structured_meta = self._to_jsonable(structured_meta)

        return self.add_turn(
            mode=mode,
            user_input=user_input,
            council_positions=council_positions,
            prime_decision=prime_decision_text,
            kis_items=kis_items,
            confidence=confidence,
            metadata=structured_meta,
        )

    @staticmethod
    def _normalize_council_positions(council_positions: List[Any]) -> List[str]:
        """Convert heterogeneous council position payloads into stable string lines."""
        normalized: List[str] = []
        for item in list(council_positions or []):
            if isinstance(item, str):
                normalized.append(item)
                continue
            if isinstance(item, dict):
                minister = str(item.get("minister", "unknown"))
                stance = str(item.get("stance", "unknown"))
                confidence = item.get("confidence")
                if confidence is None:
                    normalized.append(f"{minister}:{stance}")
                else:
                    normalized.append(f"{minister}:{stance} ({confidence})")
                continue
            normalized.append(str(item))
        return normalized

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_mode(mode: Any) -> str:
        text = str(mode or "MEETING").strip().upper()
        if not text:
            return "MEETING"
        return text

    @staticmethod
    def _normalize_domains(domains: Any) -> List[str]:
        if isinstance(domains, str):
            raw = [part.strip() for part in domains.split(",")]
        elif isinstance(domains, (list, tuple, set)):
            raw = [str(item).strip() for item in domains]
        else:
            return []

        normalized: List[str] = []
        seen = set()
        for item in raw:
            if not item:
                continue
            value = item.lower()
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    @staticmethod
    def _normalize_confidence(value: Any, *, default: float) -> float:
        try:
            confidence = float(value)
        except Exception:
            confidence = float(default)
        if not math.isfinite(confidence):
            return float(default)

        if confidence < 0.0:
            return 0.0
        if confidence > 1.0:
            return 1.0
        return confidence

    @staticmethod
    def _normalize_stakes(value: Any) -> str:
        stakes = str(value or "medium").strip().lower()
        if stakes not in _VALID_STAKES:
            return "medium"
        return stakes

    @staticmethod
    def _normalize_reversibility(value: Any) -> str:
        reversibility = str(value or "partially_reversible").strip().lower()
        if reversibility == "reversible":
            return "fully_reversible"
        if reversibility not in _VALID_REVERSIBILITY:
            return "partially_reversible"
        return reversibility

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                return 0.0
            return value
        if isinstance(value, dict):
            return {
                str(key): SessionManager._to_jsonable(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [SessionManager._to_jsonable(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc).isoformat()
            return value.isoformat()
        return str(value)

    def _parse_turns(self, raw_turns: Any) -> List[SessionTurn]:
        if not isinstance(raw_turns, list):
            return []

        parsed: List[SessionTurn] = []
        for index, raw in enumerate(raw_turns, start=1):
            if not isinstance(raw, dict):
                continue
            parsed.append(
                SessionTurn(
                    turn_num=int(raw.get("turn_num", index) or index),
                    mode=self._normalize_mode(raw.get("mode", "MEETING")),
                    user_input=str(raw.get("user_input", "")),
                    council_positions=[
                        str(item)
                        for item in list(raw.get("council_positions", []) or [])
                    ],
                    prime_decision=str(raw.get("prime_decision", "")),
                    kis_items=[str(item) for item in list(raw.get("kis_items", []) or [])],
                    user_satisfaction=raw.get("user_satisfaction"),
                    confidence=self._normalize_confidence(raw.get("confidence", 0.5), default=0.5),
                    metadata=self._to_jsonable(dict(raw.get("metadata", {}) or {})),
                )
            )
        return parsed
    
    def should_escalate_mode(self) -> str:
        """
        Determine which mode to use based on turn count and satisfaction.
        
        Returns: "QUICK", "MEETING", "WAR", or "DARBAR"
        """
        if not self.current_session:
            return "QUICK"
        
        turn_count = len(self.current_session.turns)
        
        if turn_count <= 2:
            return "QUICK"
        elif turn_count <= 5:
            return "MEETING"
        elif turn_count <= 8:
            return "WAR"
        else:
            return "DARBAR"
    
    def record_satisfaction(self, satisfied: bool, confidence: float = 0.5):
        """
        Record user's satisfaction after a turn.
        
        Returns: True if session should continue, False if it should end
        """
        if not self.current_session:
            return False
        
        if self.current_session.turns:
            self.current_session.turns[-1].user_satisfaction = satisfied
            self.current_session.turns[-1].confidence = self._normalize_confidence(
                confidence,
                default=0.5,
            )
        
        # Auto-end if satisfied
        if satisfied and confidence > 0.75:
            return False
        
        # Auto-end if too many turns without satisfaction
        if len(self.current_session.turns) > 15:
            return False
        
        return True
    
    def end_session(self, conclusion: str, satisfaction: bool, confidence: float = 0.5):
        """
        End the current session and store it.
        """
        if not self.current_session:
            return None
        
        normalized_confidence = self._normalize_confidence(confidence, default=0.5)
        self.current_session.final_conclusion = str(conclusion or "")
        self.current_session.final_satisfaction = satisfaction
        self.current_session.final_confidence = normalized_confidence
        self.current_session.ended_at = self._utc_now_iso()
        
        # Save to disk
        session_to_save = self.current_session
        self._save_session(session_to_save)
        
        # Add to history
        self.session_history.append(session_to_save)
        
        print(f"\n[Session {session_to_save.session_id[-8:]}] Ended")
        print(f"  Conclusion: {str(conclusion or '')[:100]}...")
        print(f"  Satisfaction: {satisfaction} ({normalized_confidence:.2f} confidence)")
        print(f"  Total turns: {len(session_to_save.turns)}")
        
        # Reset current session
        self.current_session = None
        
        return session_to_save
    
    def _save_session(self, session: Session):
        """Save completed session to disk"""
        completed_dir = self.storage_dir / "completed"
        completed_dir.mkdir(exist_ok=True, parents=True)
        
        session_file = completed_dir / f"session_{session.session_id}.json"
        temp_file = completed_dir / f".session_{session.session_id}.tmp"

        payload = self._to_jsonable(session.to_dict())
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
        temp_file.replace(session_file)
    
    def _generate_session_id(self, problem_statement: str) -> str:
        """Generate unique session ID"""
        import time
        timestamp = str(int(time.time() * 1000))[-10:]  # Last 10 digits of milliseconds
        problem_hash = hashlib.md5(str(problem_statement or "").encode("utf-8")).hexdigest()[:8]
        return f"session_{timestamp}_{problem_hash}"
    
    def find_related_sessions(self, current_domains: List[str], limit: int = 3) -> List[Session]:
        """
        Find previous sessions with similar domains (for problem continuity).
        
        Returns: List of relevant previous sessions
        """
        from persona.domain_detector import domain_similarity
        
        normalized_current_domains = self._normalize_domains(current_domains)
        if not normalized_current_domains:
            return []

        safe_limit = max(0, int(limit or 0))
        if safe_limit == 0:
            return []

        related = []
        for prev_session in self.session_history:
            similarity = domain_similarity(normalized_current_domains, prev_session.domains)
            
            if similarity > 0.3:  # Threshold for relevance
                related.append((similarity, prev_session))
        
        # Sort by similarity, return top N
        related.sort(key=lambda x: x[0], reverse=True)
        return [session for _, session in related[:safe_limit]]
    
    def get_session_context_for_continuity(self, current_domains: List[str]) -> str:
        """
        Get relevant context from previous sessions to inform current session.
        
        Returns: Formatted context string for inclusion in LLM prompts
        """
        related = self.find_related_sessions(current_domains, limit=2)
        
        if not related:
            return ""
        
        context_lines = ["## Previous Related Sessions:\n"]
        
        for session in related:
            context_lines.append(f"### Session {session.session_id[-8:]}")
            context_lines.append(f"Problem: {session.problem_statement}")
            context_lines.append(f"Conclusion: {session.final_conclusion or 'Inconclusive'}")
            context_lines.append(f"User Satisfied: {session.final_satisfaction}")
            context_lines.append("")
        
        return "\n".join(context_lines)
    
    def record_consequence(self, session_id: str, followup: str, outcome: str, timestamp: Optional[str] = None):
        """
        Record what happened after a session concluded (consequence tracking).
        
        This allows learning from whether advice was followed and what outcomes occurred.
        """
        consequence = {
            "session_id": str(session_id),
            "followup": str(followup),  # What the user did
            "outcome": str(outcome),    # What happened
            "recorded_at": str(timestamp or self._utc_now_iso()),
        }
        consequence = self._to_jsonable(consequence)
        
        # Append to consequences log
        with open(self.consequences_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(consequence) + "\n")
        
        print(f"[Consequence] Recorded for session {session_id[-8:]}: {followup[:50]}...")
    
    def load_consequences_for_session(self, session_id: str) -> List[Dict]:
        """
        Load all recorded consequences for a given session.
        """
        consequences = []
        
        if not self.consequences_file.exists():
            return consequences
        
        with open(self.consequences_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    consequence = json.loads(line)
                    if consequence.get("session_id") == session_id:
                        consequences.append(consequence)
                except json.JSONDecodeError:
                    pass
        
        return consequences
    
    def create_followup_session(self, parent_session_id: str, followup_problem: str) -> Session:
        """
        Create a new session explicitly linked as a follow-up to a previous session.
        
        This enables "Follow-up to yesterday's burnout discussion" continuity.
        """
        parent = None
        for session in self.session_history:
            if session.session_id == parent_session_id:
                parent = session
                break
        
        if not parent:
            print(f"[Warning] Parent session {parent_session_id} not found")
        
        # Auto-detect domains for the follow-up
        from persona.domain_detector import analyze_situation
        analysis = analyze_situation(followup_problem)
        
        session = self.start_session(
            problem_statement=followup_problem,
            domains=analysis["domains"],
            domain_confidence=analysis["domain_confidence"],
            stakes=analysis["stakes"],
            reversibility=analysis["reversibility"],
            parent_session_id=parent_session_id
        )
        
        print(f"[Session] This is a follow-up to session {parent_session_id[-8:]}")
        
        return session
    
    def get_session_statistics(self) -> Dict:
        """
        Get summary statistics about all sessions.
        """
        if not self.session_history:
            return {
                "total_sessions": 0,
                "avg_turns": 0,
                "satisfaction_rate": 0,
                "most_common_domains": [],
                "avg_confidence": 0
            }
        
        total_sessions = len(self.session_history)
        total_turns = sum(len(s.turns) for s in self.session_history)
        satisfied_count = sum(1 for s in self.session_history if s.final_satisfaction)
        
        # Domain frequency
        domain_frequency = {}
        for session in self.session_history:
            for domain in session.domains:
                domain_frequency[domain] = domain_frequency.get(domain, 0) + 1
        
        top_domains = sorted(domain_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
        
        avg_confidence = sum(s.final_confidence or 0.5 for s in self.session_history) / total_sessions
        
        return {
            "total_sessions": total_sessions,
            "avg_turns": total_turns / total_sessions,
            "satisfaction_rate": satisfied_count / total_sessions,
            "most_common_domains": [d for d, _ in top_domains],
            "avg_confidence": avg_confidence
        }
