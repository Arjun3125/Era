import requests
u='http://localhost:11434/api/embed'
payload={'model':'llama3.1:8b-instruct-q4_0','input':'test embedding'}
try:
    r=requests.post(u,json=payload,timeout=10)
    print('status',r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text[:200])
except Exception as e:
    print('ERROR',e)
