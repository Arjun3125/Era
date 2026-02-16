import requests, time
model='nomic-embed-text:latest'
texts=['test embedding one','another short text']
start=time.time()
r=requests.post('http://localhost:11434/api/embed', json={'model':model,'input':texts}, timeout=30)
print('status', r.status_code, 'elapsed', time.time()-start)
try:
    data=r.json()
    if isinstance(data, dict) and 'embeddings' in data:
        print('embedding count', len(data['embeddings']), 'dim', len(data['embeddings'][0]))
    elif isinstance(data, list):
        print('list count', len(data), 'dim', len(data[0]))
    else:
        print('response', data)
except Exception as e:
    print('json error', e, r.text)
