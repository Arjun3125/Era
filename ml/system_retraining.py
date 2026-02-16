# system_retraining.py

from collections import defaultdict


class SystemRetraining:

    def __init__(self, council, kis_engine, llm, metrics):
        self.council = council
        self.kis_engine = kis_engine
        self.llm = llm
        self.metrics = metrics
        self.learned_patterns = {}

    # --------------------------------------------------
    # SUCCESS PATTERN EXTRACTION
    # --------------------------------------------------

    def extract_success_patterns(self, num_recent_turns=100):

        recent = self.metrics.decisions[-num_recent_turns:]
        success_by_domain = defaultdict(list)

        for d in recent:
            if d["outcome"] == "success":
                success_by_domain[d["domain"]].append(d["stance"])

        self.learned_patterns = success_by_domain
        return success_by_domain

    # --------------------------------------------------
    # MINISTER RECALIBRATION
    # --------------------------------------------------

    def update_minister_confidence_formulas(self, domain):

        success_rate = self.metrics.success_rate(domain)

        for minister_name in self.council.ministers:
            if success_rate < 0.5:
                self.council.adjust_confidence(minister_name, domain, -0.05)
            else:
                self.council.adjust_confidence(minister_name, domain, +0.02)

    # --------------------------------------------------
    # DOCTRINE EVOLUTION
    # --------------------------------------------------

    def encode_learned_doctrine(self):

        for domain, stances in self.learned_patterns.items():
            if not stances:
                continue

            # Generate doctrinal summary using LLM
            prompt = f"""
Summarize the following successful strategic patterns
into a doctrinal rule for {domain} domain:

{stances}
"""
            doctrine_update = self.llm(prompt)

            self.kis_engine.add_doctrine(domain, doctrine_update)

    # --------------------------------------------------
    # KIS REBALANCING
    # --------------------------------------------------

    def rebalance_kis_weights(self):

        for cluster in self.metrics.failure_cluster_summary():
            if cluster["num_failures"] > 3:
                domain = cluster["domain"]
                self.kis_engine.penalize_domain(domain)

    # --------------------------------------------------
    # OPTIONAL LLM FINE-TUNING
    # --------------------------------------------------

    def retrain_llm_if_local(self, training_data_path="training_data.json"):

        # Export successful traces
        successful = [
            d for d in self.metrics.decisions
            if d["outcome"] == "success"
        ]

        with open(training_data_path, "w") as f:
            f.write(str(successful))

        print("Training data prepared. Use external fine-tuning pipeline.")
