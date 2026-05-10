import json
import math
import os
import re
import datetime
from typing import Dict, List, Any, Optional, Tuple


# -----------------------------
# CONFIG
import pathlib as _pathlib

_PROJECT_ROOT = _pathlib.Path(__file__).resolve().parent.parent
BASE_PATH = str(os.environ.get("ERA_MINISTER_PATH") or _PROJECT_ROOT / "data" / "ministers")

KNOWLEDGE_TYPES = ["principle", "rule", "warning", "claim", "advice"]

TYPE_WEIGHT = {
    "principle": 1.0,
    "rule": 1.1,
    "warning": 1.05,
    "claim": 0.95,
    "advice": 0.9
}

# Posture bias mapping (from design doc)
POSTURE_TYPE_BIAS = {
    "cautious": {"principle": 1.2, "rule": 1.4, "warning": 1.05, "claim": 0.95, "advice": 0.9},
    "bold": {"principle": 1.0, "rule": 0.7, "warning": 0.9, "claim": 1.0, "advice": 1.3},
    "analytical": {"principle": 1.4, "rule": 1.3, "warning": 1.05, "claim": 0.95, "advice": 0.9},
    "creative": {"principle": 1.0, "rule": 0.6, "warning": 1.0, "claim": 0.95, "advice": 1.4},
    "empathetic": {"principle": 1.3, "rule": 0.8, "warning": 1.05, "claim": 0.95, "advice": 1.2},
}


# -----------------------------
# UTILITIES
# -----------------------------
def load_json_safe(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def extract_keywords(text: str) -> List[str]:
    words = re.findall(r"\b[\w']{4,}\b", text.lower())
    return words


# -----------------------------
# WEIGHT FUNCTIONS
# -----------------------------
def domain_weight(domain: str, active_domains: List[str], confidence: float) -> float:
    base = 0.25
    if domain in active_domains:
        return max(confidence, 0.5)
    return base


def memory_weight(entry: Dict[str, Any]) -> float:
    mem = entry.get("memory", {})
    rc = float(mem.get("reinforcement_count", 0) or 0)
    penalty = float(mem.get("penalty_count", 0) or 0)
    # age support
    last = mem.get("last_reinforced_date")
    age_days = None
    try:
        if last:
            if isinstance(last, (int, float)):
                # epoch seconds
                dt = datetime.datetime.fromtimestamp(float(last))
            else:
                dt = datetime.datetime.fromisoformat(str(last))
            now = datetime.datetime.now(datetime.timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            age_days = (now - dt).days
    except Exception:
        age_days = None

    base = 1.0 + math.log(1 + max(0.0, rc))
    # penalty exponential decay
    if penalty and penalty > 0:
        base = base * math.exp(-0.3 * float(penalty))
    # aging decay (180-day half-life)
    if age_days is not None:
        try:
            base = base * math.exp(-float(age_days) / 180.0)
        except Exception:
            pass
    return max(0.01, float(base))


def context_weight(entry: Dict[str, Any], user_input: str) -> float:
    keywords = extract_keywords(user_input)
    content = entry.get("content", "").lower()

    if not keywords or not content:
        return 0.8

    matches = sum(1 for k in keywords if k in content)

    if matches >= 2:
        return 1.4
    if matches == 1:
        return 1.2
    return 0.85


def _semantic_label_similarity(labels: List[str], targets: List[str]) -> float:
    """
    Lightweight semantic label similarity: If exact label matches target substrings,
    return high score. Otherwise return a lower partial-match score based on token overlap.
    This is a fallback when real embeddings are not available.
    """
    if not labels or not targets:
        return 0.0
    lab_l = [l.lower() for l in labels if isinstance(l, str)]
    targ_l = [t.lower() for t in targets if isinstance(t, str)]
    for l in lab_l:
        for t in targ_l:
            if l == t or l in t or t in l:
                return 0.95
    # partial token overlap
    score = 0.0
    for l in lab_l:
        lset = set(re.findall(r"\w+", l))
        for t in targ_l:
            tset = set(re.findall(r"\w+", t))
            if not lset or not tset:
                continue
            overlap = len(lset & tset) / max(1, len(lset | tset))
            if overlap > score:
                score = overlap
    return float(score)


def goal_weight(entry: Dict[str, Any]) -> float:
    text = entry.get("content", "").lower()

    if any(w in text for w in ["dependency", "long-term", "trajectory", "control"]):
        return 1.2
    if any(w in text for w in ["temporary", "short-term", "relief"]):
        return 0.7
    return 1.0


def applies_applicability(entry: Dict[str, Any], situation_frame: Optional[Dict[str, Any]]) -> float:
    """
    Check applicability constraints on an entry against the situation_frame.
    Returns 0.0 if inapplicable, or 1.0 for pass, or intermediate score for partial matches.
    """
    if not situation_frame:
        return 1.0
    constraints = entry.get("applicability_constraints") or {}
    if not constraints:
        return 1.0
    # required domains
    req = constraints.get("required_domains") or []
    exc = constraints.get("excluded_domains") or []
    domain = situation_frame.get("domain")
    if req:
        if not domain or all(r not in (domain or "") for r in req):
            return 0.0
    if exc and domain and any(e in (domain or "") for e in exc):
        return 0.0
    # time pressure and stakes checks are coarse
    min_stakes = constraints.get("min_stakes")
    max_time = constraints.get("max_time_pressure")
    # if provided but not satisfied, degrade score
    score = 1.0
    stakes = situation_frame.get("stakes")
    tp = situation_frame.get("time_pressure")
    if min_stakes and stakes:
        # simplistic ordering mapping
        order = {"low": 0, "medium": 1, "high": 2}
        if order.get(stakes, 0) < order.get(min_stakes, 0):
            return 0.0
    if max_time and tp:
        order = {"low": 0, "medium": 1, "high": 2}
        if order.get(tp, 0) > order.get(max_time, 2):
            return 0.0
    return float(score)


# -----------------------------
# CORE ENGINE
# -----------------------------
def compute_kis(
    entry: Dict[str, Any],
    domain: str,
    active_domains: List[str],
    domain_confidence: float,
    user_input: str,
    posture: Optional[str] = None,
    situation_frame: Optional[Dict[str, Any]] = None,
) -> float:
    # Applicability pre-filter
    appl = applies_applicability(entry, situation_frame)
    if appl <= 0.0:
        return 0.0

    # Domain weight: blend simple membership and semantic concept tags when available
    dw = domain_weight(domain, active_domains, domain_confidence)
    # semantic concept tags adjustment
    concept_tags = entry.get("concept_tags") or []
    if concept_tags and isinstance(concept_tags, list):
        labels = [ct.get("label") if isinstance(ct, dict) else str(ct) for ct in concept_tags]
        sem = _semantic_label_similarity(labels, active_domains)
        # interpolate: prefer semantic when available
        dw = max(dw, sem * (domain_confidence or 1.0))

    # Type weight with posture adjustment
    base_tw = TYPE_WEIGHT.get(entry.get("type"), 0.9)
    if posture and posture in POSTURE_TYPE_BIAS:
        bias_map = POSTURE_TYPE_BIAS.get(posture, {})
        posture_mul = bias_map.get(entry.get("type"), 1.0)
    else:
        posture_mul = 1.0
    tw = base_tw * posture_mul

    # Memory (includes reinforcement, penalties, aging)
    mw = memory_weight(entry)

    # Context and goal weights — prefer semantic tag matching when available
    cw = context_weight(entry, user_input)
    goal_tags = entry.get("goal_tags") or []
    if goal_tags and isinstance(goal_tags, list):
        semg = _semantic_label_similarity([g if isinstance(g, str) else str(g) for g in goal_tags], [user_input])
        cw = max(cw, 0.5 + semg * 0.5)

    gw = goal_weight(entry)

    score = float(dw * tw * mw * cw * gw)
    return max(0.0, score)


def load_domain_knowledge(domain: str) -> List[Dict[str, Any]]:
    domain_path = os.path.join(BASE_PATH, domain)
    knowledge = []

    for ktype in KNOWLEDGE_TYPES:
        file_path = os.path.join(domain_path, f"{ktype}s.json")
        data = load_json_safe(file_path)
        
        # Handle nested structure: data might be {domain, category, entries: [...]}
        if isinstance(data, dict) and "entries" in data:
            entries = data.get("entries", [])
        elif isinstance(data, list):
            entries = data
        else:
            entries = []
        
        for e in entries:
            # Normalize field names to match what compute_kis expects
            normalized = {
                "aku_id": e.get("id", ""),
                "content": e.get("text", ""),
                "type": ktype.rstrip("s"),  # "principles" -> "principle"
                "_domain": domain,
                "source": e.get("source", {}),
                "memory": {
                    "reinforcement_count": int(e.get("weight", 1.0) * 10) if e.get("weight") else 1
                }
            }
            knowledge.append(normalized)

    return knowledge


def reinforce_entry(entry_id: str, domain: str, category: str, positive: bool = True) -> bool:
    """Increment reinforcement_count (positive=True) or penalty_count (positive=False).

    Writes back to the minister JSON file. Returns True if entry was found and updated.
    category: 'principles' | 'rules' | 'warnings' | 'claims'
    """
    import datetime as _dt
    import json
    import os
    import pathlib as _pathlib
    file_path = os.path.join(BASE_PATH, domain, f"{category}.json")
    if not os.path.isfile(file_path):
        return False
    try:
        data = json.loads(_pathlib.Path(file_path).read_text(encoding="utf-8"))
        entries = data.get("entries", [])
        for entry in entries:
            if entry.get("id") == entry_id:
                mem = entry.setdefault("memory", {})
                if positive:
                    mem["reinforcement_count"] = mem.get("reinforcement_count", 0) + 1
                    mem["last_reinforced_date"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
                else:
                    mem["penalty_count"] = mem.get("penalty_count", 0) + 1
                _pathlib.Path(file_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
                # Invalidate Chroma collection so next query re-indexes updated weights
                global _chroma_collection
                _chroma_collection = None
                return True
    except Exception:
        pass
    return False


_BUILTIN_ENTRIES = [
    {
        "aku_id": "builtin-1",
        "content": "Quitting without a financial buffer increases long-term risk to income and retirement.",
        "type": "warning",
        "source": {"book": "builtin:career_risk"},
        "memory": {"reinforcement_count": 2},
        "_domain": "risk",
    },
    {
        "aku_id": "builtin-2",
        "content": "Plan alternatives and preserve optionality: negotiate, freelance, or part-time work first.",
        "type": "advice",
        "source": {"book": "builtin:optionality_guide"},
        "memory": {"reinforcement_count": 1},
        "_domain": "optionality",
    },
    {
        "aku_id": "builtin-3",
        "content": "Stress and burnout often follow unresolved workload and misaligned incentives; address root causes early.",
        "type": "principle",
        "source": {"book": "builtin:psychology_of_work"},
        "memory": {"reinforcement_count": 3},
        "_domain": "psychology",
    },
    {
        "aku_id": "builtin-4",
        "content": "Prioritize emergency savings covering 3-6 months of expenses before making major job moves.",
        "type": "rule",
        "source": {"book": "builtin:personal_finance"},
        "memory": {"reinforcement_count": 4},
        "_domain": "risk",
    },
    {
        "aku_id": "builtin-5",
        "content": "Decisions labelled irreversible require documenting commitments and contingency plans.",
        "type": "principle",
        "source": {"book": "builtin:decision_theory"},
        "memory": {"reinforcement_count": 2},
        "_domain": "strategy",
    },
    {
        "aku_id": "builtin-6",
        "content": "Shifts in relative power often follow technological adoption curves; monitor diffusion metrics and chokepoints.",
        "type": "claim",
        "source": {"book": "builtin:power_technology"},
        "memory": {"reinforcement_count": 3},
        "_domain": "power",
    },
    {
        "aku_id": "builtin-7",
        "content": "Invest in resilient communications and counter-intelligence to mitigate remote sensing and collection risks.",
        "type": "advice",
        "source": {"book": "builtin:intel_and_comm"},
        "memory": {"reinforcement_count": 2},
        "_domain": "technology",
    },
]

# ── Chroma vector retrieval (optional, graceful degradation) ──────────────────
import threading as _threading

_chroma_lock = _threading.Lock()
_chroma_collection = None
_CHROMA_COLLECTION_NAME = "era_minister_knowledge"


def _get_chroma_collection():
    """Return the Chroma collection, building it on first call. Thread-safe."""
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection
    with _chroma_lock:
        if _chroma_collection is not None:
            return _chroma_collection
        try:
            import chromadb
        except ImportError:
            return None
        try:
            client = chromadb.PersistentClient(
                path=str(_pathlib.Path(BASE_PATH).parent.parent / "chroma_knowledge")
            )
            col = client.get_or_create_collection(
                name=_CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            if col.count() == 0:
                _index_minister_knowledge(col)
            _chroma_collection = col
            return col
        except Exception:
            return None

def _index_minister_knowledge(col) -> None:
    """Populate Chroma with all minister JSON entries."""
    if not os.path.isdir(BASE_PATH):
        return
    documents, metadatas, ids = [], [], []
    for domain in os.listdir(BASE_PATH):
        domain_path = os.path.join(BASE_PATH, domain)
        if not os.path.isdir(domain_path):
            continue
        for ktype in KNOWLEDGE_TYPES:
            file_path = os.path.join(domain_path, f"{ktype}s.json")
            raw = load_json_safe(file_path)
            entries = raw.get("entries", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            for entry in entries:
                text = str(entry.get("text", "")).strip()
                if not text:
                    continue
                doc_id = str(entry.get("id", "")) or f"{domain}_{ktype}_{len(ids)}"
                documents.append(text)
                metadatas.append({
                    "domain": domain,
                    "type": ktype.rstrip("s"),
                    "book": str(entry.get("source", {}).get("book", "")),
                    "weight": float(entry.get("weight", 1.0)),
                })
                ids.append(doc_id)
    if documents:
        # Chroma accepts up to 5461 items per add call
        batch = 500
        for i in range(0, len(documents), batch):
            col.add(
                documents=documents[i:i+batch],
                metadatas=metadatas[i:i+batch],
                ids=ids[i:i+batch],
            )


def synthesize_knowledge(
    user_input: str,
    active_domains: List[str],
    domain_confidence: float,
    max_items: int = 5,
    extra_context: List[str] | None = None,
) -> Dict[str, Any]:
    all_entries = []

    # ── Try Chroma semantic retrieval ──────────────────────────────────────────
    try:
        col = _get_chroma_collection()
        n_results = min(max_items * 4, col.count()) if col else 0
        if n_results > 0:
            results = col.query(
                query_texts=[user_input],
                n_results=n_results,
                where={"domain": {"$in": active_domains}} if active_domains else None,
            )
            for text, meta in zip(results["documents"][0], results["metadatas"][0]):
                all_entries.append({
                    "aku_id": "",
                    "content": text,
                    "type": meta.get("type", "principle"),
                    "_domain": meta.get("domain", ""),
                    "source": {"book": meta.get("book", "")},
                    "memory": {"reinforcement_count": int(float(meta.get("weight", 1.0)) * 10)},
                })
    except Exception:
        pass

    # ── Fall back to full file scan if Chroma unavailable ─────────────────────
    if not all_entries and os.path.isdir(BASE_PATH):
        try:
            for domain in os.listdir(BASE_PATH):
                domain_path = os.path.join(BASE_PATH, domain)
                if not os.path.isdir(domain_path):
                    continue
                all_entries.extend(load_domain_knowledge(domain))
        except Exception:
            all_entries = []

    # ── Final fallback: 7 builtins ────────────────────────────────────────────
    if not all_entries:
        all_entries = _BUILTIN_ENTRIES   # move the existing builtin list to a module-level constant

    try:
        print(f"[KIS DEBUG] total entries available for scoring: {len(all_entries)}")
    except Exception:
        pass

    total_entries_available = len(all_entries)
    scored = []

    # If extra_context is provided (answers to clarifying questions, etc.),
    # combine it with the user_input so scoring takes it into account.
    combined_context = user_input
    if extra_context:
        try:
            combined_context = user_input + "\n\n" + "\n\n".join([str(x) for x in extra_context if x])
        except Exception:
            combined_context = user_input

    for entry in all_entries:
        content = entry.get("content")
        if not content or not isinstance(content, str):
            continue
        domain = entry.get("_domain")
        kis = compute_kis(entry, domain, active_domains, domain_confidence, combined_context)
        scored.append((kis, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = scored[:max_items]

    synthesized = []
    backtrace = []
    top_kis = [round(s, 3) for s, _ in scored[:5]]

    knowledge_debug = {
        "total_entries_scanned": total_entries_available,
        "top_kis_scores": top_kis,
    }

    for score, entry in selected:
        synthesized.append({
            "aku_id": entry.get("aku_id", ""),
            "content": entry.get("content", ""),
            "type": entry.get("type", "principle"),
            "_domain": entry.get("_domain", ""),
            "source": entry.get("source", {}),
            "kis_score": round(score, 4),
        })
        backtrace.append({
            "aku_id": entry.get("aku_id"),
            "domain": entry.get("_domain"),
            "type": entry.get("type"),
            "source": entry.get("source", {}),
            "kis": round(score, 3)
        })

    def _clean_book_name(name: str) -> str:
        if not name or not isinstance(name, str):
            return ""
        n = name
        n = re.sub(r"\.(pdf|txt|epub|mobi)$", "", n, flags=re.IGNORECASE)
        n = re.sub(r"[_\-]+", " ", n)
        n = re.sub(r"^[0-9]{2,4}([_\-:]|\s)+", "", n)
        n = n.strip()
        n = re.sub(r"\s+", " ", n)
        return n

    books_scanned = set()
    for e in all_entries:
        src = e.get("source", {}) or {}
        book = src.get("book") or src.get("title") or src.get("file")
        if book:
            books_scanned.add(book)

    selected_books = set()
    for _, e in selected:
        src = e.get("source", {}) or {}
        book = src.get("book") or src.get("title") or src.get("file")
        if book:
            selected_books.add(book)

    books_list = sorted(list(books_scanned))
    selected_books_list = sorted(list(selected_books))
    cleaned_books = [_clean_book_name(b) for b in books_list]
    cleaned_selected = [_clean_book_name(b) for b in selected_books_list]

    knowledge_debug.update({
        "num_books_scanned": len(books_scanned),
        "books_scanned": cleaned_books,
        "num_selected": len(selected),
        "selected_books": cleaned_selected,
    })

    for item in backtrace:
        src = item.get("source") or {}
        raw_book = src.get("book") or src.get("title") or src.get("file")
        item["book"] = raw_book
        item["book_clean"] = _clean_book_name(raw_book)

    # Contradiction detection (simple heuristic): look for pairs with high domain overlap
    # but opposing polarity markers. This is a heuristic placeholder for a richer LLM check.
    def _detect_contradictions(selected_entries: List[Dict[str, Any]]) -> List[Tuple[str, str, float]]:
        contradictions = []
        try:
            for i in range(len(selected_entries)):
                for j in range(i + 1, len(selected_entries)):
                    a = selected_entries[i]
                    b = selected_entries[j]
                    # domain similarity via _semantic_label_similarity on their domains/tags
                    dom_a = [a.get("_domain") or ""]
                    dom_b = [b.get("_domain") or ""]
                    dom_sim = _semantic_label_similarity(dom_a, dom_b)
                    if dom_sim < 0.4:
                        continue
                    ca = (a.get("content") or "").lower()
                    cb = (b.get("content") or "").lower()
                    # crude contradiction signal: presence of negation words in one and affirmative in other
                    neg = any(w in ca for w in ("not ", "never ", "avoid ", "don't ", "do not "))
                    neg2 = any(w in cb for w in ("not ", "never ", "avoid ", "don't ", "do not "))
                    if neg != neg2:
                        score = float(dom_sim)
                        contradictions.append((a.get("aku_id"), b.get("aku_id"), score))
        except Exception:
            pass
        return contradictions

    contradictions = _detect_contradictions([e for _, e in selected])
    if contradictions:
        knowledge_debug["contradictions_detected"] = contradictions

    # Compute simple quality metrics over the selected candidates
    selected_scores = [float(s) for s, _ in selected] if selected else []
    if selected_scores:
        avg_kis = sum(selected_scores) / max(1, len(selected_scores))
    else:
        avg_kis = 0.0

    # Map avg_kis to a 0-1 heuristic quality using a simple saturating transform
    candidate_quality = float(avg_kis / (1.0 + abs(avg_kis))) if avg_kis is not None else 0.0

    knowledge_quality = {
        "avg_kis": round(float(avg_kis), 4),
        "candidate_quality": round(max(0.0, min(1.0, candidate_quality)), 4),
        "top_kis": top_kis,
        "num_candidates": len(selected_scores),
    }
    
    # Detect domains with sparse knowledge coverage
    MIN_DOMAIN_ENTRIES = 5
    knowledge_gaps: List[str] = []
    for domain in active_domains:
        domain_path = os.path.join(BASE_PATH, domain)
        if not os.path.isdir(domain_path):
            if domain not in knowledge_gaps:
                knowledge_gaps.append(domain)
            continue
        total_in_domain = 0
        for ktype in KNOWLEDGE_TYPES:
            fp = os.path.join(domain_path, f"{ktype}s.json")
            raw = load_json_safe(fp)
            entries = raw.get("entries", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            total_in_domain += len(entries)
        if total_in_domain < MIN_DOMAIN_ENTRIES and domain not in knowledge_gaps:
            knowledge_gaps.append(domain)

    return {
        "synthesized_knowledge": synthesized,
        "knowledge_trace": backtrace,
        "knowledge_debug": knowledge_debug,
        "knowledge_quality": knowledge_quality,
        "knowledge_gaps": knowledge_gaps,
    }


def generate_diagnosis_counterfactual_synthesis(llm: Any, situation: Dict[str, Any], retrieved_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Optional LLM-driven layer: produce diagnosis, counterfactuals, and synthesis.
    If `llm` is not provided or does not implement a text call, returns empty placeholders.
    """
    out = {"diagnosis_text": "", "counterfactual_risks": [], "synthesis_text": ""}
    try:
        caller = getattr(llm, "analyze", None) or getattr(llm, "speak", None) or getattr(llm, "generate", None)
        if not caller:
            return out
        # Build a compact prompt (kept short here; callers can craft richer prompts)
        ctx = "\n\n".join([e.get("content", "") for e in (retrieved_entries or [])[:5]])
        prompt = f"Situation:\n{situation}\n\nKnowledge:\n{ctx}\n\nProduce diagnosis, list of counterfactual risks, and a concise synthesis. Return JSON."
        raw = caller(system_prompt="Diagnosis/Counterfactual/Synthesis", user_prompt=prompt)
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else None
            if isinstance(parsed, dict):
                out["diagnosis_text"] = parsed.get("diagnosis_text", "")
                out["counterfactual_risks"] = parsed.get("counterfactual_risks", [])
                out["synthesis_text"] = parsed.get("synthesis_text", "")
        except Exception:
            # parsing failed — return empty placeholders
            return out
    except Exception:
        return out
    return out


def apply_ml_judgment_prior(features: Dict[str, Any], model: Any = None) -> float:
    """
    Placeholder for ML judgment prior: given feature vector and optional model,
    return a multiplier to adjust scores. Default is 1.0 (no change).
    """
    try:
        if model is None:
            return 1.0
        # model.predict_proba could be used; keep as a safe stub
        if hasattr(model, "predict"):
            p = model.predict([features])
            return float(p[0]) if p else 1.0
    except Exception:
        pass
    return 1.0
