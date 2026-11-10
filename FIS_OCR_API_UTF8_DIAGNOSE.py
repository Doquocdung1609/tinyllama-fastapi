#!/usr/bin/env python3
"""Read-only FIS OCR/API encoding diagnosis for Windows.

Run inside the user's project worktree with Python 3.11+:
  python FIS_OCR_API_UTF8_DIAGNOSE.py
No third-party dependencies. Does not alter PDFs, OCR checkpoints, indexes, or API.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request
import urllib.error

MARKERS = ('Ã', 'á»', 'Ä', 'Æ', 'â\x80', 'Â')

def corruption_score(text: str) -> int:
    return sum(text.count(x) for x in MARKERS)

def reversible_repair(s: str) -> str | None:
    try:
        candidate = s.encode('latin-1').decode('utf-8', errors='strict')
        if candidate.encode('utf-8').decode('latin-1') == s:
            return candidate
    except (UnicodeError, ValueError):
        pass
    return None

def main() -> int:
    ap = argparse.ArgumentParser(description='Diagnose OCR JSON encoding directly from FIS API')
    ap.add_argument('--base', default='http://127.0.0.1:18110/studio')
    ap.add_argument('--token-file', default='tmp/studio-runtime/access-token.txt')
    ap.add_argument('--document-id', default='4a92af827aaf1e73e017544d0ff20d0d')
    ap.add_argument('--pages', default='3,4,5,6,12,13,24')
    ap.add_argument('--output', default='tmp/ocr-utf8-api-diagnostic')
    args = ap.parse_args()
    token_path = Path(args.token_file)
    if not token_path.is_file():
        print(f'ERROR: missing token file: {token_path}', file=sys.stderr)
        return 2
    token = token_path.read_text(encoding='utf-8-sig').strip()
    if not token: raise ValueError('Empty token file')
    outdir = Path(args.output); outdir.mkdir(parents=True, exist_ok=True)
    pages = [int(s.strip()) for s in args.pages.split(',') if s.strip()]
    report = {'source': 'LOCAL_FIS_API_READ_ONLY', 'document_id': args.document_id, 'pages': []}
    for page_num in pages:
        url = f'{args.base.rstrip("/")}/documents/{args.document_id}/pages/{page_num}/evidence'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=45) as res:
                content_type = res.headers.get('Content-Type', '')
                payload = res.read()
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            print(f'PAGE {page_num}: HTTP/connection failure: {exc}')
            report['pages'].append({'page': page_num, 'error': str(exc)})
            continue
        try:
            decoded = payload.decode('utf-8', errors='strict')
            response = json.loads(decoded)
        except (UnicodeError, json.JSONDecodeError) as exc:
            print(f'PAGE {page_num}: INVALID UTF-8 or JSON: {exc}')
            report['pages'].append({'page': page_num, 'error': 'INVALID_UTF8_OR_JSON'})
            continue
        extracted = response.get('text', '')
        score = corruption_score(extracted)
        corrected = reversible_repair(extracted) if score >= 6 else None
        repaired_score = corruption_score(corrected) if corrected is not None else None
        recommendation = ('API_TEXT_CONTAINS_REVERSIBLE_MOJIBAKE' if corrected is not None and repaired_score < score
                          else 'API_TEXT_NOT_SYSTEMATICALLY_MOJIBAKE')
        prefix = outdir / f'HPG_page_{page_num}'
        (prefix.with_suffix('.api_utf8.txt')).write_text(extracted, encoding='utf-8-sig')
        (prefix.with_suffix('.api_raw.json')).write_bytes(payload)
        if corrected is not None and repaired_score < score:
            (prefix.with_suffix('.api_display_repair_only.txt')).write_text(corrected, encoding='utf-8-sig')
        item = {
            'page': page_num, 'method': response.get('method'),
            'status': response.get('status'), 'quality': response.get('quality'),
            'content_type': content_type,
            'raw_response_sha256': hashlib.sha256(payload).hexdigest(),
            'raw_utf8_valid': True, 'mojibake_score_api': score,
            'score_after_possible_repair': repaired_score,
            'diagnosis': recommendation,
        }
        report['pages'].append(item)
        print(f'PAGE {page_num}: {recommendation}; score={score}; method={item["method"]}; '
              f'raw API UTF-8 bytes={len(payload)}')
        for line in [x.strip() for x in extracted.splitlines() if x.strip()][:4]:
            print('   API:', line[:115])
    result_path = outdir / 'report.json'
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8-sig')
    print(f'\nSaved read-only diagnostic outputs to: {outdir}')
    print('If API_TEXT_NOT_SYSTEMATICALLY_MOJIBAKE, test PowerShell REST decoding/console encoding before editing OCR backend.')
    print('If API_TEXT_CONTAINS_REVERSIBLE_MOJIBAKE, inspect Tesseract and serialization boundaries; never bulk-repair verified clean text.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
