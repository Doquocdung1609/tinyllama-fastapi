"""Finalize and verify a V7A G3 SEC source handoff without contacting SEC."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from bs4 import BeautifulSoup


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def finalize(directory: Path) -> dict[str, object]:
    manifest_path = directory / 'V7A_G3_SOURCE_ACQUISITION_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('requested') != 9 or len(manifest.get('sources', [])) != 9:
        raise ValueError('Expected exactly nine immutable source records')
    for rec in manifest['sources']:
        if not rec.get('file'):
            rec['identity_pass'] = False
            rec['representation'] = 'NOT_ACQUIRED'
            continue
        primary = directory / rec['file']
        raw = primary.read_bytes()
        if sha(raw) != rec['sha256'] or len(raw) != rec['byte_size']:
            raise ValueError(f'Primary bytes changed: {rec["accession"]}')
        checks = rec['boundary_checks']
        checks['table_tags_balanced'] = checks['table_open_count'] == checks['table_close_count']
        checks['financial_statement_heading_observed'] = any(term in raw.lower() for term in (b'consolidated statements', b'consolidated financial statements', b'financial statements'))
        checks['primary_boundary_pass'] = bool(checks['html_open_near_start'] and checks['html_close_near_end']
                                               and checks['table_open_count'] > 0 and checks['table_tags_balanced']
                                               and checks['financial_statement_heading_observed']
                                               and not checks['access_denied_marker'])
        idx = rec['filing_index_crosscheck']
        if not idx.get('index_json_file') or not idx.get('filing_index_file'):
            rec['identity_pass'] = False
            rec['status'] = 'SOURCE_ACQUIRED_IDENTITY_INCOMPLETE'
            rec['representation'] = 'UNVERIFIED_SEC_RESPONSE'
            continue
        idx_json = (directory / idx['index_json_file']).read_bytes()
        idx_html = (directory / idx['filing_index_file']).read_bytes()
        if sha(idx_json) != idx['index_json_sha256'] or sha(idx_html) != idx['filing_index_sha256']:
            raise ValueError(f'Filing index bytes changed: {rec["accession"]}')
        listing = json.loads(idx_json)
        listed_names = {x['name'] for x in listing.get('directory', {}).get('item', []) if isinstance(x, dict) and 'name' in x}
        soup = BeautifulSoup(idx_html, 'html.parser')
        tables = [t for t in soup.find_all('table') if t.get('summary') == 'Document Format Files']
        if len(tables) != 1:
            raise ValueError(f'Missing document-format table: {rec["accession"]}')
        document_rows = []
        for tr in tables[0].find_all('tr'):
            cols = [td.get_text(' ', strip=True) for td in tr.find_all('td')]
            if len(cols) >= 5:
                document_rows.append(cols)
        primary_rows = [r for r in document_rows if r[2].split()[0] == rec['primary_filename']]
        if len(primary_rows) != 1:
            raise ValueError(f'Primary filename not unique in filing index: {rec["accession"]}')
        exhibit_rows = [r for r in document_rows if r[3].upper().startswith('EX-')]
        listed_size = int(primary_rows[0][-1].replace(',', ''))
        delta = len(raw) - listed_size
        trailing_script = bool(re.search(rb'<script\b[^>]+src="/[^"]+"[^>]*></script>\s*</body>', raw[-1024:], re.I))
        accession_in_index_body = rec['accession'].encode() in idx_html
        idx.pop('exhibit_like_files_count', None)
        idx.update({'primary_filename_in_document_format_table': True,
                    'accession_in_filing_index_body': accession_in_index_body,
                    'separately_listed_exhibit_count': len(exhibit_rows),
                    'index_listed_primary_byte_size': listed_size,
                    'sec_response_minus_index_size_bytes': delta})
        rec['server_added_trailing_script_observed'] = trailing_script
        rec['original_sec_representation'] = rec.get('http_status') == 200 and rec.get('final_response_url') == rec['original_sec_url']
        rec['alternate_copy'] = False
        rec['archive_byte_equivalence'] = 'NOT_ESTABLISHED; SEC response is 109 bytes longer than filing-index size' if delta == 109 else 'NOT_ESTABLISHED'
        rec['identity_pass'] = bool(rec['original_sec_representation']
                                    and rec['boundary_checks']['primary_boundary_pass']
                                    and rec['primary_filename'] in listed_names
                                    and idx['form_matches'] and accession_in_index_body)
        rec['status'] = 'ORIGINAL_SEC_IDENTITY_PASS' if rec['identity_pass'] else 'SOURCE_ACQUIRED_IDENTITY_INCOMPLETE'
        rec['representation'] = 'OFFICIAL_SEC_SERVED_PRIMARY_HTML' if rec['identity_pass'] else 'UNVERIFIED_SEC_RESPONSE'
        rec['exhibits_boundary_note'] = f'{len(exhibit_rows)} exhibit files are listed separately in the SEC filing index; only the primary HTML response is included.'
    manifest['acquired_primary_html'] = sum(bool(r.get('file')) for r in manifest['sources'])
    manifest['identity_pass'] = sum(bool(r.get('identity_pass')) for r in manifest['sources'])
    manifest['source_boundary_note'] = 'Preserved bytes are SEC-served responses; all nine are 109 bytes longer than SEC index-listed sizes and contain a trailing server-added script. No rewriting or stripping was performed.'
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    manifest_path.write_bytes(manifest_bytes)
    missing = [r for r in manifest['sources'] if not r.get('identity_pass')]
    (directory / 'V7A_G3_MISSING_OR_UNVERIFIED_SOURCES.json').write_bytes((json.dumps(missing, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
    lines = ['# V7A G3 original SEC source acquisition', '',
             f'- Requested: 9; acquired: {manifest["acquired_primary_html"]}; accession/form/index identity PASS: {manifest["identity_pass"]}; missing or unverified: {len(missing)}.',
             '- Returned HTML bytes were preserved unchanged. Each SEC response is 109 bytes longer than the filing-index size and has a trailing SEC-served script; archival byte equivalence is not claimed.',
             '- The filing index lists separate exhibit documents. The package contains primary HTML and index evidence, not exhibit bodies or the complete submission text file.',
             '- No answer/gold annotation, question change, corpus/index change, retrieval run or model tuning.', '',
             '| Accession | Form | Status | Primary bytes | SHA-256 | Separate exhibits |',
             '|---|---|---|---:|---|---:|']
    for rec in manifest['sources']:
        lines.append(f"| {rec['accession']} | {rec['form']} | {rec['status']} | {rec.get('byte_size', '')} | {rec.get('sha256', '')} | {rec.get('filing_index_crosscheck', {}).get('separately_listed_exhibit_count', '')} |")
    lines += ['', 'The JSON manifest records exact requested/final URLs, UTC timestamps, HTTP metadata, file mapping, CIK, form, table/boundary checks and filing-index evidence.',
              'A primary HTML snapshot is not a substitute for a separately filed exhibit or the complete-submission text file.']
    (directory / 'V7A_G3_ACQUISITION_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    files = sorted(p for p in directory.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt')
    sums = ''.join(f'{sha(p.read_bytes())}  {p.relative_to(directory).as_posix()}\n' for p in files)
    (directory / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8', newline='\n')
    package = directory.with_suffix('.zip')
    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(directory.rglob('*')):
            if p.is_file():
                info = zipfile.ZipInfo(p.relative_to(directory).as_posix(), date_time=(2026, 11, 2, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, p.read_bytes())
    return {'requested': 9, 'acquired': manifest['acquired_primary_html'], 'identity_pass': manifest['identity_pass'],
            'manifest_sha256': sha(manifest_bytes), 'package': str(package), 'package_sha256': sha(package.read_bytes())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(finalize(args.directory), indent=2))
