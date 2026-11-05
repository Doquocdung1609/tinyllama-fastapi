"""Audit or recover pinned SEC47 source bytes in a product-only directory."""
import argparse
import csv
from datetime import datetime, timezone
from hashlib import file_digest, sha256
import io
import json
import os
from pathlib import Path
import re
import subprocess
from time import sleep
from uuid import uuid4
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = '4677339ac4da5a62685212cac718223fe30582ae'


def read_git(path):
    return subprocess.check_output(['git', 'show', f'{CHECKPOINT}:{path}'], cwd=ROOT)


def manifest():
    raw = read_git('docs/topic3_v7a_g3/V7A_G3S_SEC47_RAW_SOURCE_MANIFEST.json')
    manifest = json.loads(raw)
    registry = read_git('docs/topic3_v7a_g2/V7A_SEC47_PRIVATE_SOURCE_MANIFEST.csv')
    if sha256(registry).hexdigest() != manifest['frozen_g2_manifest_sha256']:
        raise ValueError('FROZEN_MANIFEST_HASH_MISMATCH')
    frozen = {row['accession_number']: row for row in csv.DictReader(io.StringIO(registry.decode('utf-8-sig')))}
    if len(manifest['sources']) != 47 or {s['accession'] for s in manifest['sources']} != set(frozen):
        raise ValueError('FROZEN_MANIFEST_MEMBERSHIP_MISMATCH')
    for row in manifest['sources']:
        ref = frozen[row['accession']]
        if any(row[a] != ref[b] for a, b in [('cik','cik'), ('ticker','ticker'), ('form','form_type'),
                                             ('report_date','report_date'), ('source_url','source_url')]):
            raise ValueError('FROZEN_SOURCE_IDENTITY_MISMATCH')
        row['filing_date'] = ref['filing_date']
    return manifest, sha256(raw).hexdigest()


def hash_file(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def mapped(values):
    return {key: Path(path) for key, path in (value.split('=', 1) for value in values)}


def scan(roots, manifest, archive_map, source_map):
    packages = manifest['source_packages']
    sources = manifest['sources']
    by_size = {}
    for row in sources:
        by_size.setdefault(row['byte_size'], {})[row['sha256']] = row['accession']
    found, mismatches, conflicts = {}, set(), set()

    def local(path, size):
        if size in by_size:
            accession = by_size[size].get(hash_file(path))
            if accession:
                found.setdefault(accession, (path, None))
                return
        for row in sources:
            if path.name == Path(row['source_url']).name or row['accession'] in path.name:
                mismatches.add(row['accession'])

    def archive(path, declared=None):
        try:
            with zipfile.ZipFile(path) as bundle:
                names = {info.filename: info for info in bundle.infolist()}
                if declared and hash_file(path) != packages[declared]['sha256']:
                    conflicts.add(declared)
                    return
                files_by_size = {}
                for info in names.values():
                    if not info.is_dir() and info.file_size in by_size:
                        files_by_size.setdefault(info.file_size,[]).append(info)
                for row in sources:
                    info = names.get(row['source_zip_member'])
                    if info and info.file_size == row['byte_size'] and sha256(bundle.read(info)).hexdigest() == row['sha256']:
                        found.setdefault(row['accession'], (path, info.filename))
                    else:
                        if info:
                            mismatches.add(row['accession'])
                        for candidate in files_by_size.get(row['byte_size'],[]):
                            if candidate!=info and sha256(bundle.read(candidate)).hexdigest()==row['sha256']:
                                found.setdefault(row['accession'],(path,candidate.filename))
                                break
        except (OSError, zipfile.BadZipFile, RuntimeError):
            if declared:
                conflicts.add(declared)

    for name, package in packages.items():
        path = archive_map.get(name, Path(package['path']))
        if path.is_file():
            archive(path, name)
    for accession, path in source_map.items():
        if path.is_file():
            local(path, path.stat().st_size)
            if accession not in found:
                mismatches.add(accession)
    ignored = {'.git','.venv','venv','node_modules','site-packages','.gradle','__pycache__',
               'vectors','qdrant','bin','obj','.cache','dist','build'}
    pending = list(roots)
    visited = set()
    while pending:
        folder = pending.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.is_symlink() or getattr(entry, 'is_junction', lambda: False)():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name.casefold() not in ignored:
                            pending.append(entry.path)
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    path = Path(entry.path)
                    if path in visited:
                        continue
                    if path.suffix.lower()=='.zip':
                        visited.add(path)
                        archive(path)
                    else:
                        size = entry.stat(follow_symlinks=False).st_size
                        if size in by_size or path.suffix.lower() in {'.htm','.html','.xhtml'}:
                            local(path, size)
        except OSError:
            continue
    return found, mismatches, conflicts


def atomic_json(path, data):
    temp = path.with_name(f'{path.name}.{uuid4().hex}.tmp')
    try:
        temp.write_text(json.dumps(data, indent=2), encoding='utf-8')
        for attempt in range(5):
            try:
                temp.replace(path)
                return
            except PermissionError:
                if attempt==4:
                    raise
                sleep(.1*(attempt+1))
    finally:
        temp.unlink(missing_ok=True)


def filing_metadata(row):
    from app.financial_ingestion import PARSER_VERSION, INGESTION_VERSION
    from app.financial_ingestion.schemas import FilingMetadata
    return FilingMetadata(filing_id=f"sec:{row['cik']}:{row['accession']}",
        parser_version=PARSER_VERSION, ingestion_version=INGESTION_VERSION,
        cik=row['cik'], ticker=row['ticker'], company_name=row['ticker'],
        accession_number=row['accession'], form_type=row['form'], filing_date=row['filing_date'],
        report_date=row['report_date'], primary_document=Path(row['source_url']).name,
        source_url=row['source_url'])


def install(row, recovered_root):
    """Stage verified bytes for the existing serialized product worker."""
    from app.product.sec_library import db, paths, process, root, rows, update
    from app.product.sec_import_identity import validate
    from app.financial_ingestion.pipeline import validate_metadata_identity
    import portalocker
    import time

    m = filing_metadata(row)
    key = sha256(m.filing_id.encode()).hexdigest()[:24]
    present = next((r for r in rows() if r['id']==key), None)
    if present and (present['status']=='READY' or present['status']=='LEXICAL_READY'
                    and os.getenv('STUDIO_SEC_IMPORT_LEXICAL_ONLY')=='1'):
        return {'product_status':present['status'],'product_reason':present['reason'],'library_id':key}
    source = paths(key)[0]
    with (root()/'import-worker.lock').open('a+') as stream:
        try:
            portalocker.lock(stream,portalocker.LOCK_EX|portalocker.LOCK_NB)
        except portalocker.LockException:
            return {'product_status':'BLOCKED','product_reason':'SEC_IMPORT_BUSY'}
        try:
            if any(r['status'] in {'DOWNLOADING','EXTRACTING','INDEXING'} for r in rows()):
                return {'product_status':'BLOCKED','product_reason':'SEC_IMPORT_BUSY'}
            if row['local_status']=='LOCAL_ORIGINAL_VERIFIED':
                if row.get('zip_member'):
                    with zipfile.ZipFile(row['local_file']) as archive:
                        raw = archive.read(row['zip_member'])
                else:
                    raw = Path(row['local_file']).read_bytes()
                expected = row['sha256']
            elif row['recovery'] in {'ORIGINAL_SOURCE_RECOVERED','OFFICIAL_SOURCE_HASH_DRIFT'}:
                raw = (recovered_root/'raw'/row['accession']/m.primary_document).read_bytes()
                expected = row['actual_sha256']
            else:
                return {'product_status':'MANIFEST_ONLY'}
            if sha256(raw).hexdigest()!=expected:
                return {'product_status':'FAILED','product_reason':'SOURCE_CHANGED_AFTER_AUDIT'}
            validate_metadata_identity(m,additional_forms={'20-F','6-K'})
            try:
                identity=validate(raw,m)
                m.company_name=identity['company_name'] or m.company_name
                m.fiscal_year=identity['fiscal_year']
                m.fiscal_period=identity['fiscal_period']
            except ValueError as exc:
                return {'product_status':'PARTIAL','product_reason':str(exc)[:120]}
            if m.form_type=='6-K':
                return {'product_status':'PARTIAL','product_reason':'EXHIBIT_REVIEW_REQUIRED'}
            source.mkdir(parents=True,exist_ok=True)
            ownership = source/'ownership.json'
            marker = {'owner':'FIS_USER_SEC_LIBRARY_V1','id':key}
            if ownership.is_file():
                if json.loads(ownership.read_text(encoding='utf-8'))!=marker:
                    raise ValueError('UNOWNED_PRODUCT_ROOT')
            elif any(source.iterdir()):
                raise ValueError('NONEMPTY_UNOWNED_PRODUCT_ROOT')
            else:
                atomic_json(ownership,marker)
            target = source/'raw'/m.cik/m.accession_number/m.primary_document
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and hash_file(target)!=expected:
                return {'product_status':'FAILED','product_reason':'EXISTING_PRODUCT_SOURCE_CONFLICT'}
            if not target.exists():
                temp = target.with_suffix('.part')
                temp.write_bytes(raw)
                temp.replace(target)
            atomic_json(source/'acquisition.json',{'source_url':m.source_url,'raw_sha256':expected,
                'frozen_raw_sha256':row['sha256'],'recovery_class':row['recovery'],
                'retrieved_at':row.get('retrieved_at')})
            with db() as connection:
                connection.execute('INSERT OR IGNORE INTO filings VALUES (?,?,?,NULL,?)',
                                   (key,m.model_dump_json(),'DISCOVERED',time.time()))
            update(key,'DOWNLOADING')
        finally:
            portalocker.unlock(stream)
    process(key)
    result = next(r for r in rows() if r['id']==key)
    return {'product_status':result['status'],'product_reason':result['reason'],'library_id':key}


def recover(row, output, sec):
    from app.financial_ingestion.sec_client import SECRequestError
    from app.product.sec_import_identity import validate
    from app.financial_ingestion.pipeline import validate_metadata_identity

    folder = output / 'raw' / row['accession']
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / Path(row['source_url']).name
    receipt = folder / 'receipt.json'
    if receipt.is_file() and target.is_file():
        cached = json.loads(receipt.read_text(encoding='utf-8'))
        if cached.get('recovery') in {'ORIGINAL_SOURCE_RECOVERED','OFFICIAL_SOURCE_HASH_DRIFT'} and cached['source_url']==row['source_url'] and cached['actual_sha256']==hash_file(target):
            return cached
    try:
        response = sec.download(row['source_url'], target, max_bytes=max(16_000_000, row['byte_size'] * 2))
    except SECRequestError as exc:
        return {'recovery':'FETCH_FAILED', 'reason':f'SEC_HTTP_{exc.status_code}' if exc.status_code else type(exc).__name__}
    raw = target.read_bytes()
    actual = sha256(raw).hexdigest()
    record = {'source_url':row['source_url'], 'accession':row['accession'], 'cik':row['cik'], 'form':row['form'],
              'http_status':response.status_code, 'content_type':response.content_type,
              'retrieved_at':datetime.now(timezone.utc).isoformat(), 'actual_sha256':actual, 'actual_bytes':len(raw)}
    try:
        if response.final_url != row['source_url'] or not re.search(r'(?:text/html|application/xhtml\+xml)', response.content_type or ''):
            raise ValueError('SEC_RESPONSE_IDENTITY_CONFLICT')
        if b'<html' not in raw[:8192].lower() or b'</html>' not in raw[-8192:].lower():
            raise ValueError('SEC_HTML_BOUNDARIES_MISSING')
        exact = actual == row['sha256'] and len(raw) == row['byte_size']
        if not exact:
            metadata = filing_metadata(row)
            validate_metadata_identity(metadata,additional_forms={'20-F','6-K'})
            validate(raw, metadata)
        record['recovery'] = 'ORIGINAL_SOURCE_RECOVERED' if exact else 'OFFICIAL_SOURCE_HASH_DRIFT'
    except ValueError as exc:
        record.update(recovery='IDENTITY_CONFLICT', reason=str(exc).splitlines()[0][:120])
    atomic_json(receipt, record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--search-root', action='append', type=Path, default=[])
    parser.add_argument('--archive-map', action='append', default=[], metavar='PACKAGE=PATH')
    parser.add_argument('--source-map', action='append', default=[], metavar='ACCESSION=PATH')
    parser.add_argument('--out', type=Path, default=ROOT/'tmp/studio-runtime/sec47-v4')
    parser.add_argument('--install',action='store_true',help='Index audited source bytes using the product worker')
    parser.add_argument('--lexical-only',action='store_true',help='Publish BM25 first and leave Dense pending')
    parser.add_argument('--ticker',action='append',default=[],help='Prioritize installation for selected tickers')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Report local availability without network access')
    mode.add_argument('--verify-only', action='store_true', help='Verify only local sources and write the audit')
    mode.add_argument('--recover', action='store_true', help='Download missing pinned SEC primary documents')
    args = parser.parse_args()
    if args.lexical_only:
        os.environ['STUDIO_SEC_IMPORT_LEXICAL_ONLY']='1'
    if args.install and (args.verify_only or args.dry_run):
        parser.error('--install cannot be used with read-only audit modes')
    data, manifest_hash = manifest()
    found, mismatches, conflicts = scan(args.search_root, data, mapped(args.archive_map), mapped(args.source_map))
    args.out.mkdir(parents=True, exist_ok=True)
    sec = None
    if args.recover:
        from app.product.sec_library import client
        sec = client()
    records = []
    try:
        for source in data['sources']:
            accession = source['accession']
            row = {**source, 'local_status':'SOURCE_MISSING', 'recovery':'NOT_ATTEMPTED'}
            if accession in found:
                path, member = found[accession]
                row.update(local_status='LOCAL_ORIGINAL_VERIFIED', local_file=str(path), zip_member=member)
            elif accession in mismatches:
                row['local_status'] = 'LOCAL_SOURCE_HASH_MISMATCH'
            elif source['origin_package'] in conflicts:
                row['local_status'] = 'PACKAGE_HASH_CONFLICT'
            if sec and accession not in found:
                row.update(recover(row, args.out, sec))
            records.append(row)
            print(accession, row['local_status'], row['recovery'], flush=True)
            atomic_json(args.out/'SEC47_AUDIT.json', {'checkpoint':CHECKPOINT, 'manifest_sha256':manifest_hash, 'records':records})
    finally:
        if sec:
            sec.session.close()
    if args.recover or args.install:
        from app.product.sec_library import root
        public = [{k:v for k,v in r.items() if k not in {'local_file','zip_member','source_zip_member'}} for r in records]
        atomic_json(root()/'sec47-status.json',public)
    if args.install:
        for row in sorted(records,key=lambda r:(r['form'] not in {'10-K','20-F'},r['ticker'],r['report_date']),reverse=False):
            if args.ticker and row['ticker'] not in args.ticker:
                continue
            try:
                row.update(install(row,args.out))
            except (ValueError,OSError) as exc:
                row.update(product_status='FAILED',product_reason=type(exc).__name__)
            print(row['accession'],row.get('product_status'),row.get('product_reason'),flush=True)
            atomic_json(args.out/'SEC47_AUDIT.json',{'checkpoint':CHECKPOINT,'manifest_sha256':manifest_hash,'records':records})
            public = [{k:v for k,v in r.items() if k not in {'local_file','zip_member','source_zip_member'}} for r in records]
            atomic_json(root()/'sec47-status.json',public)
    columns = sorted({key for row in records for key in row})
    with (args.out/'SEC47_AUDIT.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)


if __name__ == '__main__':
    main()
