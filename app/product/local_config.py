"""Worktree-local non-secret SEC roots; independent of transient shell state."""
import json,os
from pathlib import Path
from app.config import ROOT_DIR

KEYS=('STUDIO_SEC_RESEARCH_ROOT','STUDIO_SEC_VECTOR_ROOT','TOPIC3_RESEARCH_ROOT')
def sec_roots():
    path=Path(os.getenv('STUDIO_LOCAL_CONFIG',str(ROOT_DIR/'tmp/studio-runtime/sec-config.json')))
    config=json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}
    roots={k:str(config.get(k) or os.getenv(k,'')).strip() for k in KEYS}
    for key,value in roots.items():
        if value and not Path(value).is_dir():raise ValueError('SEC_CONFIG_PATH_MISSING:'+key)
    return roots
