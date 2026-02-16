"""
Runtime that runs ministers, aggregates council, and asks PrimeConfident for final decision.
Provides a demo-run method that uses Mock ministers or real ministers.
"""
from typing import Dict, Any
from sovereign.council.aggregator import CouncilAggregator
from sovereign.prime_confident import PrimeConfident


class CouncilRuntime:
    def __init__(self, ministers: Dict[str, Any]):
        self.ministers = ministers
        self.aggregator = CouncilAggregator()
        self.prime = PrimeConfident()

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # call each minister
        outputs: Dict[str, Dict[str, Any]] = {}
        for name, minister in self.ministers.items():
            try:
                out = minister.advice(context)
            except Exception as e:
                out = {"minister": name, "stance": "caution", "confidence": 0.0, "error": str(e)}
            outputs[name] = out

        council_rec = self.aggregator.evaluate(outputs)
        final = self.prime.decide(council_rec, outputs)
        return {"minister_outputs": outputs, "council": council_rec, "prime": final}


# Simple mock minister example if run directly
if __name__ == "__main__":
    class MockMinister:
        def __init__(self, name, stance, conf):
            self.name = name
            self._stance = stance
            self._conf = conf

        def advice(self, context):
            return {"minister": self.name, "stance": self._stance, "confidence": self._conf}

    ministers = {
        "risk": MockMinister("risk", "oppose", 0.85),
        "ethics": MockMinister("ethics", "support", 0.6),
        "ops": MockMinister("ops", "support", 0.5),
    }
    runtime = CouncilRuntime(ministers)
    print(runtime.run({"scenario": "test"}))
