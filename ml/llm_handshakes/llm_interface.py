"""
LLM Handshakes - Structured Calls with Bounded Authority

The LLM is a sensor only, not a decision-maker.

It provides:
1. Situation classification (hard)
2. Constraint extraction (critical)
3. Counterfactual sketching (bounded)
4. Intent & bias detection (optional)

All outputs are structured, bounded, auditable, and overridable.
"""

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# Try to import Ollama client, fallback to None for mocking
try:
    # If this is running in ML context without ingestion module
    import sys
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    
    from ingestion.v2.src.ollama_client import OllamaClient
    from ingestion.v2.src.config import DEFAULT_DEEPSEEK_MODEL
    OLLAMA_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    OllamaClient = None
    DEFAULT_DEEPSEEK_MODEL = "huihui_ai/deepseek-r1-abliterated:8b"
    OLLAMA_AVAILABLE = False


@dataclass
class SituationFrameOutput:
    """Output from CALL 1: Situation Framing."""
    decision_type: str  # "irreversible" | "reversible" | "exploratory"
    risk_level: str  # "low" | "medium" | "high"
    time_horizon: str  # "short" | "medium" | "long"
    time_pressure: float  # 0.0–1.0
    information_completeness: float  # 0.0–1.0
    agency: str  # "individual" | "org"
    confidence: float  # 0.0–1.0


@dataclass
class ConstraintExtractionOutput:
    """Output from CALL 2: Constraint Extraction."""
    irreversibility_score: float  # 0.0–1.0
    fragility_score: float  # 0.0–1.0
    optionality_loss_score: float  # 0.0–1.0
    downside_asymmetry: float  # 0.0–1.0
    upside_asymmetry: float  # 0.0–1.0
    likely_regret_if_wrong: float  # 0.0–1.0
    confidence: float  # 0.0–1.0


@dataclass
class CounterfactualOption:
    """Single option in counterfactual sketch."""
    action: str  # "commit" | "delay" | "explore"
    primary_downside: str
    primary_upside: str
    reversibility: str  # "low" | "medium" | "high"
    recovery_time_days: int


@dataclass
class CounterfactualSketchOutput:
    """Output from CALL 3: Counterfactual Sketch."""
    options: List[CounterfactualOption]
    confidence: float  # 0.0–1.0


@dataclass
class IntentDetectionOutput:
    """Output from CALL 4: Intent & Bias Detection."""
    goal_orientation: str  # "operational" | "tactical" | "strategic"
    emotional_pressure: float  # 0.0–1.0
    urgency_bias_detected: bool
    confidence: float  # 0.0–1.0


# ============================================================================
# GLOBAL SYSTEM PROMPT
# ============================================================================

GLOBAL_SYSTEM_PROMPT = """
You are an expert human decision analyst.

You must reason holistically, not by keywords.
Do not quote the user.
Do not explain your reasoning.
Do not provide advice.

Your task is to silently analyze the situation as a wise human would
and return ONLY the requested structured fields.

All numeric values must be grounded in judgment, not text frequency.
If uncertain, lower confidence.

This forces latent reasoning, not pattern matching.
"""


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

CALL_1_PROMPT = """
Analyze the following situation as a human decision analyst.

Classify the nature of the decision based on:
- reversibility: Can this be undone if it goes wrong?
- stakes: What is at risk if wrong?
- uncertainty: How much is unknown?
- time pressure: How urgent is this?
- agency: Is this individual or organizational?

Do NOT look for keywords.
Use holistic judgment.

Return ONLY valid JSON matching this schema (use double quotes):
{{
  "decision_type": "irreversible | reversible | exploratory",
  "risk_level": "low | medium | high",
  "time_horizon": "short | medium | long",
  "time_pressure": 0.0,
  "information_completeness": 0.0,
  "agency": "individual | org",
  "confidence": 0.0
}}

User situation:
{user_input}
"""


CALL_2_PROMPT = """
Analyze the situation from a failure-first perspective.

Assume the decision goes wrong.
Estimate what would be hard or impossible to recover.

Do NOT rely on keywords.
Use human intuition about risk, loss, and fragility.

Return ONLY valid JSON matching this schema:
{{
  "irreversibility_score": 0.0,
  "fragility_score": 0.0,
  "optionality_loss_score": 0.0,
  "downside_asymmetry": 0.0,
  "upside_asymmetry": 0.0,
  "likely_regret_if_wrong": 0.0,
  "confidence": 0.0
}}

Where:
- irreversibility_score: How hard to undo if wrong?
- fragility_score: How fragile is the situation?
- optionality_loss_score: How much future choice would be lost?
- downside_asymmetry: Are losses worse than potential gains?
- upside_asymmetry: Are potential gains good but limited?
- likely_regret_if_wrong: How much regret if this fails?

User situation:
{user_input}

Situation context:
{situation_context}
"""


CALL_3_PROMPT = """
Enumerate plausible future outcomes for different broad actions.

You must NOT recommend anything.
You must NOT judge what is best.
You must NOT give advice.

Only describe consequences a human would anticipate.

Maximum 3 actions.
Return ONLY JSON matching this schema:
{{
  "options": [
    {{
      "action": "commit | delay | explore",
      "primary_downside": "string",
      "primary_upside": "string",
      "reversibility": "low | medium | high",
      "recovery_time_days": 0
    }}
  ],
  "confidence": 0.0
}}

User situation:
{user_input}

Constraints:
{constraints_context}
"""


CALL_4_PROMPT = """
Assess the user's intent and emotional posture.

Infer:
- motivation (operational fix | tactical improvement | strategic vision)
- emotional pressure (escalation, fear, urgency claimed as genuine?)
- whether emotions are distorting judgment

Do NOT quote or analyze specific words.
Use human intuition.

Return ONLY JSON:
{{
  "goal_orientation": "operational | tactical | strategic",
  "emotional_pressure": 0.0,
  "urgency_bias_detected": true | false,
  "confidence": 0.0
}

User input:
{user_input}
"""


# ============================================================================
# LLM CALL WRAPPERS - Ollama Integration
# ============================================================================

class LLMInterface:
    """
    Interface for LLM calls via Ollama.
    
    Uses ollama_client to make structured calls to deepseek-r1-abliterated:8b
    with retry logic and fallback mechanisms.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: str = "http://localhost:11434",
        max_retries: int = 2,
        timeout: int = 90
    ):
        """
        Initialize LLM interface.
        
        Args:
            model: Model name (defaults to deepseek-r1-abliterated:8b)
            base_url: Ollama base URL
            max_retries: Number of retries on failure
            timeout: Request timeout in seconds
        """
        self.model = model or DEFAULT_DEEPSEEK_MODEL
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout = timeout
        self.call_count = 0
        
        # Initialize Ollama client if available
        if OLLAMA_AVAILABLE and OllamaClient:
            try:
                self.client = OllamaClient(model=self.model, base_url=self.base_url)
            except Exception as e:
                print(f"[WARN] Failed to initialize OllamaClient: {e}")
                self.client = None
        else:
            self.client = None
    
    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make a structured LLM call via Ollama with retry logic.
        
        Args:
            system_prompt: System/instruction prompt
            user_prompt: User query/situation
            
        Returns:
            LLM response text (must be valid JSON for structured calls)
        """
        if not self.client:
            print(f"[WARN] OllamaClient not available, returning empty response")
            return "{}"
        
        self.call_count += 1
        
        # Combine prompts for the API
        full_prompt = user_prompt
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.generate(
                    prompt=full_prompt,
                    model=self.model,
                    timeout=self.timeout,
                    system=system_prompt
                )
                
                if response:
                    # Validate it's valid JSON-like
                    if "{" in response and "}" in response:
                        return response
                    # If not JSON, warn and return empty object
                    print(f"[WARN] LLM response not JSON-like: {response[:100]}")
                    return "{}"
                    
            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"[WARN] LLM call attempt {attempt + 1} failed: {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    print(f"[ERROR] LLM call failed after {self.max_retries + 1} attempts: {e}")
                    return "{}"
        
        return "{}"
    
    def call_1_situation_framing(self, user_input: str) -> SituationFrameOutput:
        """CALL 1: Situation Framing (hardest)."""
        prompt = CALL_1_PROMPT.format(user_input=user_input)
        
        response_text = self.call_llm(GLOBAL_SYSTEM_PROMPT, prompt)
        
        # Parse JSON response
        try:
            data = json.loads(response_text)
            return SituationFrameOutput(**data)
        except (json.JSONDecodeError, TypeError):
            # Fallback: return neutral/uncertain
            return SituationFrameOutput(
                decision_type="exploratory",
                risk_level="medium",
                time_horizon="medium",
                time_pressure=0.5,
                information_completeness=0.5,
                agency="individual",
                confidence=0.3
            )
    
    def call_2_constraint_extraction(
        self,
        user_input: str,
        situation: SituationFrameOutput
    ) -> ConstraintExtractionOutput:
        """CALL 2: Constraint Extraction (critical)."""
        
        context = f"""
Decision type: {situation.decision_type}
Risk level: {situation.risk_level}
Time horizon: {situation.time_horizon}
Information completeness: {situation.information_completeness}
"""
        
        prompt = CALL_2_PROMPT.format(
            user_input=user_input,
            situation_context=context
        )
        
        response_text = self.call_llm(GLOBAL_SYSTEM_PROMPT, prompt)
        
        try:
            data = json.loads(response_text)
            return ConstraintExtractionOutput(**data)
        except (json.JSONDecodeError, TypeError):
            return ConstraintExtractionOutput(
                irreversibility_score=0.5,
                fragility_score=0.5,
                optionality_loss_score=0.5,
                downside_asymmetry=0.5,
                upside_asymmetry=0.5,
                likely_regret_if_wrong=0.5,
                confidence=0.3
            )
    
    def call_3_counterfactual_sketch(
        self,
        user_input: str,
        constraints: ConstraintExtractionOutput
    ) -> CounterfactualSketchOutput:
        """CALL 3: Counterfactual Sketch (bounded)."""
        
        context = f"""
Irreversibility: {constraints.irreversibility_score}
Fragility: {constraints.fragility_score}
Downside asymmetry: {constraints.downside_asymmetry}
"""
        
        prompt = CALL_3_PROMPT.format(
            user_input=user_input,
            constraints_context=context
        )
        
        response_text = self.call_llm(GLOBAL_SYSTEM_PROMPT, prompt)
        
        try:
            data = json.loads(response_text)
            options = [CounterfactualOption(**opt) for opt in data.get("options", [])]
            
            # Limit to 3 options
            options = options[:3]
            
            return CounterfactualSketchOutput(
                options=options,
                confidence=data.get("confidence", 0.5)
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return CounterfactualSketchOutput(options=[], confidence=0.3)
    
    def call_4_intent_detection(self, user_input: str) -> IntentDetectionOutput:
        """CALL 4: Intent & Bias Detection (optional)."""
        
        prompt = CALL_4_PROMPT.format(user_input=user_input)
        
        response_text = self.call_llm(GLOBAL_SYSTEM_PROMPT, prompt)
        
        try:
            data = json.loads(response_text)
            return IntentDetectionOutput(**data)
        except (json.JSONDecodeError, TypeError):
            return IntentDetectionOutput(
                goal_orientation="tactical",
                emotional_pressure=0.5,
                urgency_bias_detected=False,
                confidence=0.3
            )
    
    def run_handshake_sequence(self, user_input: str) -> Dict[str, Any]:
        """
        Run full 4-call handshake sequence.
        
        Returns complete situation assessment.
        """
        
        # CALL 1: Situation framing
        situation = self.call_1_situation_framing(user_input)
        
        # CALL 2: Constraint extraction
        constraints = self.call_2_constraint_extraction(user_input, situation)
        
        # CALL 3: Counterfactual sketch
        counterfactuals = self.call_3_counterfactual_sketch(user_input, constraints)
        
        # CALL 4: Intent detection
        intent = self.call_4_intent_detection(user_input)
        
        return {
            "situation": {
                "decision_type": situation.decision_type,
                "risk_level": situation.risk_level,
                "time_horizon": situation.time_horizon,
                "time_pressure": situation.time_pressure,
                "information_completeness": situation.information_completeness,
                "agency": situation.agency,
                "confidence": situation.confidence,
            },
            "constraints": {
                "irreversibility_score": constraints.irreversibility_score,
                "fragility_score": constraints.fragility_score,
                "optionality_loss_score": constraints.optionality_loss_score,
                "downside_asymmetry": constraints.downside_asymmetry,
                "upside_asymmetry": constraints.upside_asymmetry,
                "confidence": constraints.confidence,
            },
            "counterfactuals": {
                "options": [
                    {
                        "action": opt.action,
                        "primary_downside": opt.primary_downside,
                        "primary_upside": opt.primary_upside,
                        "reversibility": opt.reversibility,
                        "recovery_time_days": opt.recovery_time_days,
                    }
                    for opt in counterfactuals.options
                ],
                "confidence": counterfactuals.confidence,
            },
            "intent": {
                "goal_orientation": intent.goal_orientation,
                "emotional_pressure": intent.emotional_pressure,
                "urgency_bias_detected": intent.urgency_bias_detected,
                "confidence": intent.confidence,
            },
        }
