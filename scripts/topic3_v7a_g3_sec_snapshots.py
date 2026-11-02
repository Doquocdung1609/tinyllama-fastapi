"""Acquire nine immutable original SEC primary HTML files for V7A G3 review.

Reads only the G3 source-bytes CSV and G2 filing metadata. Does not read answers,
gold labels, corpus chunks, retrieval outputs, or model results.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
import zipfile

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import get_settings  # noqa: E402
from app.financial_ingestion.sec_client import SECClient, SECRequestError, filing_source_url  # noqa: E402
from topic3_v7a_g3_finalize import finalize  # noqa: E402

CSV_NAME = 'AGENT2_G3_SOURCE_BYTES_REQUIRED.csv'
G2_MANIFEST = ROOT / 'docs/topic3_v7a_g2/V7A_SEC47_PRIVATE_SOURCE_MANIFEST.csv'
EXPECTED_FORMS = {'10-K', '10-Q', '20-F'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def index_form(html: bytes) -> str | None:
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all(class_='infoHead'):
        if tag.get_text(' ', strip=True).lower() == 'form':
            nxt = tag.find_next(class_='info')
            if nxt:
                return nxt.get_text(' ', strip=True).upper()
    text = soup.get_text(' ', strip=True)
    match = re.search(r'\bForm\s+(10-K|10-Q|20-F)\b', text, re.I)
    return match.group(1).upper() if match else None


def validate_input(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(rows) != 9 or len({r['accession'] for r in rows}) != 9:
        raise ValueError('G3 CSV must contain exactly nine distinct accessions')
    g2 = {r['accession_number']: r for r in csv_rows(G2_MANIFEST.read_bytes())}
    for r in rows:
        acc = r['accession']
        if acc not in g2 or r['source_url'] != g2[acc]['source_url'] or r['form'] != g2[acc]['form_type'] or r['ticker'] != g2[acc]['ticker']:
            raise ValueError(f'G3 source differs from frozen G2 filing manifest: {acc}')
        if r['form'] not in EXPECTED_FORMS:
            raise ValueError(f'Unexpected form in nine-source queue: {acc}')
        parsed = urlparse(r['source_url'])
        primary = Path(parsed.path).name
        if r['source_url'] != filing_source_url(g2[acc]['cik'], acc, primary):
            raise ValueError(f'G3 URL path does not match CIK/accession/primary document: {acc}')
    return rows


def boundary_checks(path: Path, form: str) -> dict[str, object]:
    raw = path.read_bytes()
    low = raw.lower()
    beginning = low[:8192]
    end = low[-8192:]
    html_open = b'<html' in beginning
    html_close = b'</html>' in end
    table_open_count = low.count(b'<table')
    table_close_count = low.count(b'</table>')
    access_denied = b'access denied' in beginning or b'undeclared automated tool' in beginning
    document_type_marker = bool(re.search(rb'(?:documenttype|document type|form type)[^<]{0,100}' + form.encode(), low[:500000], re.I))
    return {'html_open_near_start': html_open, 'html_close_near_end': html_close,
            'table_open_count': table_open_count, 'table_close_count': table_close_count,
            'access_denied_marker': access_denied, 'document_type_marker_in_primary': document_type_marker,
            'primary_boundary_pass': html_open and html_close and table_open_count > 0 and not access_denied}


def acquire(input_zip: Path, output_dir: Path) -> None:
    if output_dir.exists():
        raise FileExistsError(f'Refusing to overwrite existing handoff: {output_dir}')
    with zipfile.ZipFile(input_zip) as z:
        source_csv = z.read(CSV_NAME)
    rows = validate_input(csv_rows(source_csv))
    settings = get_settings()
    client = SECClient(settings.sec_user_agent, requests_per_second=1, timeout_seconds=40, max_retries=1)
    output_dir.mkdir(parents=True)
    raw_dir = output_dir / 'raw'
    index_dir = output_dir / 'filing_indexes'
    raw_dir.mkdir()
    index_dir.mkdir()
    records: list[dict[str, object]] = []
    for r in rows:
        acc, url, form = r['accession'], r['source_url'], r['form']
        cik = next(x['cik'] for x in csv_rows(G2_MANIFEST.read_bytes()) if x['accession_number'] == acc)
        primary_name = Path(urlparse(url).path).name
        path = raw_dir / f'{acc}__{primary_name}'
        rec: dict[str, object] = {'accession': acc, 'cik': cik, 'ticker': r['ticker'], 'form': form,
                                   'original_sec_url': url, 'primary_filename': primary_name,
                                   'retrieval_method': 'HTTPS GET via SECClient; configured contact User-Agent; 1 request/second',
                                   'representation': 'ORIGINAL_SEC_PRIMARY_HTML',
                                   'status': 'FETCH_PENDING'}
        try:
            result = client.download(url, path, max_bytes=100 * 1024 * 1024)
            rec.update({'acquired_at_utc': result.retrieved_at, 'http_status': result.status_code,
                        'content_type': result.content_type, 'final_response_url': result.final_url,
                        'file': path.relative_to(output_dir).as_posix(), 'byte_size': path.stat().st_size,
                        'sha256': sha(path.read_bytes()), 'boundary_checks': boundary_checks(path, form)})
            if result.status_code != 200 or result.final_url != url or 'html' not in (result.content_type or ''):
                rec['status'] = 'IDENTITY_OR_CONTENT_TYPE_FAILED'
            else:
                rec['status'] = 'PRIMARY_FETCHED_PENDING_INDEX'
        except Exception as exc:
            rec.update({'status': 'FETCH_FAILED', 'http_status': getattr(exc, 'status_code', None),
                        'error_type': type(exc).__name__, 'error': str(exc),
                        'acquired_at_utc': datetime.now(timezone.utc).isoformat()})
            records.append(rec)
            print(acc, rec['status'], rec.get('http_status'), flush=True)
            continue
        base = url.rsplit('/', 1)[0]
        listing_url = base + '/index.json'
        filing_index_url = base + '/' + acc + '-index.html'
        index_json_path = index_dir / f'{acc}__index.json'
        index_html_path = index_dir / f'{acc}__filing-index.html'
        index_check: dict[str, object] = {'index_json_url': listing_url, 'filing_index_url': filing_index_url}
        try:
            jres = client.download(listing_url, index_json_path, max_bytes=5 * 1024 * 1024)
            listing = json.loads(index_json_path.read_bytes())
            names = {x['name'] for x in listing.get('directory', {}).get('item', []) if isinstance(x, dict) and 'name' in x}
            index_check.update({'index_json_http_status': jres.status_code, 'index_json_final_url': jres.final_url,
                                'index_json_sha256': sha(index_json_path.read_bytes()),
                                'primary_filename_in_directory_listing': primary_name in names,
                                'directory_item_count': len(names), 'exhibit_like_files_count': sum(n.lower().startswith(('ex', 'exhibit')) for n in names),
                                'index_json_file': index_json_path.relative_to(output_dir).as_posix()})
        except Exception as exc:
            index_check.update({'index_json_error': str(exc), 'index_json_http_status': getattr(exc, 'status_code', None)})
        try:
            hres = client.download(filing_index_url, index_html_path, max_bytes=5 * 1024 * 1024)
            html_bytes = index_html_path.read_bytes()
            form_found = index_form(html_bytes)
            index_check.update({'filing_index_http_status': hres.status_code, 'filing_index_final_url': hres.final_url,
                                'filing_index_sha256': sha(html_bytes), 'form_reported_by_filing_index': form_found,
                                'form_matches': form_found == form,
                                'accession_in_filing_index_url': acc.replace('-', '') in hres.final_url or acc in hres.final_url,
                                'filing_index_file': index_html_path.relative_to(output_dir).as_posix()})
        except Exception as exc:
            index_check.update({'filing_index_error': str(exc), 'filing_index_http_status': getattr(exc, 'status_code', None)})
        rec['filing_index_crosscheck'] = index_check
        rec['identity_pass'] = bool(rec['status'] == 'PRIMARY_FETCHED_PENDING_INDEX'
                                    and rec['boundary_checks']['primary_boundary_pass']
                                    and index_check.get('primary_filename_in_directory_listing')
                                    and index_check.get('form_matches')
                                    and index_check.get('accession_in_filing_index_url'))
        rec['status'] = 'ORIGINAL_SEC_IDENTITY_PASS' if rec['identity_pass'] else 'SOURCE_ACQUIRED_IDENTITY_INCOMPLETE'
        rec['exhibits_boundary_note'] = 'Primary HTML only; separately listed exhibits in SEC filing index are not represented as bytes in this snapshot.'
        records.append(rec)
        print(acc, rec['status'], rec.get('byte_size'), flush=True)
    acquired = sum(bool(r.get('file')) for r in records)
    passed = sum(bool(r.get('identity_pass')) for r in records)
    manifest = {'status': 'G3_RAW_SEC_SOURCE_ACQUISITION_ONLY',
                'input_checkpoint_zip_sha256': sha(input_zip.read_bytes()),
                'input_csv_sha256': sha(source_csv),
                'frozen_g2_source_manifest_sha256': sha(G2_MANIFEST.read_bytes()),
                'requested': 9, 'acquired_primary_html': acquired, 'identity_pass': passed,
                'request_rate_per_second': 1, 'contact_user_agent_configured': True,
                'sources': records,
                'scientific_boundary': 'No answer/gold annotation or retrieval evaluation performed'}
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    (output_dir / 'V7A_G3_SOURCE_ACQUISITION_MANIFEST.json').write_bytes(manifest_bytes)
    missing = [r for r in records if not r.get('identity_pass')]
    (output_dir / 'V7A_G3_MISSING_OR_UNVERIFIED_SOURCES.json').write_bytes((json.dumps(missing, indent=2, ensure_ascii=False) + '\n').encode())
    lines = ['# V7A G3 raw SEC source acquisition', '',
             f'- Requested: 9; primary HTML acquired: {acquired}; identity checks passed: {passed}; missing or unverified: {len(missing)}.',
             '- Files are byte-preserved SEC responses. Primary HTML is distinct from filing indexes and separately stored exhibits.',
             '- No gold answers, question changes, corpus/index changes, retrieval runs or model tuning.', '',
             '| Accession | Form | Status | Bytes | SHA-256 |', '|---|---|---|---:|---|']
    for r in records:
        lines.append(f"| {r['accession']} | {r['form']} | {r['status']} | {r.get('byte_size', '')} | {r.get('sha256', '')} |")
    lines += ['', 'See the JSON manifest for exact URL, final response URL, UTC timestamp, HTTP metadata, file mapping, boundary checks and filing-index evidence.',
              'Original SEC archive access can be limited by SEC; each failed or unverified source remains explicit.']
    (output_dir / 'V7A_G3_ACQUISITION_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    files = sorted(p for p in output_dir.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt')
    sums = ''.join(f'{sha(p.read_bytes())}  {p.relative_to(output_dir).as_posix()}\n' for p in files)
    (output_dir / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8', newline='\n')
    print(json.dumps(finalize(output_dir), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-zip', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    acquire(args.input_zip, args.output_dir)


if __name__ == '__main__':
    main()
