# API, Security, and Test Surface Map

## API Endpoints Detected in Code

- `hse/analytics_server.py` `flask_route` `/`
- `hse/analytics_server.py` `flask_route` `/stream`

## Security-Relevant Pattern Hits

- `cors_enable`: 1 file(s)
- `hardcoded_local_ollama`: 15 file(s)
- `open_bind_0_0_0_0`: 1 file(s)
- `postgres_default`: 5 file(s)
- `python_eval_call`: 0 file(s)
- `python_exec_call`: 0 file(s)
- `redis_default`: 1 file(s)
- `requests_verify_false`: 0 file(s)
- `skip_ollama_check`: 3 file(s)
- `subprocess_popen`: 5 file(s)

## Security Pattern Detail (first 50 files per pattern)

### `cors_enable`
- `hse/analytics_server.py` | L9: CORS(app)

### `hardcoded_local_ollama`
- `evaluation/gating_support.py` | L317: base_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
- `evaluation/kis2_retrieval.py` | L403: base_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
- `evaluation/run_phase2_robustness.py` | L72: "OLLAMA_HOST": "http://127.0.0.1:11434", ; L1707: status = requests.get("http://127.0.0.1:11434/api/tags", timeout=5).status_code
- `evaluation/run_phase2_with_gates.py` | L38: endpoint = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/") + "/api/tags"
- `ingestion/v2/src/async_workers.py` | L212: "http://localhost:11434/api/embed",
- `ingestion/v2/src/ingestion_config.py` | L218: "base_url": "http://localhost:11434",
- `ingestion/v2/src/ollama_client.py` | L15: """Ollama client using the local HTTP API at http://localhost:11434. ; L21: def __init__(self, model: Optional[str] = None, base_url: str = "http://localhost:11434"):
- `ml/llm_handshakes/llm_interface.py` | L251: base_url: str = "http://localhost:11434",
- `scripts/check_ollama_api.py` | L4: 'http://localhost:11434/api/models', ; L5: 'http://localhost:11434/api/generate', ; L6: 'http://localhost:11434/authorize',
- `tests/test_deepseek_doctrine.py` | L104: response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
- `tests/test_embed.py` | L2: u='http://localhost:11434/api/embed'
- `tests/test_embed_model.py` | L5: r=requests.post('http://localhost:11434/api/embed', json={'model':model,'input':texts}, timeout=30)
- `tests/test_generate.py` | L2: u='http://localhost:11434/api/generate'
- `tests/test_improved_doctrine.py` | L100: parse_url = "http://localhost:11434/api/generate" ; L136: print("\nERROR: Could not connect to Ollama at http://localhost:11434")
- `utils/ML_WISDOM_INTEGRATION_GUIDE.py` | L27: base_url="http://localhost:11434",

### `open_bind_0_0_0_0`
- `hse/analytics_server.py` | L63: app.run(host="0.0.0.0", port=port, threaded=True)

### `postgres_default`
- `ingestion/v2/src/async_ingest_orchestrator.py` | L208: db_dsn: Optional Postgres DSN (e.g., "postgresql://user:pass@localhost/db")
- `ingestion/v2/src/ASYNC_PIPELINE_GUIDE.py` | L245: db_dsn="postgresql://...",  # Optional; uses stub if not provided ; L270: db_dsn = "postgresql://user:password@localhost:5432/mydatabase"
- `ingestion/v2/src/ingestion_config.py` | L199: "connection_string": "postgresql://user:password@localhost:5432/era_ingestion",
- `ingestion/v2/src/integration_examples.py` | L69: db_dsn='postgresql://...'
- `ingestion/v2/src/minister_vector_db.py` | L102: "postgresql://user:pass@localhost:5432/minister_db")

### `python_eval_call`
- none
### `python_exec_call`
- none
### `redis_default`
- `ingestion/v2/src/distributed_queue.py` | L164: def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "era_ingestion"):

### `requests_verify_false`
- none
### `skip_ollama_check`
- `persona/ollama_runtime.py` | L6: - Boot-time ollama.list() availability check (hard fail unless SKIP_OLLAMA_CHECK=1) ; L42: # Honor environment override SKIP_OLLAMA_CHECK to allow development without daemon. ; L43: skip_check = os.getenv("SKIP_OLLAMA_CHECK", "").lower() in {"1", "true", "yes"}
- `run_benchmark.py` | L29: os.environ["SKIP_OLLAMA_CHECK"] = "1"  # Allow running without Ollama for now
- `run_eval_demo.py` | L22: os.environ["SKIP_OLLAMA_CHECK"] = "1"

### `subprocess_popen`
- `llm/ollama_model_selector.py` | L27: proc = subprocess.Popen(["ollama", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
- `multi_agent_sim/run_terminal.py` | L53: proc = subprocess.Popen([sys.executable, str(terminal_path)], env=env)
- `multi_agent_sim/terminal.py` | L68: proc = subprocess.Popen(
- `sovereign/sovereign_main.py` | L20: proc = subprocess.Popen(["ollama", "run", model], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
- `tests/sovereign_stress_test.py` | L90: proc = subprocess.Popen(["ollama", "run", model], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

## Test Inventory Summary

- Test python files: **58**
- Total test functions (name starts with `test_`): **62**
- Total test classes (name contains `Test`): **20**