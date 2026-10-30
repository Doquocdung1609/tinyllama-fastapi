"""Read-only local presentation preflight for an explicitly owned V3R2/V3R3 workspace."""
import argparse
import json
import sys
from pathlib import Path

import psutil
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.product.workspace import DIGEST, MODEL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--api', default='http://127.0.0.1:8110')
    parser.add_argument('--token-file', type=Path, default=Path('tmp/studio-runtime/access-token.txt'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    marker = args.workspace / 'search-v3r2.json'
    if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')).get('owner') != 'TOPIC3_V3R2_OWNER_CLONE':
        raise SystemExit('EXPLICIT_OWNER_WORKSPACE_REQUIRED')
    launcher=Path('tmp/studio-runtime/processes.json')
    launched=json.loads(launcher.read_text(encoding='utf-8')) if launcher.is_file() else {}
    workspace_matches=bool(launched.get('workspace')) and Path(launched['workspace']).resolve()==args.workspace.resolve()
    token = args.token_file.read_text(encoding='utf-8-sig').strip()
    session = requests.Session()
    session.headers['Authorization'] = 'Bearer ' + token

    def local(path):
        response = session.get(args.api + path, timeout=15)
        response.raise_for_status()
        return response.json()

    docs = local('/studio/documents')['documents']
    preparation = local('/studio/search-preparation')
    resources = local('/studio/resource-status')
    readiness = local('/studio/readiness')
    models = requests.get('http://127.0.0.1:11434/api/tags', timeout=10).json()['models']
    nomic = next((m for m in models if m.get('name') == MODEL), None)
    available = psutil.virtual_memory().available
    result = {
        'status': 'READY' if workspace_matches and docs and all(d['status'] == 'READY' for d in docs)
            and preparation['status'] == 'READY' and preparation['profile'] == 'production_v3r3'
            and nomic and nomic.get('digest') == DIGEST
            and readiness['ocr']['status'] == 'READY' and available >= 768*1024**2
            else 'WAIT_OR_REVIEW',
        'workspace': str(args.workspace.resolve()),
        'launcher_workspace_matches': workspace_matches,
        'document_count': len(docs),
        'all_documents_ready': bool(docs) and all(d['status'] == 'READY' for d in docs),
        'search_preparation': preparation,
        'model_digest_matches': bool(nomic and nomic.get('digest') == DIGEST),
        'ocr': readiness['ocr'],
        'available_ram_mib': round(available/1024**2, 2),
        'memory_warning': available < 1536*1024**2,
        'resource_admission': resources,
        'api_url': args.api,
        'advice': 'Use READY documents and prepared index; schedule OCR after presentation.'
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
