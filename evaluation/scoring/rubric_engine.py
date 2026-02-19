"""
Rubric Engine - Loads and validates ground truth rubrics

Manages scenario rubrics, validates data integrity via hashing.
"""

import json
import hashlib
from typing import Dict, Optional
from pathlib import Path


class RubricEngine:
    """Load and validate evaluation rubrics"""
    
    def __init__(self, benchmark_dir: str = "evaluation/benchmark_dataset"):
        self.benchmark_dir = Path(benchmark_dir)
        self.scenarios = {}
        self.manifest = None
        self.hashes = {}
    
    def load_manifest(self) -> Dict:
        """Load and validate dataset manifest with SHA256 hashes"""
        manifest_path = self.benchmark_dir / "dataset_manifest.json"
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
        with open(manifest_path, 'r') as f:
            self.manifest = json.load(f)
        
        return self.manifest
    
    def verify_dataset_integrity(self) -> bool:
        """
        Verify all dataset files match their SHA256 hashes.
        
        Hard rule: No hash match → abort evaluation
        
        Returns:
            True if all hashes valid, False otherwise
        """
        
        if not self.manifest:
            self.load_manifest()
        
        expected_hashes = self.manifest.get("file_hashes", {})
        dataset_files = self.manifest.get("datasets", [])
        
        all_valid = True
        for dataset_file in dataset_files:
            file_path = self.benchmark_dir / dataset_file
            
            if not file_path.exists():
                print(f"❌ Missing file: {dataset_file}")
                all_valid = False
                continue
            
            actual_hash = self._compute_file_hash(file_path)
            expected_hash = expected_hashes.get(dataset_file)
            
            if actual_hash != expected_hash:
                print(f"❌ Hash mismatch for {dataset_file}")
                print(f"   Expected: {expected_hash}")
                print(f"   Actual:   {actual_hash}")
                all_valid = False
            else:
                print(f"✓ Hash valid: {dataset_file}")
                self.hashes[dataset_file] = actual_hash
        
        return all_valid
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def load_scenario(self, scenario_id: str, source_file: str = None) -> Dict:
        """
        Load a single scenario by ID
        
        Args:
            scenario_id: e.g., "IRR_001"
            source_file: e.g., "irreversible.json" (auto-detected if None)
        
        Returns:
            Scenario dict with ground_truth_rubric
        """
        
        # Try to find the scenario if source_file not specified
        if source_file is None:
            category = scenario_id.split('_')[0].lower()
            source_file = f"{category}.json"
        
        file_path = self.benchmark_dir / source_file
        
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {source_file}")
        
        with open(file_path, 'r') as f:
            scenarios = json.load(f)
        
        for scenario in scenarios:
            if scenario.get("id") == scenario_id:
                return scenario
        
        raise ValueError(f"Scenario {scenario_id} not found in {source_file}")
    
    def load_all_scenarios(self) -> Dict[str, Dict]:
        """Load all scenarios from all dataset files"""
        
        if not self.manifest:
            self.load_manifest()
        
        all_scenarios = {}
        
        for dataset_file in self.manifest.get("datasets", []):
            file_path = self.benchmark_dir / dataset_file
            
            if not file_path.exists():
                print(f"⚠ Skipping missing file: {dataset_file}")
                continue
            
            with open(file_path, 'r') as f:
                scenarios = json.load(f)
            
            for scenario in scenarios:
                scenario_id = scenario.get("id")
                if scenario_id:
                    all_scenarios[scenario_id] = scenario
        
        self.scenarios = all_scenarios
        return all_scenarios
    
    def get_rubric(self, scenario_id: str) -> Dict:
        """Get ground truth rubric for a scenario"""
        
        if scenario_id not in self.scenarios:
            self.load_scenario(scenario_id)
        
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")
        
        return scenario.get("ground_truth_rubric", {})
