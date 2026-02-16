"""Quick environment verification script for ingestion pipeline.

Run:
    python scripts/check_requirements.py

It will attempt to import key packages and report success/failure so you can
confirm `pip install -r requirements.txt` completed correctly.
"""

packages = [
    ("requests", "requests"),
    ("aiohttp", "aiohttp"),
    ("asyncpg", "asyncpg"),
    ("pypdf", "pypdf"),
    ("psycopg2", "psycopg2"),
    ("pgvector", "pgvector"),
    ("dotenv", "dotenv"),
]

failed = []
for name, mod in packages:
    try:
        __import__(mod)
        print(f"OK: {name}")
    except Exception as e:
        print(f"MISSING: {name} -> import error: {e}")
        failed.append(name)

if failed:
    print("\nSome packages are missing. Install with:")
    print("    python -m pip install -r requirements.txt")
    raise SystemExit(1)

print("\nAll checks passed.")
