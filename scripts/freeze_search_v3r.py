"""Freeze all runtime/search/performance policy before opening any new test source."""
import argparse,json,hashlib,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.product.workspace import OllamaEmbedder
from app.config import get_settings

REPO=Path(__file__).resolve().parents[1]
def snapshot():
    paths={p for pattern in ['app/**/*.py','frontend/src/**/*','frontend/e2e/*v3r*','scripts/*v3r*.py','tests/*v3r*.py','tests/test_region_pdf_extraction.py'] for p in REPO.glob(pattern) if p.is_file()}
    paths|={REPO/p for p in ['main.py','requirements.txt','frontend/package.json','frontend/package-lock.json','scripts/run_financial_studio.ps1']}
    files={str(p.relative_to(REPO)).replace('\\','/'):hashlib.sha256(p.read_text(encoding='utf-8').encode()).hexdigest() for p in sorted(paths)}
    resources={name:hashlib.sha256((get_settings().tessdata_dir/(name+'.traineddata')).read_bytes()).hexdigest() for name in ('eng','vie','osd')}
    body={'canonical_source_files':files,'active_ocr_languages':resources,'embedding':OllamaEmbedder().identity(),'policy':'V3R regions;V3 unchanged scoring;exact IFRS source-label candidates;reviewed numeric cells only;source validation on every search'}
    return {**body,'policy_sha256':hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--lock',default='docs/search_v3r/POLICY_LOCK.json');p.add_argument('--verify',action='store_true');a=p.parse_args();path=Path(a.lock);current=snapshot()
    if a.verify:
        saved=json.loads(path.read_text(encoding='utf-8'))
        if saved['policy_sha256']!=current['policy_sha256']:raise ValueError('FROZEN_POLICY_CHANGED')
        print('FROZEN_POLICY_VERIFIED',current['policy_sha256'])
    else:
        if path.exists():raise ValueError('POLICY_ALREADY_FROZEN')
        path.write_text(json.dumps({**current,'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'protocol':'New source contents/questions not opened before freeze. Single agent annotation remains provisional;owner audit pending.'},indent=2)+'\n',encoding='utf-8');print('POLICY_FROZEN',current['policy_sha256'])
