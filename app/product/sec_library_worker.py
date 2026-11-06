"""Isolated product SEC acquisition/parser/index worker; never opens research labels."""
from hashlib import sha256
from pathlib import Path
import json,os,sys
from contextlib import closing
from uuid import uuid4
from app.product.sec_library import rows,paths,update,client

def isolate_interrupted_lexical(root, vectors, lexical, generation, chunks):
    """Preserve an unpublished index whose metadata predates this generation."""
    from app.financial_index.lexical import LexicalIndex
    if (root/'lexical-publication.json').exists():
        return lexical
    manifest=vectors/'generation_manifest.json'
    if manifest.is_file() and json.loads(manifest.read_bytes()).get('state')=='READY':
        return lexical
    with closing(lexical.connect()) as connection:
        old=connection.execute('SELECT generation FROM active').fetchone()
    if old is None:
        return lexical
    if old[0]==generation:
        expected={chunk.chunk_id:chunk.model_dump(mode='json') for chunk in chunks}
        if all(expected.get(record['chunk']['chunk_id'])==record['chunk'] for record in lexical.records(generation)):
            return lexical
    root=root.resolve(strict=True)
    archive=root/('interrupted-lexical-'+uuid4().hex)
    archive.mkdir()
    for name in ('lexical_v1.sqlite3','lexical_v1.sqlite3-wal','lexical_v1.sqlite3-shm'):
        path=root/name
        if path.is_file():
            if path.resolve().parent!=root:
                raise ValueError('PRODUCT_SOURCE_PATH_ESCAPE')
            path.replace(archive/name)
    return LexicalIndex(root/'lexical_v1.sqlite3')


def publish_dense(key, root, vectors):
    if os.getenv('STUDIO_SEC_IMPORT_LEXICAL_ONLY')=='1':
        update(key,'LEXICAL_READY','DENSE_PENDING')
        return
    from scripts.p10_build_isolated_vectors import build
    from app.product.sec_product_snapshot import ProductSecSnapshot
    update(key,'LEXICAL_READY','BUILDING_DENSE')
    result=build(root,vectors,4,None,snapshot_factory=ProductSecSnapshot)
    if result['state']!='READY':raise ValueError('VECTOR_GENERATION_INCOMPLETE')
    update(key,'READY')


def run(key):
    from app.financial_ingestion import PARSER_VERSION,CHUNKER_VERSION
    from app.financial_ingestion.schemas import FilingMetadata,DatasetManifest
    from app.financial_ingestion.html_parser import parse_sec_html,normalized_filing_text
    from app.financial_ingestion.chunker import chunk_filing
    from app.financial_ingestion.pipeline import validate_metadata_identity
    from app.financial_index.lexical import LexicalIndex
    from app.financial_query.catalog import catalog_from_verified_metadata
    from app.table_evidence.identity import digest
    from scripts.p10_build_isolated_vectors import atomic_json
    row=next(r for r in rows() if r['id']==key);m=FilingMetadata.model_validate_json(row['metadata'])
    validate_metadata_identity(m,additional_forms={'20-F','6-K'});root,vectors=paths(key);root.mkdir(parents=True,exist_ok=True)
    marker=root/'ownership.json'
    if not marker.exists():
        if any(root.iterdir()):raise ValueError('NONEMPTY_UNOWNED_PRODUCT_ROOT')
        marker.write_text(json.dumps({'owner':'FIS_USER_SEC_LIBRARY_V1','id':key}),encoding='utf-8')
    if json.loads(marker.read_text(encoding='utf-8'))!={'owner':'FIS_USER_SEC_LIBRARY_V1','id':key}:raise ValueError('UNOWNED_PRODUCT_ROOT')
    if (root/'lexical-publication.json').is_file():
        from app.product.sec_search import SecResearchIndex
        published=SecResearchIndex(root,vectors,root,lexical_only=True)
        try:
            if not any(f['filing_id']==m.filing_id for f in published.catalog_rows):
                raise ValueError('PUBLISHED_FILING_IDENTITY_MISMATCH')
        finally:
            published.close()
        return publish_dense(key,root,vectors)
    raw_path=root/'raw'/m.cik/m.accession_number/m.primary_document
    acquisition=root/'acquisition.json'
    sec=client()
    try:
        if not raw_path.exists():
            response=sec.download(m.source_url,raw_path,max_bytes=16_000_000)
            if response.final_url!=m.source_url or not any(t in (response.content_type or '') for t in ('text/html','application/xhtml+xml')):raise ValueError('SEC_RESPONSE_IDENTITY_REQUIRES_REVIEW')
            atomic_json(acquisition,{'source_url':m.source_url,'raw_sha256':sha256(raw_path.read_bytes()).hexdigest(),
                'retrieved_at':response.retrieved_at,'response':response.response_metadata()})
        elif not acquisition.exists():
            # A legacy cache is authenticated against fresh official bytes, never
            # silently adopted as an official acquisition solely because it exists.
            check=raw_path.with_suffix(raw_path.suffix+'.verify')
            try:
                response=sec.download(m.source_url,check,max_bytes=16_000_000)
                if response.final_url!=m.source_url or sha256(check.read_bytes()).digest()!=sha256(raw_path.read_bytes()).digest():raise ValueError('OFFICIAL_SOURCE_CHANGED_REVIEW_REQUIRED')
                atomic_json(acquisition,{'source_url':m.source_url,'raw_sha256':sha256(raw_path.read_bytes()).hexdigest(),
                    'retrieved_at':response.retrieved_at,'response':response.response_metadata()})
            finally:check.unlink(missing_ok=True)
        receipt=json.loads(acquisition.read_text(encoding='utf-8'))
        if receipt['source_url']!=m.source_url or receipt['raw_sha256']!=sha256(raw_path.read_bytes()).hexdigest():raise ValueError('CACHED_SOURCE_HASH_CHANGED')
    finally:sec.session.close()
    raw=raw_path.read_bytes()
    from app.product.sec_import_identity import validate
    identity=validate(raw,m)
    if m.form_type=='6-K':raise ValueError('EXHIBIT_REVIEW_REQUIRED')
    update(key,'SOURCE_VERIFIED')
    update(key,'EXTRACTING')
    m.company_name=identity['company_name'] or m.company_name
    m.fiscal_year=identity['fiscal_year'] or m.fiscal_year
    m.fiscal_period=identity['fiscal_period'] or m.fiscal_period
    m.raw_content_hash=sha256(raw).hexdigest();m.parser_version=PARSER_VERSION;m.chunker_version=CHUNKER_VERSION
    filing=parse_sec_html(raw,m);m.normalized_content_hash=sha256(normalized_filing_text(filing).encode()).hexdigest()
    chunks=chunk_filing(filing)
    if not chunks:raise ValueError('NO_EXTRACTED_SOURCE_CHUNKS')
    frozen=root/'frozen_v1';frozen.mkdir(exist_ok=True)
    structured=frozen/'structured.json';chunk_file=frozen/'chunks.jsonl'
    structured.write_text(filing.model_dump_json(),encoding='utf-8');chunk_file.write_text('\n'.join(c.model_dump_json() for c in chunks)+'\n',encoding='utf-8')
    previous_manifest=frozen/'manifest.json'
    created_at=json.loads(previous_manifest.read_text(encoding='utf-8'))['created_at'] if previous_manifest.exists() else __import__('datetime').date.today().isoformat()
    manifest=DatasetManifest(dataset_id='user-sec-'+key,snapshot_version='product-v1',created_at=created_at,
        sources=[m.source_url],filing_ids=[m.filing_id],raw_hashes={m.filing_id:m.raw_content_hash},normalized_hashes={m.filing_id:m.normalized_content_hash},
        parser_version=PARSER_VERSION,chunker_version=CHUNKER_VERSION,ingestion_version=m.ingestion_version,chunk_counts={m.filing_id:len(chunks)},
        document_count=1,index_generation='PRODUCT_SEC_LIBRARY',reproduction_commands=['python -m app.product.sec_library_worker '+key],partial_documents=[m.filing_id] if any(t.extraction_status=='PARTIAL_EXTRACTION' for t in filing.tables) else [])
    manifest.manifest_hash=manifest.content_hash();generation=digest({'manifest':manifest.manifest_hash,'lexical':'accepted-C-v1','vectors':None})
    source={'filing_id':m.filing_id,'raw_path':str(raw_path.resolve()),'structured_path':str(structured.resolve()),'chunks_path':str(chunk_file.resolve()),
        'raw_hash':m.raw_content_hash,'normalized_hash':m.normalized_content_hash,'structured_hash':sha256(structured.read_bytes()).hexdigest(),
        'chunks_hash':sha256(chunk_file.read_bytes()).hexdigest(),'manifest_hash':manifest.manifest_hash}
    from app.product.sec_product_snapshot import ProductCatalogFiling,ProductCorpusCatalog
    catalog=catalog_from_verified_metadata(manifest,[filing],generation_id=generation,
        filing_model=ProductCatalogFiling,catalog_model=ProductCorpusCatalog,omit_overlong_labels=True)
    for name,data in [('manifest.json',manifest.model_dump(mode='json')),('catalog.json',catalog.model_dump(mode='json')),('sources.json',[source]),
        ('freeze.json',{'generation':generation,'manifest_hash':manifest.manifest_hash,'purpose':'PRODUCT_USER_LIBRARY_SOURCE_ONLY',
            'source_groups':[{'cik':m.cik,'accession':m.accession_number,'url':m.source_url,'raw_hash':m.raw_content_hash}]})]:
        (frozen/name).write_text(json.dumps(data,ensure_ascii=False,sort_keys=True),encoding='utf-8')
    atomic_json(root/'extraction-progress.json',{'source_bytes':len(raw),'tables':len(filing.tables),
                                                 'extracted_chunks':len(chunks)})
    update(key,'EXTRACTED')
    update(key,'BUILDING_LEXICAL')
    lexical=LexicalIndex(root/'lexical_v1.sqlite3')
    lexical=isolate_interrupted_lexical(root,vectors,lexical,generation,chunks)
    lexical.start(manifest.dataset_id,generation,{'product_only':True})
    lexical.add(generation,[{'chunk':c.model_dump(mode='json'),'source':source} for c in chunks]);lexical.seal(generation);lexical.publish(manifest.dataset_id,generation)
    atomic_json(root/'lexical-publication.json',{'state':'LEXICAL_READY','dataset_id':manifest.dataset_id,
        'generation':generation,'manifest_hash':manifest.manifest_hash,'parent_count':len(chunks),'completed_points':0})
    update(key,'LEXICAL_READY','DENSE_PENDING')
    return publish_dense(key,root,vectors)

if __name__=='__main__':
    key=sys.argv[1]
    try:
        import portalocker
        from app.product.sec_library import root
        with (root()/'import-worker.lock').open('a+') as stream:
            portalocker.lock(stream,portalocker.LOCK_EX)
            try:run(key)
            finally:portalocker.unlock(stream)
    except Exception as e:
        # Store bounded codes, never contacts, URLs with secrets, or tracebacks.
        from app.financial_ingestion.sec_client import SECRequestError
        reason='SOURCE_BYTES_BUDGET_EXCEEDED' if isinstance(e,SECRequestError) and 'byte limit' in str(e) else 'SEC_HTTP_'+str(e.status_code) if isinstance(e,SECRequestError) and e.status_code else str(e) if isinstance(e,ValueError) and str(e).replace('_','').isalnum() else type(e).__name__
        root_path=paths(key)[0]
        state='LEXICAL_READY' if (root_path/'lexical-publication.json').is_file() else 'RETRYABLE'
        update(key,state,reason[:120])
