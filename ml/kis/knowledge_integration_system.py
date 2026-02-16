"""
Knowledge Integration System (KIS) - Core Engine

Multi-factor scoring algorithm that synthesizes domain-relevant knowledge
from a distributed knowledge base. Ranks knowledge items using 5 independent
weight factors.

Location: c:\era\ml\kis\knowledge_integration_system.py
"""

import math
import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import os


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class KnowledgeType(Enum):
    PRINCIPLE = "principle"
    RULE = "rule"
    WARNING = "warning"
    CLAIM = "claim"
    ADVICE = "advice"


# Inherent type weights (baseline)
TYPE_WEIGHTS = {
    "principle": 1.0,   # foundational
    "rule": 1.1,        # actionable (highest)
    "warning": 1.05,    # cautionary
    "claim": 0.95,      # factual
    "advice": 0.9,      # suggestions (lowest)
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class KnowledgeEntry:
    """Single knowledge unit in the system."""
    aku_id: str
    content: str
    type: str  # principle, rule, warning, claim, advice
    domain: str
    source: Dict[str, Any]
    memory: Dict[str, Any] = field(default_factory=dict)
    
    # Computed during scoring
    kis_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "aku_id": self.aku_id,
            "content": self.content,
            "type": self.type,
            "domain": self.domain,
            "source": self.source,
            "memory": self.memory,
            "kis": self.kis_score,
        }


@dataclass
class KISRequest:
    """Request for knowledge synthesis."""
    user_input: str
    active_domains: List[str]
    domain_confidence: Dict[str, float]
    max_items: int = 5


@dataclass
class KISResult:
    """Result of knowledge synthesis."""
    synthesized_knowledge: List[str]
    knowledge_trace: List[Dict[str, Any]]
    knowledge_debug: Dict[str, Any]
    knowledge_quality: Dict[str, Any]


# ============================================================================
# WEIGHT FACTOR FUNCTIONS (5 Dimensions)
# ============================================================================

def compute_domain_weight(
    domain: str,
    active_domains: List[str],
    domain_confidence: Dict[str, float]
) -> float:
    """
    Weight 1: Domain Relevance
    
    Range: 0.25 to 1.4
    
    - If domain in active_domains: max(confidence[domain], 0.5)
    - If domain NOT in active_domains: 0.25 (penalty)
    """
    if domain in active_domains:
        confidence = domain_confidence.get(domain, 0.5)
        return max(confidence, 0.5)
    else:
        return 0.25  # off-domain penalty


def compute_type_weight(knowledge_type: str) -> float:
    """
    Weight 2: Knowledge Type Authority
    
    Range: 0.9 to 1.1
    
    Principle:  1.0  (neutral, foundational)
    Rule:       1.1  (highest weight, actionable)
    Warning:    1.05 (cautionary)
    Claim:      0.95 (factual)
    Advice:     0.9  (suggestions, lowest)
    """
    return TYPE_WEIGHTS.get(knowledge_type, 1.0)


def compute_memory_weight(reinforcement_count: int, penalty_count: int = 0) -> float:
    """
    Weight 3: Memory & Reinforcement
    
    Formula: (1 + ln(1 + reinforcement_count)) × exp(-0.3 × penalty_count)
    
    Range: ~0.3 to ~8.0
    
    Examples:
    - rc=0:    mw = 1.0
    - rc=1:    mw ≈ 1.693
    - rc=10:   mw ≈ 3.398
    - rc=100:  mw ≈ 5.605
    - rc=1000: mw ≈ 7.908
    
    Penalties decay dominance: repeated failures hurt.
    """
    base = 1.0 + math.log(1.0 + reinforcement_count)
    
    # Penalties apply multiplicative decay
    penalty_multiplier = math.exp(-0.3 * penalty_count)
    
    return base * penalty_multiplier


def compute_context_weight(
    content: str,
    user_input: str,
    keywords: Optional[List[str]] = None
) -> float:
    """
    Weight 4: Context Relevance (Keyword/Semantic Matching)
    
    Range: 0.85 to 1.4
    
    - 2+ keyword matches:  1.4  (highly relevant)
    - 1 keyword match:     1.2  (moderately relevant)
    - 0 keyword matches:   0.85 (generic)
    """
    if keywords is None:
        keywords = extract_keywords(content)
    
    # Check how many keywords from content appear in user_input
    user_input_lower = user_input.lower()
    matches = sum(1 for kw in keywords if kw.lower() in user_input_lower)
    
    if matches >= 2:
        return 1.4
    elif matches == 1:
        return 1.2
    else:
        return 0.85


def compute_goal_weight(content: str) -> float:
    """
    Weight 5: Goal Alignment (Time Horizon)
    
    Range: 0.7 to 1.2
    
    Language parsing for decision intent:
    - Strategic (forever, legacy, impact, vision):     1.2
    - Tactical (quarter, project, timeline):           1.0
    - Operational (today, immediate, urgent):          0.7
    """
    content_lower = content.lower()
    
    strategic_terms = ["forever", "legacy", "impact", "vision", "long-term", "permanently"]
    tactical_terms = ["quarter", "project", "timeline", "month", "year"]
    operational_terms = ["today", "immediate", "urgent", "now", "immediately"]
    
    if any(term in content_lower for term in strategic_terms):
        return 1.2
    elif any(term in content_lower for term in tactical_terms):
        return 1.0
    elif any(term in content_lower for term in operational_terms):
        return 0.7
    else:
        return 1.0  # neutral default


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    Extract domain-relevant keywords from text.
    
    Simple approach: noun-heavy tokens, length > 4 chars.
    """
    import re
    
    # Remove punctuation, split
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Filter: > 4 chars, not common words
    stopwords = {"the", "and", "that", "this", "with", "from", "have", "your", "been"}
    candidates = [w for w in words if len(w) > 4 and w not in stopwords]
    
    # Return unique, top N
    return list(set(candidates))[:max_keywords]


def load_builtin_entries() -> List[KnowledgeEntry]:
    """
    Fallback hardcoded entries if on-disk JSON unavailable.
    
    7 domain-spanning entries ensuring non-empty returns.
    """
    return [
        KnowledgeEntry(
            aku_id="builtin-1",
            content="Quitting without financial buffer leaves you vulnerable. Ensure 6-12 months expenses saved before major career transitions.",
            type="warning",
            domain="career_risk",
            source={"book": "builtin:risk_guide"},
            memory={"reinforcement_count": 2, "penalty_count": 0}
        ),
        KnowledgeEntry(
            aku_id="builtin-2",
            content="Plan alternatives before committing. Keep multiple paths open to maintain negotiating power.",
            type="advice",
            domain="optionality_guide",
            source={"book": "builtin:optionality_guide"},
            memory={"reinforcement_count": 5, "penalty_count": 0}
        ),
        KnowledgeEntry(
            aku_id="builtin-3",
            content="Stress and burnout reduce decision quality. Prioritize recovery and mental health during high-stakes periods.",
            type="principle",
            domain="psychology_of_work",
            source={"book": "builtin:psychology_guide"},
            memory={"reinforcement_count": 1, "penalty_count": 0}
        ),
        KnowledgeEntry(
            aku_id="builtin-4",
            content="Prioritize emergency savings. Build 3-month liquid reserves before investing in growth opportunities.",
            type="rule",
            domain="personal_finance",
            source={"book": "builtin:finance_guide"},
            memory={"reinforcement_count": 3, "penalty_count": 0}
        ),
        KnowledgeEntry(
            aku_id="builtin-5",
            content="Irreversible decisions warrant extra scrutiny. Reversible decisions can be optimized through iteration.",
            type="principle",
            domain="decision_theory",
            source={"book": "builtin:decision_theory"},
            memory={"reinforcement_count": 4, "penalty_count": 0}
        ),
        KnowledgeEntry(
            aku_id="builtin-6",
            content="Technological adoption curves follow S-patterns. Early adoption provides advantage; late adoption faces diminishing returns.",
            type="rule",
            domain="power_technology",
            source={"book": "builtin:tech_guide"},
            memory={"reinforcement_count": 2, "penalty_count": 0}
        ),
        KnowledgeEntry(
            aku_id="builtin-7",
            content="Resilient communications maintain clarity under pressure. Practice key messages before high-stakes conversations.",
            type="advice",
            domain="intel_and_comm",
            source={"book": "builtin:communication_guide"},
            memory={"reinforcement_count": 1, "penalty_count": 0}
        ),
    ]


def load_knowledge_entries(domains: List[str], base_path: str = "data/ministers") -> List[KnowledgeEntry]:
    """
    Load knowledge entries from on-disk JSON files.
    
    Path structure: base_path/[domain]/[type].json
    
    Falls back to builtin entries if files unavailable.
    """
    entries = []
    
    for domain in domains:
        domain_path = os.path.join(base_path, domain)
        
        if not os.path.exists(domain_path):
            continue
        
        # Try to load each type file
        for ktype in ["principle", "rule", "warning", "claim", "advice"]:
            type_file = os.path.join(domain_path, f"{ktype}s.json")
            
            if os.path.exists(type_file):
                try:
                    with open(type_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                entries.append(KnowledgeEntry(
                                    aku_id=item.get("aku_id", ""),
                                    content=item.get("content", ""),
                                    type=ktype.rstrip('s'),  # Remove plural
                                    domain=domain,
                                    source=item.get("source", {}),
                                    memory=item.get("memory", {})
                                ))
                except (json.JSONDecodeError, IOError):
                    pass
    
    # Fallback to builtin
    if not entries:
        entries = load_builtin_entries()
    
    return entries


# ============================================================================
# CORE KIS ENGINE
# ============================================================================

class KnowledgeIntegrationSystem:
    """
    Multi-factor knowledge scoring engine.
    
    Synthesizes domain-relevant knowledge via 5 independent weight factors:
    1. Domain relevance
    2. Knowledge type authority
    3. Memory reinforcement
    4. Context matching
    5. Goal alignment
    """
    
    def __init__(self, base_path: str = "data/ministers"):
        self.base_path = base_path
    
    def synthesize_knowledge(self, request: KISRequest) -> KISResult:
        """
        Main KIS pipeline (9 stages).
        
        Stages:
        1. Input validation
        2. Knowledge loading
        3. Entry enumeration
        4. KIS scoring
        5. Sorting & selection
        6. Backtrace generation
        7. Quality metrics
        8. Debug information
        9. Result assembly
        """
        
        # Stage 1: Validation
        if not request.user_input or not request.active_domains:
            return self._empty_result()
        
        # Stage 2: Load entries
        entries = load_knowledge_entries(request.active_domains, self.base_path)
        if not entries:
            entries = load_builtin_entries()
        
        # Stage 3–4: Enumerate and score
        scored_entries = []
        for entry in entries:
            dw = compute_domain_weight(entry.domain, request.active_domains, request.domain_confidence)
            tw = compute_type_weight(entry.type)
            mw = compute_memory_weight(
                entry.memory.get("reinforcement_count", 0),
                entry.memory.get("penalty_count", 0)
            )
            cw = compute_context_weight(entry.content, request.user_input)
            gw = compute_goal_weight(entry.content)
            
            # Composite KIS score
            entry.kis_score = dw * tw * mw * cw * gw
            scored_entries.append(entry)
        
        # Stage 5: Sort and select top N
        scored_entries.sort(key=lambda e: e.kis_score, reverse=True)
        selected = scored_entries[:request.max_items]
        
        # Stage 6: Knowledge trace
        knowledge_trace = [
            {
                "aku_id": e.aku_id,
                "domain": e.domain,
                "type": e.type,
                "source": e.source,
                "kis": round(e.kis_score, 3),
                "book": e.source.get("book", "unknown"),
            }
            for e in selected
        ]
        
        # Stage 7: Quality metrics
        kis_scores = [e.kis_score for e in selected]
        knowledge_quality = {
            "num_selected": len(selected),
            "top_kis_scores": [round(s, 3) for s in kis_scores],
            "avg_kis": round(sum(kis_scores) / len(kis_scores), 3) if kis_scores else 0.0,
        }
        
        # Stage 8: Debug info
        books_scanned = set(e.domain for e in entries)
        selected_books = set(e.domain for e in selected)
        
        knowledge_debug = {
            "total_entries_scanned": len(entries),
            "num_books_scanned": len(books_scanned),
            "books_scanned": sorted(books_scanned),
            "selected_books": sorted(selected_books),
        }
        
        # Stage 9: Assemble result
        synthesized_knowledge = [e.content for e in selected]
        
        return KISResult(
            synthesized_knowledge=synthesized_knowledge,
            knowledge_trace=knowledge_trace,
            knowledge_debug=knowledge_debug,
            knowledge_quality=knowledge_quality,
        )
    
    def _empty_result(self) -> KISResult:
        """Return empty but valid result."""
        return KISResult(
            synthesized_knowledge=[],
            knowledge_trace=[],
            knowledge_debug={"total_entries_scanned": 0, "books_scanned": []},
            knowledge_quality={"num_selected": 0, "top_kis_scores": [], "avg_kis": 0.0},
        )
