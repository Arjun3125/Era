"""
Post-Conversation ML Learning Processor

After each conversation ends, analyze what was learned and extract improvements
for future conversations. This closes the learning loop.

Flow:
1. Conversation completes and stores Episode + Metrics
2. ML Processor analyzes: What worked? What didn't?
3. Extract patterns: Domain effectiveness, question types, satisfaction drivers
4. Generate insights: Which domains need improvement? What questions work best?
5. Update decision preferences: Next session uses learned patterns
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict


class ConversationLearningProcessor:
    """
    Post-conversation ML analysis and pattern extraction.
    """
    
    def __init__(self, storage_dir: str = "data/learning_insights"):
        self.storage_dir = storage_dir
        Path(storage_dir).mkdir(parents=True, exist_ok=True)
        
        self.patterns_file = f"{storage_dir}/domain-patterns.jsonl"
        self.insights_file = f"{storage_dir}/learning-insights.jsonl"
        self.weak_domains_file = f"{storage_dir}/weak-domains.json"
        
    # =====================================================
    # MAIN LEARNING PIPELINE
    # =====================================================
    
    def process_conversation(
        self,
        conversation_result: Dict[str, Any],
        session_num: int
    ) -> Dict[str, Any]:
        """
        Main entry point: Analyze conversation and extract learning.
        
        Args:
            conversation_result: From conduct_dialogue(), contains:
                - problem_statement
                - domains
                - stakes
                - turns
                - user_satisfied
                - final_recommendation
                - final_confidence
                - conversation_history
            session_num: Session number
        
        Returns:
            Learning insights including:
            - domain_performance
            - question_effectiveness
            - pattern_summary
            - recommendations_for_next_session
        """
        
        learning_record = {
            "timestamp": datetime.now().isoformat(),
            "session_number": session_num,
            "conversation_id": f"session_{session_num}",
        }
        
        # 1. Extract basic metrics
        metrics = self._extract_metrics(conversation_result)
        learning_record["metrics"] = metrics
        
        # 2. Analyze by domain effectiveness
        domain_analysis = self._analyze_domain_effectiveness(
            conversation_result["domains"],
            conversation_result["user_satisfied"],
            conversation_result["turns"],
            conversation_result["final_confidence"]
        )
        learning_record["domain_analysis"] = domain_analysis
        
        # 3. Analyze conversation quality
        quality_analysis = self._analyze_conversation_quality(conversation_result)
        learning_record["quality_analysis"] = quality_analysis
        
        # 4. Extract question patterns
        question_patterns = self._extract_question_patterns(conversation_result)
        learning_record["question_patterns"] = question_patterns
        
        # 5. Generate recommendations for next session
        recommendations = self._generate_next_session_recommendations(
            domain_analysis,
            quality_analysis,
            conversation_result
        )
        learning_record["recommendations"] = recommendations
        
        # 6. Identify weak domains across all sessions
        weak_domains = self._identify_weak_domains(session_num)
        learning_record["weak_domains"] = weak_domains
        
        # 7. Persist learning insights
        self._persist_learning(learning_record)
        
        # 8. Print summary
        self._print_learning_summary(learning_record)
        
        return learning_record
    
    # =====================================================
    # ANALYSIS METHODS
    # =====================================================
    
    def _extract_metrics(self, conversation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic conversation metrics."""
        return {
            "num_turns": conversation_result.get("turns", 0),
            "user_satisfied": conversation_result.get("user_satisfied", False),
            "final_confidence": conversation_result.get("final_confidence", 0.0),
            "domains": conversation_result.get("domains", []),
            "stakes": conversation_result.get("stakes", "medium"),
            "kis_items_available": len(conversation_result.get("kis_items", [])),
        }
    
    def _analyze_domain_effectiveness(
        self,
        domains: List[str],
        satisfied: bool,
        turns: int,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Analyze how well each domain was handled.
        
        Records:
        - Success rate per domain
        - Satisfaction drivers by domain
        - Confidence patterns
        """
        
        analysis = {
            "domains_engaged": domains,
            "primary_domain": domains[0] if domains else "unknown",
            "satisfaction_by_domain": {},
            "efficiency": {
                "turns_to_satisfaction": turns if satisfied else "unsatisfied",
                "confidence_achieved": confidence,
                "turns_per_domain": turns / len(domains) if domains else turns,
            }
        }
        
        # Record satisfaction outcome per domain
        for domain in domains:
            analysis["satisfaction_by_domain"][domain] = {
                "satisfied": satisfied,
                "turns": turns,
                "confidence": confidence,
            }
        
        return analysis
    
    def _analyze_conversation_quality(
        self,
        conversation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze quality indicators:
        - Did Persona Prime ask clarifying questions?
        - Was there back-and-forth clarity?
        - Did user express satisfaction?
        """
        
        history = conversation_result.get("conversation_history", [])
        
        analysis = {
            "total_exchanges": len(history),
            "persona_turns": len([h for h in history if h["speaker"] == "persona"]),
            "user_turns": len([h for h in history if h["speaker"] == "user"]),
            "conversation_depth": len(history) > 4,  # Boolean: multi-turn conversation
            "clarity_indicators": [],
        }
        
        # Look for clarity patterns
        for msg in history:
            text_lower = msg["text"].lower()
            if any(q in text_lower for q in ["clarify", "confirm", "understand", "specific about"]):
                analysis["clarity_indicators"].append("Clarifying question asked")
            if any(c in text_lower for c in ["satisfied", "helpful", "clear", "good advice"]):
                analysis["clarity_indicators"].append("Satisfaction signal detected")
        
        return analysis
    
    def _extract_question_patterns(
        self,
        conversation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract what types of questions worked well.
        
        Questions to ask:
        - Which clarifying question types got the best response?
        - Which domains benefit from more questions?
        - How many turns until user is satisfied?
        """
        
        history = conversation_result.get("conversation_history", [])
        questions_asked = []
        
        for msg in history:
            if msg["speaker"] == "persona" and "?" in msg["text"]:
                # Extract sentences with questions
                sentences = msg["text"].split(".")
                for sent in sentences:
                    if "?" in sent:
                        questions_asked.append(sent.strip()[:150])  # First 150 chars
        
        return {
            "total_questions": len(questions_asked),
            "question_examples": questions_asked[:3],  # Show first 3 questions
            "domains_requiring_questions": conversation_result.get("domains", []),
            "questions_before_satisfaction": len(questions_asked),
        }
    
    def _generate_next_session_recommendations(
        self,
        domain_analysis: Dict[str, Any],
        quality_analysis: Dict[str, Any],
        conversation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate specific recommendations for NEXT session.
        
        Based on what worked/didn't work,
        suggest improvements for similar future conversations.
        """
        
        recommendations = []
        
        # If satisfied quickly, what helped?
        if conversation_result.get("user_satisfied") and conversation_result.get("turns", 0) <= 3:
            recommendations.append({
                "type": "efficiency",
                "suggestion": "This domain achieved satisfaction efficiently. Replicate question pattern for similar problems.",
                "action": "Next similar problem: Start with same clarifying questions"
            })
        
        # If many turns needed, what was missing?
        if conversation_result.get("turns", 0) > 5:
            recommendations.append({
                "type": "clarification_depth",
                "suggestion": f"Took {conversation_result['turns']} turns to satisfy. May need deeper initial clarification.",
                "action": "Next conversation in these domains: Ask more specific follow-ups upfront"
            })
        
        # If not satisfied
        if not conversation_result.get("user_satisfied"):
            recommendations.append({
                "type": "coverage",
                "suggestion": "User remained unsatisfied. This domain may need different approach.",
                "action": "Next session with this domain: Consider involving more minister perspectives or different dialogue structure"
            })
        
        # Confidence feedback
        confidence = conversation_result.get("final_confidence", 0.0)
        if confidence < 0.6:
            recommendations.append({
                "type": "confidence",
                "suggestion": f"Low confidence ({confidence:.0%}) in recommendation. May indicate weak KIS coverage.",
                "action": "Next session: Pre-brief more minister perspectives before final recommendation"
            })
        
        # If high satisfaction + high confidence
        if conversation_result.get("user_satisfied") and confidence > 0.8:
            recommendations.append({
                "type": "best_practice",
                "suggestion": "Excellent outcome: satisfied user + confident recommendation.",
                "action": "Pattern this approach for future similar conversations"
            })
        
        return {
            "count": len(recommendations),
            "recommendations": recommendations,
            "domains_to_focus": conversation_result.get("domains", []),
        }
    
    def _identify_weak_domains(self, current_session: int) -> Dict[str, Any]:
        """
        Across all conversations, which domains underperform?
        
        Loads all past conversations and computes domain success rates.
        """
        
        domain_stats = defaultdict(lambda: {"satisfied": 0, "total": 0, "avg_turns": []})
        
        # Load all past conversation JSONs
        conv_dir = Path("data/conversations")
        if conv_dir.exists():
            for conv_file in conv_dir.glob("*.json"):
                try:
                    with open(conv_file, "r") as f:
                        data = json.load(f)
                        
                    domains = data.get("domains", [])
                    satisfied = data.get("user_satisfied", False)
                    turns = data.get("turns", 0)
                    
                    for domain in domains:
                        domain_stats[domain]["total"] += 1
                        if satisfied:
                            domain_stats[domain]["satisfied"] += 1
                        domain_stats[domain]["avg_turns"].append(turns)
                except:
                    pass
        
        # Compute success rates and identify weak ones
        weak_ones = []
        for domain, stats in domain_stats.items():
            if stats["total"] > 0:
                success_rate = stats["satisfied"] / stats["total"]
                avg_turns = sum(stats["avg_turns"]) / len(stats["avg_turns"])
                
                # Consider "weak" if <60% success or >4 avg turns
                if success_rate < 0.6 or avg_turns > 4:
                    weak_ones.append({
                        "domain": domain,
                        "success_rate": f"{success_rate:.0%}",
                        "conversations": stats["total"],
                        "avg_turns": f"{avg_turns:.1f}",
                    })
        
        return {
            "weak_domains": sorted(weak_ones, key=lambda x: float(x["success_rate"].rstrip("%")), reverse=True),
            "total_domains_tracked": len(domain_stats),
            "recommendation": "Focus next improvements on domains with <60% success rate"
        }
    
    # =====================================================
    # PERSISTENCE & REPORTING
    # =====================================================
    
    def _persist_learning(self, learning_record: Dict[str, Any]):
        """
        Save learning insights to disk for future reference.
        """
        try:
            # Append to learning insights file
            with open(self.insights_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(learning_record) + "\n")
            
            # Update weak domains summary
            weak_domains = learning_record.get("weak_domains", {})
            with open(self.weak_domains_file, "w", encoding="utf-8") as f:
                json.dump(weak_domains, f, indent=2)
                
        except Exception as e:
            print(f"[WARNING] Failed to persist learning: {e}")
    
    def _print_learning_summary(self, learning_record: Dict[str, Any]):
        """
        Print human-readable summary of what was learned.
        """
        print("\n" + "="*70)
        print("📚 ML LEARNING ANALYSIS (Post-Conversation)")
        print("="*70)
        
        metrics = learning_record.get("metrics", {})
        print(f"\n[Conversation Metrics]")
        print(f"  • Turns: {metrics.get('num_turns')}")
        print(f"  • User Satisfied: {'✅ YES' if metrics.get('user_satisfied') else '❌ NO'}")
        print(f"  • Confidence: {metrics.get('final_confidence'):.0%}")
        print(f"  • Domains: {', '.join(metrics.get('domains', []))}")
        
        quality = learning_record.get("quality_analysis", {})
        print(f"\n[Conversation Quality]")
        print(f"  • Total Exchanges: {quality.get('total_exchanges')}")
        print(f"  • Persona Questions: {quality.get('persona_turns')}")
        print(f"  • Depth Score: {'Deep multi-turn' if quality.get('conversation_depth') else 'Short conversation'}")
        
        recs = learning_record.get("recommendations", {})
        if recs.get("recommendations"):
            print(f"\n[📝 Recommendations for Next Session]")
            for i, rec in enumerate(recs["recommendations"], 1):
                print(f"  {i}. [{rec['type'].upper()}] {rec['suggestion']}")
                print(f"     → {rec['action']}")
        
        weak = learning_record.get("weak_domains", {})
        weak_list = weak.get("weak_domains", [])
        if weak_list:
            print(f"\n[⚠️  Weak Domains (system-wide)]")
            for domain_info in weak_list[:3]:  # Show top 3
                print(f"  • {domain_info['domain']}: {domain_info['success_rate']} success, " +
                      f"{domain_info['avg_turns']} avg turns")
        
        print("\n[💾 Learning Saved]")
        print(f"  → Insights appended to: {self.insights_file}")
        print(f"  → Weak domains updated: {self.weak_domains_file}")
        print("="*70 + "\n")
    
    # =====================================================
    # QUERYING LEARNED PATTERNS
    # =====================================================
    
    def get_learned_patterns_for_domain(self, domain: str) -> Dict[str, Any]:
        """
        Query: For a specific domain, what have we learned about success?
        
        Used by next session to replicate better approaches.
        """
        
        domain_history = []
        
        # Load all past insights
        if Path(self.insights_file).exists():
            with open(self.insights_file, "r") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        if domain in record.get("metrics", {}).get("domains", []):
                            domain_history.append(record)
                    except:
                        pass
        
        if not domain_history:
            return {"domain": domain, "message": "No prior experience with this domain"}
        
        # Analyze patterns
        satisfied_count = len([r for r in domain_history if r.get("metrics", {}).get("user_satisfied")])
        avg_turns = sum(r.get("metrics", {}).get("num_turns", 0) for r in domain_history) / len(domain_history)
        
        return {
            "domain": domain,
            "conversations_with_domain": len(domain_history),
            "satisfied_conversations": satisfied_count,
            "success_rate": f"{100 * satisfied_count / len(domain_history):.0f}%",
            "average_turns": f"{avg_turns:.1f}",
            "recommendation": self._suggest_pattern(domain_history),
        }
    
    def _suggest_pattern(self, domain_history: List[Dict[str, Any]]) -> str:
        """
        Based on history, suggest the best approach for this domain.
        """
        
        # Find the most successful conversation
        best = max(
            (r for r in domain_history if r.get("metrics", {}).get("user_satisfied")),
            key=lambda r: r.get("metrics", {}).get("num_turns", float("inf")),
            default=None
        )
        
        if best and best.get("metrics", {}).get("num_turns", 0) <= 3:
            return "✅ This domain achieves fast satisfaction. Replicate the quick-resolution pattern."
        elif best:
            return "⚠️ This domain needs thorough dialogue. Plan for multiple clarifying rounds."
        else:
            return "❓ No successful patterns found yet. Experiment with different approaches."


# =====================================================
# INTEGRATION HELPER
# =====================================================

def process_conversation_for_learning(
    conversation_result: Dict[str, Any],
    session_num: int,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to process a conversation through the ML learning pipeline.
    
    Call this after every conversation:
    
    ```python
    learning = process_conversation_for_learning(result, session_num=5)
    ```
    """
    
    processor = ConversationLearningProcessor()
    return processor.process_conversation(conversation_result, session_num)


if __name__ == "__main__":
    # Simple test
    test_result = {
        "problem_statement": "Should I change careers?",
        "domains": ["career", "psychology"],
        "stakes": "high",
        "turns": 3,
        "user_satisfied": True,
        "final_recommendation": "Consider negotiating with current employer first",
        "final_confidence": 0.85,
        "kis_items": [],
        "conversation_history": [
            {"speaker": "user", "text": "I'm unhappy at work"},
            {"speaker": "persona", "text": "What specifically makes you unhappy? Is it the role or the environment?"},
            {"speaker": "user", "text": "Both, actually. Low pay, high stress."},
        ]
    }
    
    processor = ConversationLearningProcessor()
    learning = processor.process_conversation(test_result, session_num=1)
    print(json.dumps(learning, indent=2))
