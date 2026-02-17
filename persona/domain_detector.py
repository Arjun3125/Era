"""
Domain Detection System

Parses problem statements to extract active domains using:
- Keyword matching against domain dictionaries
- LLM-based situation analysis (via OllamaRuntime)
- Context inference from previous sessions
"""
import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path


# Domain keyword mappings
DOMAIN_KEYWORDS = {
    "career": [
        "job", "career", "work", "employment", "promotion", "quit", "quit",
        "resign", "hiring", "interview", "boss", "manager", "colleague",
        "team", "project", "salary", "compensation", "raise", "workplace",
        "professional", "skill", "competence", "expertise"
    ],
    "psychology": [
        "stress", "anxiety", "depression", "mental", "emotional", "feel",
        "overwhelm", "burnout", "confidence", "self-esteem", "identity",
        "relationship", "family", "trauma", "healing", "therapy", "mindset"
    ],
    "risk": [
        "risk", "danger", "safe", "security", "loss", "fail", "failure",
        "uncertain", "financial", "income", "savings", "debt", "credit",
        "investment", "money", "budget", "afford", "expensive"
    ],
    "strategy": [
        "plan", "strategy", "goal", "objective", "approach", "method",
        "decision", "choose", "option", "alternative", "path", "direction",
        "long-term", "short-term", "timeline", "priority", "focus"
    ],
    "power": [
        "control", "influence", "authority", "power", "dominance", "subordinate",
        "negotiate", "bargain", "deal", "leverage", "advantage", "position",
        "conflict", "competition", "win", "lose", "strength", "weakness"
    ],
    "optionality": [
        "flexible", "option", "optionality", "choice", "freedom", "alternative",
        "backup", "contingency", "plan b", "escape", "pivot", "switch",
        "adapt", "change", "transition", "mobility"
    ],
    "timing": [
        "now", "when", "urgent", "deadline", "time", "season", "moment",
        "ready", "wait", "delay", "rush", "soon", "later", "patience"
    ],
    "technology": [
        "tech", "technology", "digital", "online", "software", "automation",
        "ai", "data", "platform", "system", "tool", "upgrade", "learning",
        "skill", "competence"
    ]
}

# Reverse mapping: domain -> keywords
REVERSE_DOMAIN_KEYWORDS = {
    domain: set(keywords) for domain, keywords in DOMAIN_KEYWORDS.items()
}


def extract_keywords_from_text(text: str) -> List[str]:
    """Extract lowercase words from text for keyword matching."""
    words = re.findall(r"\b[\w']{3,}\b", text.lower())
    return words


def detect_domains_by_keywords(problem_statement: str, threshold: int = 1) -> Dict[str, float]:
    """
    Detect domains by keyword matching.
    
    Args:
        problem_statement: User's problem description
        threshold: Minimum keyword matches to activate a domain
    
    Returns:
        Dict mapping domain -> confidence (0.0-1.0)
    """
    text_words = set(extract_keywords_from_text(problem_statement))
    domain_scores = {}
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        keyword_set = set(keywords)
        matches = len(text_words & keyword_set)
        
        if matches >= threshold:
            # Confidence based on match ratio
            confidence = min(1.0, matches / max(len(keyword_set), 5))
            domain_scores[domain] = confidence
    
    return domain_scores


def detect_stakes(problem_statement: str) -> str:
    """
    Detect urgency/stakes level from problem statement.
    
    Returns: "low", "medium", or "high"
    """
    text_lower = problem_statement.lower()
    
    high_stakes_keywords = [
        "urgent", "emergency", "critical", "crisis", "dangerous", "risk",
        "life", "death", "health", "quit", "resign", "bankruptcy", "disaster"
    ]
    
    medium_stakes_keywords = [
        "soon", "important", "concern", "worried", "conflict", "trouble",
        "problem", "issue", "struggling", "difficulty"
    ]
    
    high_count = sum(1 for kw in high_stakes_keywords if kw in text_lower)
    medium_count = sum(1 for kw in medium_stakes_keywords if kw in text_lower)
    
    if high_count >= 1:
        return "high"
    elif medium_count >= 2:
        return "medium"
    else:
        return "low"


def detect_reversibility(problem_statement: str) -> str:
    """
    Estimate if decision is reversible or not.
    
    Returns: "fully_reversible", "partially_reversible", or "irreversible"
    """
    text_lower = problem_statement.lower()
    
    irreversible_keywords = [
        "quit", "resign", "divorce", "break up", "end relationship", "burn bridges",
        "move", "relocate", "surgery", "major surgery"
    ]
    
    reversible_keywords = [
        "try", "experiment", "test", "apply", "propose", "request", "negotiate",
        "consider", "explore", "think about"
    ]
    
    irreversible_count = sum(1 for kw in irreversible_keywords if kw in text_lower)
    reversible_count = sum(1 for kw in reversible_keywords if kw in text_lower)
    
    if irreversible_count >= 1:
        return "irreversible"
    elif reversible_count >= 2:
        return "fully_reversible"
    else:
        return "partially_reversible"


def analyze_situation(problem_statement: str, llm_adapter: Optional[object] = None) -> Dict:
    """
    Comprehensive situation analysis combining keyword matching and optional LLM analysis.
    
    Returns:
        {
            "problem": str,
            "domains": List[str],
            "domain_confidence": float,
            "stakes": str,
            "reversibility": str,
            "key_entities": List[str],
            "llm_analysis": Optional[Dict]
        }
    """
    # Keyword-based detection
    domain_scores = detect_domains_by_keywords(problem_statement)
    
    # Sort by confidence
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    active_domains = [d for d, score in sorted_domains if score >= 0.1]  # Lower threshold
    
    # Use top domain's confidence as overall confidence, or default
    domain_confidence = sorted_domains[0][1] if sorted_domains else 0.6
    
    stakes = detect_stakes(problem_statement)
    reversibility = detect_reversibility(problem_statement)
    
    # Extract key entities (potential mentions of people, places, things)
    key_entities = extract_key_entities(problem_statement)
    
    analysis = {
        "problem": problem_statement,
        "domains": active_domains if active_domains else ["strategy"],  # Fallback to strategy
        "domain_confidence": domain_confidence,
        "stakes": stakes,
        "reversibility": reversibility,
        "key_entities": key_entities,
        "domain_scores": dict(sorted_domains)
    }
    
    # Optional: Enhance with LLM if available
    if llm_adapter:
        try:
            llm_analysis = analyze_with_llm(problem_statement, llm_adapter)
            analysis["llm_analysis"] = llm_analysis
        except Exception as e:
            analysis["llm_error"] = str(e)
    
    return analysis


def extract_key_entities(text: str) -> List[str]:
    """
    Extract potential named entities/key concepts from problem statement.
    Simple heuristic: capitalized words, quoted phrases.
    """
    entities = []
    
    # Capitalized words (potential names/proper nouns)
    capitalized = re.findall(r"\b[A-Z][a-z]+\b", text)
    entities.extend(capitalized)
    
    # Quoted phrases
    quoted = re.findall(r"[\"']([^\"']+)[\"']", text)
    entities.extend(quoted)
    
    return list(set(entities))[:5]  # Return unique, max 5


def analyze_with_llm(problem_statement: str, llm_adapter) -> Dict:
    """
    Use LLM to enhance situation analysis.
    Identifies implicit domains, emotional tone, hidden constraints.
    """
    prompt = f"""Analyze this problem statement and provide structured insights:

Problem: {problem_statement}

Respond with:
1. Implicit domains (beyond obvious ones)
2. Emotional tone (e.g., "anxious", "determined", "resigned")
3. Hidden constraints or assumptions
4. Potential second-order consequences

Keep each point brief."""
    
    try:
        response = llm_adapter.analyze(problem_statement, system_prompt=prompt)
        return {
            "insights": response,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


def domain_similarity(domains1: List[str], domains2: List[str]) -> float:
    """
    Calculate similarity between two domain lists (for problem continuity).
    
    Returns: 0.0-1.0 similarity score
    """
    if not domains1 or not domains2:
        return 0.0
    
    set1 = set(domains1)
    set2 = set(domains2)
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0
