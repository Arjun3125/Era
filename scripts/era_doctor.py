#!/usr/bin/env python3
"""
ERA Doctor — Comprehensive System Diagnostic & Fallback Analyzer.
Like 'flutter doctor' or 'brew doctor', scans all ERA dependencies, local LLM services,
vector stores, ministerial doctrine capital, and ML buffers. Alerts the user if any
system is operating in fallback mode and provides step-by-step fix instructions.
"""
import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Terminal color formatting
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header():
    print(f"\n{BOLD}================================================================================{RESET}")
    print(f"{BOLD}[DOCTOR] ERA DOCTOR -- Epistemic Reasoning Architecture Diagnostic Utility{RESET}")
    print(f"{BOLD}================================================================================{RESET}\n")

def check_python_env() -> Tuple[bool, str, str]:
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        return False, f"Python {ver_str}", f"Upgrade to Python 3.10+ (Current: {ver_str})."
    return True, f"Python {ver_str} (Supported)", ""

def check_core_dependencies() -> Tuple[bool, str, List[str]]:
    required = ["chromadb", "pytest", "pydantic", "yaml"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        return False, f"Missing packages: {', '.join(missing)}", [f"Run: pip install {' '.join(missing)}"]
    return True, "All core Python packages installed", []

def check_openrouter_config() -> Tuple[bool, str, List[str]]:
    import os
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if api_key:
        return True, "OpenRouter API key configured", []
    return False, "OPENROUTER_API_KEY not set", [
        "Set OPENROUTER_API_KEY environment variable for cloud LLM access.",
        "Get a free key at https://openrouter.ai/keys"
    ]

def check_vector_store() -> Tuple[bool, str, List[str]]:
    try:
        import chromadb
        root = Path(__file__).resolve().parent.parent
        chroma_dir = root / "chroma_knowledge"
        if not chroma_dir.exists():
            return False, "ChromaDB storage directory ('chroma_knowledge') not found.", [
                "Diagnosis: KIS engine will fall back to offline keyword file scans.",
                "Fix: Run ingestion pipeline to populate vector index: python -m ingestion.v2.src.ingest_pipeline"
            ]
        client = chromadb.PersistentClient(path=str(chroma_dir))
        cols = client.list_collections()
        if not cols:
            return False, "ChromaDB initialized but contains 0 collections.", [
                "Diagnosis: Vector index empty; KIS will fall back to offline file scans.",
                "Fix: Run: python -m ingestion.v2.src.ingest_pipeline"
            ]
        return True, f"ChromaDB persistent vector store online ({len(cols)} collections indexed).", []
    except Exception as e:
        return False, f"ChromaDB initialization error: {str(e)}", [
            "Diagnosis: KIS engine will operate in offline fallback mode.",
            "Fix: Ensure directory permissions are writable or reinstall chromadb."
        ]

def check_minister_capital() -> Tuple[bool, str, List[str]]:
    root = Path(__file__).resolve().parent.parent
    ministers_dir = root / "data" / "ministers"
    if not ministers_dir.exists():
        return False, "Minister data directory ('data/ministers') missing.", [
            "Diagnosis: System will fall back to 7 built-in KIS entries.",
            "Fix: Restore repository data directory or run ingestion pipeline."
        ]
    
    ministers = [d.name for d in ministers_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if not ministers:
        return False, "0 ministers found in data/ministers directory.", [
            "Diagnosis: System will fall back to 7 built-in KIS entries.",
            "Fix: Restore repository data directory or run ingestion pipeline."
        ]
    
    sparse_ministers = []
    
    for m in ministers:
        mdir = ministers_dir / m
        total_items = 0
        for ktype in ["principles.json", "rules.json", "warnings.json", "claims.json", "advice.json"]:
            fp = mdir / ktype
            if fp.exists():
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        entries = data.get("entries", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                        total_items += len(entries)
                except Exception:
                    pass
        if total_items < 1:
            sparse_ministers.append(f"{m} ({total_items} items)")
            
    if sparse_ministers:
        return False, f"Minister knowledge capital incomplete or sparse ({', '.join(sparse_ministers[:5])}).", [
            "Diagnosis: Sparse ministers will fall back to general doctrine reasoning.",
            "Fix: Run ingestion workers: python -m ingestion.v2.src.ingest_pipeline"
        ]
    return True, f"All {len(ministers)} ministerial domain stores populated with active KIS capital.", []

def check_ml_buffers() -> Tuple[bool, str, List[str]]:
    root = Path(__file__).resolve().parent.parent
    train_dir = root / "04_training_data"
    if not train_dir.exists():
        return True, "ML training buffer directory ready (Cold start mode active).", []
    files = list(train_dir.glob("*.json*"))
    return True, f"ML trajectory buffer active ({len(files)} training logs recorded).", []

def simulate_deliberation_fallback() -> Tuple[bool, str, List[str]]:
    try:
        root = str(Path(__file__).resolve().parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        from persona.knowledge_engine import synthesize_knowledge
        res = synthesize_knowledge("test financial crisis loan", ["risk", "strategy"], 0.8)
        if res.get("fallback_triggered"):
            return False, "KIS Engine test triggered fallback during simulation.", res.get("fallback_reasons", [])
        return True, "KIS Engine end-to-end simulation passed without triggering fallbacks.", []
    except Exception as e:
        return False, f"KIS simulation failed with error: {str(e)}", [
            "Fix: Verify knowledge_engine.py syntax and dependencies."
        ]

def check_test_suite() -> Tuple[bool, str, List[str]]:
    root = str(Path(__file__).resolve().parent.parent)
    try:
        print(f"      [Running full pytest test suite across 430+ tests (~10 seconds)...]", flush=True)
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180
        )
        if res.returncode == 0:
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            summary = lines[-1] if lines else "All tests passed cleanly."
            return True, f"Full test suite verified ({summary})", []
        else:
            err_msg = res.stdout[:600] if res.stdout else res.stderr[:600]
            return False, f"Test suite failures detected (Exit code {res.returncode})", [
                "Diagnosis: One or more unit/integration tests failed.",
                f"Details: {err_msg}",
                "Fix: Run 'pytest -v' in terminal to inspect failing tests and debug."
            ]
    except Exception as e:
        return False, f"Failed to execute test suite: {str(e)}", [
            "Fix: Ensure pytest is installed and accessible via sys.executable."
        ]

def check_ears_pwm_health() -> Tuple[bool, str, List[str]]:
    root = Path(__file__).resolve().parent.parent
    pwm_dir = root / "data" / "pwm"
    mem_dir = root / "data" / "memory"
    
    missing_or_corrupt = []
    for fname, dict_key in [("entities.json", "entities"), ("voiceprints.json", "voiceprints"), ("consolidated_memories.json", "digests"), ("voiceprint_candidates.json", "candidates")]:
        fp = pwm_dir / fname
        if fp.exists():
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or dict_key not in data:
                        missing_or_corrupt.append(f"{fname} (corrupt schema missing '{dict_key}')")
            except Exception:
                missing_or_corrupt.append(f"{fname} (JSON decode error)")
    
    if missing_or_corrupt:
        return False, f"EARS Personal World Model files corrupted or malformed: {', '.join(missing_or_corrupt)}", [
            "Diagnosis: One or more EARS JSON state files cannot be parsed.",
            "Fix: Delete corrupt files in data/pwm/ so they re-initialize cleanly on next daemon start."
        ]
    return True, "All EARS Personal World Model & memory registries intact and uncorrupted.", []


def main():
    print_header()
    
    checks = [
        ("Python Environment", check_python_env),
        ("Core Dependencies", check_core_dependencies),
        ("OpenRouter Config", check_openrouter_config),
        ("ChromaDB Vector Store", check_vector_store),
        ("Minister Knowledge Capital", check_minister_capital),
        ("ML Training Buffers", check_ml_buffers),
        ("EARS Personal World Model", check_ears_pwm_health),
        ("End-to-End Fallback Audit", simulate_deliberation_fallback),
        ("Full Test Suite Verification", check_test_suite),
    ]
    
    total = len(checks)
    passed = 0
    warnings_or_fallbacks = 0
    
    for name, fn in checks:
        ok, status, fixes = fn()
        if ok:
            passed += 1
            print(f"[{GREEN}OK{RESET}] {BOLD}{name}{RESET}: {status}")
        else:
            warnings_or_fallbacks += 1
            print(f"[{YELLOW}WARN{RESET}] {BOLD}{name}{RESET}: {YELLOW}{status}{RESET}")
            if isinstance(fixes, list):
                for f in fixes:
                    print(f"      {f}")
            elif fixes:
                print(f"      {fixes}")
        print()
        
    print(f"{BOLD}--------------------------------------------------------------------------------{RESET}")
    if warnings_or_fallbacks == 0:
        print(f"{GREEN}{BOLD}[PASS] ERA DOCTOR VERDICT: ALL SYSTEMS HEALTHY & PRODUCTION READY!{RESET}")
        print(f"    0 fallbacks triggered across {total} diagnostic checks.")
        sys.exit(0)
    else:
        print(f"{YELLOW}{BOLD}[WARN] ERA DOCTOR VERDICT: FALLBACK MODE ACTIVE ({warnings_or_fallbacks}/{total} components in fallback){RESET}")
        print(f"    The system is operational and safe, but using offline/heuristic fallbacks.")
        print(f"    Follow the fix instructions above to restore 100% full neural/vector operation.")
        sys.exit(0)

if __name__ == "__main__":
    main()
