"""
Outcome Recording Module - Step 4: Training Data Collection

Records decision outcomes and persists them for ML training.

Pipeline:
1. Decision made → stored in memory
2. Outcome observed → recorded to database 
3. Training data generated → fed to ML models
4. Learned weights → applied back to system
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import hashlib


class OutcomeDatabase:
    """
    Persistent storage for decision outcomes.
    
    Stores raw decision-outcome pairs that can be converted to training data.
    """
    
    def __init__(self, storage_path: str = "ml/cache/outcomes"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Main outcome records
        self.outcomes_file = self.storage_path / "outcome_records.jsonl"  # One JSON per line
        self.index_file = self.storage_path / "outcome_index.json"
        
        # Statistics
        self.stats_file = self.storage_path / "outcome_stats.json"
        
        self.index: Dict[str, Dict[str, Any]] = {}
        self._load_index()
    
    def _load_index(self):
        """Load outcome index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    self.index = json.load(f)
            except Exception:
                self.index = {}
    
    def _save_index(self):
        """Save index to disk."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def record_decision(
        self,
        decision_id: str,
        user_input: str,
        llm_analysis: Dict[str, Any],
        kis_guidance: Dict[str, Any],
        situation_features: Dict[str, float],
        constraint_features: Dict[str, float],
        knowledge_features: Dict[str, float],
        action: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a decision that was made.
        
        Returns decision_key for later outcome recording.
        """
        decision_record = {
            "decision_id": decision_id,
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            
            # LLM handshake output
            "llm_analysis": llm_analysis,
            
            # KIS guidance
            "kis_guidance": kis_guidance,
            
            # Feature vectors for training
            "situation_features": situation_features,
            "constraint_features": constraint_features,
            "knowledge_features": knowledge_features,
            
            # Action taken (optional)
            "action": action,
            
            # Outcome (will be filled later)
            "outcome": None,
            "outcome_timestamp": None,
        }
        
        decision_key = self._generate_decision_key(decision_id)
        
        # Append to outcomes file
        with open(self.outcomes_file, 'a') as f:
            f.write(json.dumps({
                "key": decision_key,
                "record": decision_record
            }) + '\n')
        
        # Update index
        self.index[decision_key] = {
            "decision_id": decision_id,
            "recorded_at": datetime.now().isoformat(),
            "has_outcome": False,
        }
        self._save_index()
        
        return decision_key
    
    def record_outcome(
        self,
        decision_key: str,
        success: bool,
        regret_score: float = 0.0,
        recovery_time_days: int = 0,
        secondary_damage: bool = False,
        notes: str = ""
    ) -> bool:
        """
        Record outcome for a previously recorded decision.
        
        Returns True if successful.
        """
        if decision_key not in self.index:
            return False
        
        outcome = {
            "success": success,
            "regret_score": regret_score,
            "recovery_time_days": recovery_time_days,
            "secondary_damage": secondary_damage,
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Read all outcomes, update the matching one, write back
        records = []
        found = False
        
        try:
            with open(self.outcomes_file, 'r') as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        if item["key"] == decision_key:
                            item["record"]["outcome"] = outcome
                            item["record"]["outcome_timestamp"] = outcome["timestamp"]
                            found = True
                        records.append(item)
        except FileNotFoundError:
            return False
        
        if not found:
            return False
        
        # Write back
        with open(self.outcomes_file, 'w') as f:
            for item in records:
                f.write(json.dumps(item) + '\n')
        
        # Update index
        self.index[decision_key]["has_outcome"] = True
        self.index[decision_key]["outcome_recorded_at"] = datetime.now().isoformat()
        self._save_index()
        
        return True
    
    def get_decision(self, decision_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a decision record by key."""
        try:
            with open(self.outcomes_file, 'r') as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        if item["key"] == decision_key:
                            return item["record"]
        except FileNotFoundError:
            return None
        
        return None
    
    def get_all_decisions_with_outcomes(self) -> List[Dict[str, Any]]:
        """
        Get all decisions that have recorded outcomes.
        
        For training data generation.
        """
        records = []
        
        try:
            with open(self.outcomes_file, 'r') as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        record = item["record"]
                        
                        # Only include records with outcomes
                        if record.get("outcome"):
                            records.append(record)
        except FileNotFoundError:
            pass
        
        return records
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get outcome database statistics."""
        total_decisions = len(self.index)
        decisions_with_outcomes = sum(
            1 for v in self.index.values() 
            if v.get("has_outcome", False)
        )
        
        outcomes = self.get_all_decisions_with_outcomes()
        
        successful = sum(1 for r in outcomes if r["outcome"]["success"])
        with_regret = sum(1 for r in outcomes if r["outcome"]["regret_score"] > 0.5)
        with_secondary_damage = sum(1 for r in outcomes if r["outcome"]["secondary_damage"])
        
        return {
            "total_decisions_recorded": total_decisions,
            "decisions_with_outcomes": decisions_with_outcomes,
            "success_rate": successful / decisions_with_outcomes if decisions_with_outcomes > 0 else 0.0,
            "high_regret_count": with_regret,
            "secondary_damage_count": with_secondary_damage,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _generate_decision_key(self, decision_id: str) -> str:
        """Generate unique key for decision."""
        timestamp = datetime.now().isoformat()
        combined = f"{decision_id}_{timestamp}"
        hash_val = hashlib.md5(combined.encode()).hexdigest()[:8]
        return f"dec_{decision_id}_{hash_val}"


class TrainingDataGenerator:
    """
    Converts outcome records to training data for ML models.
    """
    
    def __init__(self, outcome_db: OutcomeDatabase):
        self.outcome_db = outcome_db
    
    def generate_training_dataset(self) -> List[Dict[str, Any]]:
        """
        Convert outcome records to training dataset.
        
        Each training sample:
        {
            "features": {...situation_features, ...constraint_features, ...knowledge_features},
            "label": {type weights from label_generator},
            "outcome": {...raw outcome...},
            "decision_id": str
        }
        """
        from ..labels.label_generator import generate_type_weights
        
        training_samples = []
        outcomes = self.outcome_db.get_all_decisions_with_outcomes()
        
        for record in outcomes:
            # Combine all features
            features = {
                **record.get("situation_features", {}),
                **record.get("constraint_features", {}),
                **record.get("knowledge_features", {}),
            }
            
            # Generate labels from outcome
            label = generate_type_weights(
                record.get("situation_features", {}),
                record.get("constraint_features", {}),
                record.get("knowledge_features", {}),
                record.get("outcome", {})
            )
            
            training_samples.append({
                "decision_id": record.get("decision_id", "unknown"),
                "features": features,
                "label": label.to_dict(),
                "outcome": record.get("outcome", {}),
                "timestamp": record.get("timestamp", ""),
            })
        
        return training_samples
    
    def save_training_dataset(
        self,
        dataset: List[Dict[str, Any]],
        output_path: str = "ml/cache/training_datasets"
    ) -> str:
        """
        Save training dataset to disk.
        
        Returns path to saved file.
        """
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"training_dataset_{timestamp}.json"
        filepath = Path(output_path) / filename
        
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "num_samples": len(dataset),
                "samples": dataset,
            }, f, indent=2)
        
        return str(filepath)


class FeedbackIntegrator:
    """
    Integrates trained ML models back into the system.
    
    Pipeline:
    1. Generate training data from outcomes
    2. Train ML judgment prior
    3. Save trained model state
    4. Apply learned weights to future decisions
    """
    
    def __init__(
        self,
        outcome_db: OutcomeDatabase,
        ml_prior: Any = None,  # MLJudgmentPrior
        cache_dir: str = "ml/cache"
    ):
        self.outcome_db = outcome_db
        self.ml_prior = ml_prior
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.training_log = self.cache_dir / "training_log.jsonl"
    
    def run_training_cycle(self) -> Dict[str, Any]:
        """
        Complete training cycle: outcomes → training data → train model → save weights.
        
        Returns training statistics.
        """
        if not self.ml_prior:
            return {"status": "error", "reason": "ML prior not available"}
        
        # Generate training data
        generator = TrainingDataGenerator(self.outcome_db)
        dataset = generator.generate_training_dataset()
        
        if len(dataset) < 5:
            return {
                "status": "skipped",
                "reason": f"Insufficient training data ({len(dataset)} samples, need >= 5)",
            }
        
        # Add to ML model
        for sample in dataset:
            self.ml_prior.add_training_sample(
                sample["features"],
                sample["label"]
            )
        
        # Train
        trained = self.ml_prior.train(force=True)
        
        if not trained:
            return {
                "status": "failed",
                "reason": "ML model training returned False",
            }
        
        # Save trained weights
        model_file = self._save_trained_model()
        
        # Save dataset
        dataset_file = generator.save_training_dataset(dataset)
        
        # Log training event
        training_event = {
            "timestamp": datetime.now().isoformat(),
            "samples_trained": len(dataset),
            "model_file": model_file,
            "dataset_file": dataset_file,
            "learned_priors": self.ml_prior.learned_priors,
        }
        
        with open(self.training_log, 'a') as f:
            f.write(json.dumps(training_event) + '\n')
        
        return {
            "status": "success",
            "samples_trained": len(dataset),
            "model_file": model_file,
            "dataset_file": dataset_file,
            "learned_priors_count": len(self.ml_prior.learned_priors),
        }
    
    def _save_trained_model(self) -> str:
        """Save trained model state."""
        models_dir = Path("ml/models")
        models_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_file = models_dir / f"judgment_prior_{timestamp}.json"
        
        # Save model state
        model_data = {
            "timestamp": datetime.now().isoformat(),
            "num_training_samples": self.ml_prior.state.num_training_samples,
            "training_epochs": self.ml_prior.state.training_epochs,
            "learned_priors": self.ml_prior.learned_priors,
        }
        
        with open(model_file, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        return str(model_file)
    
    def apply_learned_weights(self) -> Dict[str, Dict[str, float]]:
        """
        Get learned weights for use in future decisions.
        
        These weights adjust KIS scoring based on historical success.
        """
        if not self.ml_prior or not self.ml_prior.learned_priors:
            return {}
        
        return self.ml_prior.learned_priors
