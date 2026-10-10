import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
files=['app/services/rag_service.py','app/services/pdf_service.py','app/services/chunk_service.py','app/services/qdrant_service.py','app/services/calculation_service.py','app/api/documents.py','client.py']
obj={'locked_at':datetime.now(timezone.utc).isoformat(),'policy':'No application/retrieval tuning after this point; holdout results are audit-only.','files':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}}
Path('reports/rag_implementation_lock.json').write_text(json.dumps(obj,indent=2),encoding='utf-8')
print(obj['locked_at'])
