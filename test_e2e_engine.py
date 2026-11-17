from modules.council_execution.engine import NativeCouncil

def test_full_system():
    council = NativeCouncil()
    assert council.db is not None, "Database not initialized"
    
    # Analyze a scenario
    results = council.ministers["risk"].analyze(
        "I am quitting my job tomorrow without having a new one lined up. I have no savings and zero income. This exposes me to heavy financial bankruptcy.",
        {}
    )
    
    print("Risk Minister Results:")
    print("Stance:", results["stance"])
    print("Reasoning:", results["reasoning"])
    assert results["stance"] in ["oppose", "cautious", "neutral", "support", "bold"]
    
    # Try the adaptation minister
    results_adap = council.ministers["adaptation"].analyze(
        "I plan to switch careers to a completely new field and will take online courses to bridge the gap.",
        {}
    )
    
    print("Adaptation Minister Results:")
    print("Stance:", results_adap["stance"])
    print("Reasoning:", results_adap["reasoning"])

if __name__ == "__main__":
    test_full_system()
    print("Full system verification passed!")
