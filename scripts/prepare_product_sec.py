"""Explicit owner-authorized PG/HD product setup, no qrels/evaluation campaign.

Uses the existing parser, chunks, lexical index, frozen snapshot, authenticated
cell verifier and isolated dense builder. Never overwrites accepted generations.
Run only when SEC acquisition is explicitly authorized and contact UA configured.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import get_settings
from app.financial_ingestion.sec_client import SECClient
from app.financial_ingestion.pipeline import validate_metadata_identity
from app.financial_ingestion.schemas import FilingMetadata,DatasetManifest,DocumentStatus
from app.financial_ingestion.html_parser import parse_sec_html,normalized_filing_text
from app.financial_ingestion.chunker import chunk_filing
from app.financial_ingestion import PARSER_VERSION,CHUNKER_VERSION
from app.financial_index.lexical import LexicalIndex
from app.financial_query.catalog import catalog_from_verified_metadata
from app.table_evidence.identity import digest
from scripts.autonomous_sec_probe import owned_root


def prepare(root):
    root=owned_root(root)
    repo=Path(__file__).resolve().parents[1]
    plan=json.loads((repo/'docs/topic3/milestone_d/d3/D3_PUBLIC_SOURCE_PROBE_v2.json').read_text('utf-8'))
    registry_path=repo/'docs/topic3/final_product/SEC_PRODUCT_SOURCE_REGISTRY.json'
    freeze_path=root/'frozen_v1/freeze.json'
    if freeze_path.exists():
        freeze=json.loads(freeze_path.read_text('utf-8'))
        assert registry_path.exists() and json.loads(registry_path.read_text('utf-8'))['generation']==freeze['generation']
        return freeze
    settings=get_settings();client=SECClient(settings.sec_user_agent,requests_per_second=1,timeout_seconds=30,max_retries=0)
    entries=[];filings=[];sources=[]
    try:
        for old in plan['records']:
            if old['ticker'] not in {'PG','HD'}:continue
            metadata=FilingMetadata.model_validate(old['metadata'])
            validate_metadata_identity(metadata)
            raw_path=root/'raw'/metadata.cik/metadata.accession_number/metadata.primary_document
            if not raw_path.exists():client.download(metadata.source_url,raw_path,max_bytes=4_000_000)
            raw=raw_path.read_bytes();metadata.raw_content_hash=sha256(raw).hexdigest()
            metadata.parser_version=PARSER_VERSION;metadata.chunker_version=CHUNKER_VERSION
            filing=parse_sec_html(raw,metadata)
            metadata.normalized_content_hash=sha256(normalized_filing_text(filing).encode()).hexdigest()
            metadata.document_status=DocumentStatus.PARTIAL_EXTRACTION if any(t.extraction_status=='PARTIAL_EXTRACTION' for t in filing.tables) else DocumentStatus.READY
            chunks=chunk_filing(filing);filings.append(filing)
            structured=root/'frozen_v1/structured'/f'{metadata.cik}.json';chunk_file=root/'frozen_v1/chunks'/f'{metadata.cik}.jsonl'
            for path,data in [(structured,filing.model_dump_json().encode()),(chunk_file,('\n'.join(c.model_dump_json() for c in chunks)+'\n').encode())]:
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as stream:stream.write(data)
            frozen={'filing_id':metadata.filing_id,'raw_path':str(raw_path),'structured_path':str(structured),'chunks_path':str(chunk_file),
                'raw_hash':metadata.raw_content_hash,'normalized_hash':metadata.normalized_content_hash,
                'structured_hash':sha256(structured.read_bytes()).hexdigest(),'chunks_hash':sha256(chunk_file.read_bytes()).hexdigest()}
            sources.append(frozen);entries.extend({'chunk':c.model_dump(mode='json'),'source':frozen} for c in chunks)
            print(metadata.ticker,len(chunks),metadata.raw_content_hash,flush=True)
    finally:client.session.close()
    manifest=DatasetManifest(dataset_id='product-pg-hd-20261028',snapshot_version='product-v1',created_at='2026-10-28',
        sources=[f.metadata.source_url for f in filings],filing_ids=[f.metadata.filing_id for f in filings],
        raw_hashes={f.metadata.filing_id:f.metadata.raw_content_hash for f in filings},normalized_hashes={f.metadata.filing_id:f.metadata.normalized_content_hash for f in filings},
        parser_version=PARSER_VERSION,chunker_version=CHUNKER_VERSION,ingestion_version=filings[0].metadata.ingestion_version,
        chunk_counts={f.metadata.filing_id:sum(e['chunk']['filing_id']==f.metadata.filing_id for e in entries) for f in filings},
        document_count=len(filings),index_generation='LEXICAL_ONLY_RESEARCH',partial_documents=[f.metadata.filing_id for f in filings if f.metadata.document_status=='PARTIAL_EXTRACTION'],
        reproduction_commands=['python scripts/prepare_product_sec.py --root <new-owned-root>'])
    manifest.manifest_hash=manifest.content_hash();generation=digest({'manifest':manifest.manifest_hash,'lexical':'accepted-C-v1','vectors':None})
    for entry in entries:entry['source']['manifest_hash']=manifest.manifest_hash
    catalog=catalog_from_verified_metadata(manifest,filings,generation_id=generation)
    freeze={'schema':'product-official-sec-source-registry/v1','manifest_hash':manifest.manifest_hash,'generation':generation,
        'source_groups':[{'cik':f.metadata.cik,'accession':f.metadata.accession_number,'url':f.metadata.source_url,'raw_hash':f.metadata.raw_content_hash} for f in filings],
        'purpose':'Owner-authorized product acceptance sources. Fresh SEC bytes; not the old P10/P11 research snapshot; no evaluation qrels.'}
    for name,data in [('manifest.json',manifest.model_dump(mode='json')),('catalog.json',catalog.model_dump(mode='json')),('sources.json',sources),('freeze.json',freeze)]:
        with (root/'frozen_v1'/name).open('x',encoding='utf-8') as stream:json.dump(data,stream,ensure_ascii=False,sort_keys=True)
    if registry_path.exists() and json.loads(registry_path.read_text('utf-8'))!=freeze:raise ValueError('EXISTING_COMMITTED_PRODUCT_REGISTRY_DIFFERENT')
    registry_path.write_text(json.dumps(freeze,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lexical=LexicalIndex(root/'lexical_v1.sqlite3');lexical.start(manifest.dataset_id,generation,{'sources':[{'manifest':manifest.model_dump(mode='json')}],'product_only':True})
    lexical.add(generation,entries);lexical.seal(generation);lexical.publish(manifest.dataset_id,generation)
    return freeze


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.root),indent=2))
