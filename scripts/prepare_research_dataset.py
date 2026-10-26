"""Freeze mechanical exact-row diagnostics BEFORE ranking on new SEC sources.

Only previously acquired, owned research bytes are parsed. No network/owner
corpus/embeddings. Automatic literal-row labels are NOT human adjudication.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from app.financial_ingestion import PARSER_VERSION,CHUNKER_VERSION
from app.financial_ingestion.schemas import FilingMetadata,DatasetManifest,DocumentStatus
from app.financial_ingestion.pipeline import validate_metadata_identity
from app.financial_ingestion.html_parser import parse_sec_html,normalized_filing_text
from app.financial_ingestion.chunker import chunk_filing
from app.financial_index.lexical import LexicalIndex
from app.table_evidence.identity import canonical,digest
from scripts.autonomous_sec_probe import owned_root

METRICS=('net sales','net income','total assets','current liabilities','operating income','cash and cash equivalents')


def new_file(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data)


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--root',type=Path,required=True);cli.add_argument('--probe',type=Path,required=True);args=cli.parse_args()
    root=owned_root(args.root);probe=json.loads(args.probe.read_text(encoding='utf-8'));filings=[];entries=[];querysets={s:[] for s in ['dev','validation','heldout']};sources=[]
    for rec in probe['records']:
        if rec['status'] not in {'ACQUIRED_OFFICIAL_SOURCE','EXISTING_ISOLATED_BYTES_NOT_REPLACED'}:continue
        raw_path=(root/rec['relative_path']).resolve()
        if not raw_path.is_relative_to(root):raise ValueError('RESEARCH_PATH_ESCAPE')
        raw=raw_path.read_bytes()
        if sha256(raw).hexdigest()!=rec['source_sha256']:raise ValueError('ACQUIRED_BYTES_CHANGED')
        m=FilingMetadata.model_validate(rec['metadata']);validate_metadata_identity(m)
        m.raw_content_hash=rec['source_sha256'];m.chunker_version=CHUNKER_VERSION
        f=parse_sec_html(raw,m)
        m.normalized_content_hash=sha256(normalized_filing_text(f).encode()).hexdigest()
        m.document_status=DocumentStatus.PARTIAL_EXTRACTION if any(t.extraction_status=='PARTIAL_EXTRACTION' for t in f.tables) else DocumentStatus.READY
        chunks=chunk_filing(f);filings.append(f)
        structured=root/'frozen_v1'/'structured'/f'{m.cik}.json';chunkspath=root/'frozen_v1'/'chunks'/f'{m.cik}.jsonl'
        new_file(structured,f.model_dump_json().encode());new_file(chunkspath,('\n'.join(c.model_dump_json() for c in chunks)+'\n').encode())
        frozen={'filing_id':m.filing_id,'raw_path':str(raw_path),'structured_path':str(structured),'chunks_path':str(chunkspath),
            'raw_hash':m.raw_content_hash,'normalized_hash':m.normalized_content_hash,
            'structured_hash':sha256(structured.read_bytes()).hexdigest(),'chunks_hash':sha256(chunkspath.read_bytes()).hexdigest()}
        sources.append(frozen);entries.extend({'chunk':c.model_dump(mode='json'),'source':frozen} for c in chunks)
        for metric in METRICS:
            relevant=[c.chunk_id for c in chunks if c.kind=='table' and c.metadata.get('row_label','').casefold().strip(' :')==metric]
            if relevant:
                querysets[rec['partition']].append({'id':f'{m.cik}:{metric.replace(" ","_")}','question':f'CIK {int(m.cik)} {metric} 10-Q',
                    'cik':m.cik,'filing_id':m.filing_id,'category':'exact_literal_table_row','relevance':{cid:2 for cid in sorted(relevant)},
                    'evidence_groups':[sorted(relevant)],'judgment_method':'automatic exact source row label plus frozen source correspondence; no human adjudication'})
    if not filings:raise ValueError('NO_FRESH_OFFICIAL_SOURCE_BYTES')
    manifest=DatasetManifest(dataset_id='research-sec-v1',snapshot_version='autonomous-v1',created_at='2026-10-26',
        sources=[f.metadata.source_url for f in filings],filing_ids=[f.metadata.filing_id for f in filings],
        raw_hashes={f.metadata.filing_id:f.metadata.raw_content_hash for f in filings},normalized_hashes={f.metadata.filing_id:f.metadata.normalized_content_hash for f in filings},
        parser_version=PARSER_VERSION,chunker_version=CHUNKER_VERSION,ingestion_version=filings[0].metadata.ingestion_version,
        chunk_counts={f.metadata.filing_id:sum(e['chunk']['filing_id']==f.metadata.filing_id for e in entries) for f in filings},
        document_count=len(filings),index_generation='LEXICAL_ONLY_RESEARCH',partial_documents=[f.metadata.filing_id for f in filings if f.metadata.document_status=='PARTIAL_EXTRACTION'],reproduction_commands=['python -m scripts.prepare_research_dataset --root <owned-root> --probe <probe-v2>'])
    manifest.manifest_hash=manifest.content_hash()
    generation=digest({'manifest':manifest.manifest_hash,'lexical':'accepted-C-v1','vectors':None})
    for e in entries:e['source']['manifest_hash']=manifest.manifest_hash
    from app.financial_query.catalog import catalog_from_verified_metadata
    catalog=catalog_from_verified_metadata(manifest,filings,generation_id=generation)
    new_file(root/'frozen_v1'/'manifest.json',manifest.model_dump_json().encode())
    new_file(root/'frozen_v1'/'catalog.json',catalog.model_dump_json().encode())
    new_file(root/'frozen_v1'/'sources.json',canonical(sources).encode())
    query_hashes={}
    for split,queries in querysets.items():
        data=canonical(queries).encode();new_file(root/'frozen_v1'/f'{split}_queries.json',data);query_hashes[split]={'sha256':sha256(data).hexdigest(),'count':len(queries)}
    freeze={'schema_version':'topic3-fresh-exact-row-freeze/v1','manifest_hash':manifest.manifest_hash,'generation':generation,
        'source_groups':[{'cik':f.metadata.cik,'accession':f.metadata.accession_number,'url':f.metadata.source_url,'raw_hash':f.metadata.raw_content_hash} for f in filings],
        'query_files':query_hashes,'arms':['B','D','F','R','T','A','AT'],'candidate_limit':40,'rrf_k':60,'top_k':[5,10],
        'row_weight':.05,'role_weight':.05,'exact_guardrail':.02,'overall_recall_guardrail':.02,'required_ndcg_improvement':0,
        'required_paraphrase_recall_gain':.05,'p95_ratio_to_F_max':1.5,'selected_finalist':None,
        'eligibility':'EXPLORATORY_LITERAL_ROW_DIAGNOSTIC_ONLY','human_annotators':0,
        'limitations':['Reduced3 issuer/3 document exact-label diagnostic; not144 questions/12 categories.','JPM excluded by fixed4MB source budget before ranking.',
            'No broad semantic or financial-value ground truth; no human adjudication.','All real sources exceed D2 context cap; Dense unavailable at preflight.',
            'No eligible adaptive finalist without required baselines/categories.','Heldout queries must not be scored before D5.']}
    new_file(root/'frozen_v1'/'freeze.json',canonical(freeze).encode())
    # Freeze exists before the new lexical index is built or any ranking runs.
    index=LexicalIndex(root/'lexical_v1.sqlite3');index.start(manifest.dataset_id,generation,{'sources':[{'manifest':manifest.model_dump(mode='json')}],'research_only':True})
    index.add(generation,entries);index.seal(generation);index.publish(manifest.dataset_id,generation)
    print(json.dumps(freeze,indent=2))


if __name__=='__main__':main()
