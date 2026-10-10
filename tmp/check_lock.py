import hashlib,json
from pathlib import Path
x=json.load(open('reports/rag_implementation_lock.json'))
for p,h in x['files'].items(): print(p,'OK' if hashlib.sha256(Path(p).read_bytes()).hexdigest()==h else 'CHANGED')
