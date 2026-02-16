# episodic_memory.py

import json
import os
import hashlib
from datetime import datetime
from collections import defaultdict
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss


class EpisodicMemory:

    def __init__(self, storage_path="episodic_store"):
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)

        self.episodes = []
        self.failure_clusters = defaultdict(list)

        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.dimension = 384
        self.index = faiss.IndexFlatL2(self.dimension)

        self.meta = []

        self._load()

    # -----------------------------------------------------
    # CORE STORAGE
    # -----------------------------------------------------

    def store_episode(self, turn_id, domain, decision, confidence, outcome, consequences):
        episode = {
            "turn_id": turn_id,
            "domain": domain,
            "decision": decision,
            "confidence": confidence,
            "outcome": outcome,
            "consequences": consequences,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        self.episodes.append(episode)

        text_repr = f"{domain} | {decision} | {outcome}"
        emb = self.embedding_model.encode([text_repr])
        self.index.add(np.array(emb).astype("float32"))
        self.meta.append(episode)

        if outcome == "failure":
            pattern_key = self._hash_pattern(domain, decision)
            self.failure_clusters[pattern_key].append(turn_id)

        self._save()

    # -----------------------------------------------------
    # RETRIEVAL
    # -----------------------------------------------------

    def find_similar_episodes(self, current_domain, current_decision, k=5):
        if not self.meta:
            return []

        query = f"{current_domain} | {current_decision}"
        emb = self.embedding_model.encode([query])
        D, I = self.index.search(np.array(emb).astype("float32"), k)

        results = []
        for idx in I[0]:
            if idx < len(self.meta):
                results.append(self.meta[idx])

        return results

    # -----------------------------------------------------
    # PATTERN DETECTION
    # -----------------------------------------------------

    def detect_pattern_repetition(self, new_domain, new_decision):
        pattern_key = self._hash_pattern(new_domain, new_decision)

        if pattern_key in self.failure_clusters:
            return {
                "repetition": True,
                "past_failures": self.failure_clusters[pattern_key]
            }

        return {"repetition": False}

    # -----------------------------------------------------
    # CONTRADICTION DETECTION
    # -----------------------------------------------------

    def detect_contradiction(self, domain, new_decision):
        contradictions = []

        for ep in self.episodes:
            if ep["domain"] == domain:
                if self._is_conflicting(ep["decision"], new_decision):
                    contradictions.append(ep)

        return contradictions

    def _is_conflicting(self, past_decision, new_decision):
        # naive rule: detect opposite verbs
        negative_keywords = ["reduce", "cut", "stop", "avoid"]
        positive_keywords = ["increase", "expand", "invest", "accelerate"]

        for neg in negative_keywords:
            for pos in positive_keywords:
                if neg in past_decision.lower() and pos in new_decision.lower():
                    return True
                if pos in past_decision.lower() and neg in new_decision.lower():
                    return True

        return False

    # -----------------------------------------------------
    # ENFORCEMENT LAYER
    # -----------------------------------------------------

    def enforce_memory_constraint(self, domain, proposed_response):
        contradictions = self.detect_contradiction(domain, proposed_response)
        repetition = self.detect_pattern_repetition(domain, proposed_response)

        if contradictions:
            return {
                "allowed": False,
                "reason": "Contradicts past decision in same domain.",
                "conflicts": contradictions
            }

        if repetition["repetition"]:
            return {
                "allowed": False,
                "reason": "Repeating past failed pattern.",
                "failures": repetition["past_failures"]
            }

        return {"allowed": True}

    # -----------------------------------------------------
    # INTERNAL
    # -----------------------------------------------------

    def _hash_pattern(self, domain, decision):
        return hashlib.sha256(f"{domain}-{decision}".encode()).hexdigest()

    def _save(self):
        with open(os.path.join(self.storage_path, "episodes.json"), "w") as f:
            json.dump(self.episodes, f, indent=2)

    def _load(self):
        file_path = os.path.join(self.storage_path, "episodes.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                self.episodes = json.load(f)

            for ep in self.episodes:
                text_repr = f"{ep['domain']} | {ep['decision']} | {ep['outcome']}"
                emb = self.embedding_model.encode([text_repr])
                self.index.add(np.array(emb).astype("float32"))
                self.meta.append(ep)

                if ep["outcome"] == "failure":
                    key = self._hash_pattern(ep["domain"], ep["decision"])
                    self.failure_clusters[key].append(ep["turn_id"])
