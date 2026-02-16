import requests

urls = [
    'http://localhost:11434/api/models',
    'http://localhost:11434/api/generate',
    'http://localhost:11434/authorize',
]
for u in urls:
    try:
        r = requests.get(u, timeout=10)
        print(f"{u} -> {r.status_code}")
        try:
            print(r.json())
        except Exception:
            print(r.text[:1000])
    except Exception as e:
        print(f"{u} -> ERROR: {e}")
