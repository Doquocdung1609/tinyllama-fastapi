"""Research-only D1→D3→D2→D4 coordinator and explicitly synthetic demo."""
from hashlib import sha256
import json
from pathlib import Path
from app.financial_ingestion import PARSER_VERSION,CHUNKER_VERSION,INGESTION_VERSION
from app.financial_ingestion.schemas import FilingMetadata,FinancialChunk
from app.financial_ingestion.html_parser import parse_sec_html,normalized_filing_text
from app.financial_ingestion.chunker import chunk_filing
from app.financial_index.lexical import LexicalIndex
from app.financial_query.contracts import CorpusCatalogV1,ScopeResolutionResultV1
from app.research_retrieval import retrieve_financial_query
from app.research_retrieval.adapters import OwnedLexicalAdapter
from app.research_retrieval.contracts import PolicyV1
from app.research_retrieval.snapshot import FrozenResearchSnapshot
from app.table_evidence import context_from_snapshot,build_table_evidence,build_evidence_bundle
from app.table_evidence.contracts import SourceBindingV1
from app.table_evidence.identity import digest
from app.research_qa.contracts import NumericRequestV1,AnswerResultV1
from app.research_qa.verifier import answer_from_bundle,verify_claim
from app.research_qa.numeric import period_key

OWNER='TOPIC3_AUTONOMOUS_D2_TO_D5_GATED_EXECUTION_AUTHORIZED'


class DemoAdapter(OwnedLexicalAdapter):
    def search(self,*args):
        hits=super().search(*args)
        from contextlib import closing
        with closing(self.lexical.connect()) as c:
            for h in hits:
                row=c.execute('SELECT payload,payload_hash FROM documents WHERE cid=?',(h.chunk_id,)).fetchone()
                if row is None or digest(json.loads(row['payload']))!=row['payload_hash'] or row['payload_hash']!=h.payload_hash:
                    raise ValueError('DEMO_PARENT_PAYLOAD_TAMPERED')
        return hits


class ResearchBackend:
    source_type='OFFICIAL_SEC_RESEARCH_DIAGNOSTIC'
    def __init__(self,root,snapshot_factory=FrozenResearchSnapshot):
        self.adapter=snapshot_factory(root);self.catalog=self.adapter.catalog;self.context=None
        self.p6_catalog=None

    def evidence_lookup(self,hit):return None

    def query(self,question,filters,arm='B',operation='EXTRACT',top_k=5,use_llm=False,workflow='research'):
        if workflow=='automatic_real':
            if self.context is not None:raise ValueError('AUTOMATIC_REAL_REQUIRES_OFFICIAL_SEC_SNAPSHOT')
            from app.research_qa.automatic_real import automatic_real_query
            if self.p6_catalog is None:
                from app.research_qa.source_alias import verified_alias_catalog
                with self.adapter.lock:
                    if self.p6_catalog is None:self.p6_catalog=verified_alias_catalog(self.adapter)
            return automatic_real_query(self.adapter,question,filters,operation,use_llm,arm,self.p6_catalog)
        if workflow!='research':raise ValueError('UNKNOWN_RESEARCH_WORKFLOW')
        r=retrieve_financial_query(question,filters,self.catalog,self.adapter,arm,policy=PolicyV1(top_k=top_k),evidence_lookup=self.evidence_lookup)
        def stop(status,reason):return AnswerResultV1(status=status,reasons=(reason,))
        citations=[]
        for hit in r.results:
            p=FinancialChunk.model_validate_json(hit.candidate.parent_json)
            citations.append({'parent_id':p.chunk_id,'payload_hash':hit.candidate.payload_hash,'filing_id':p.filing_id,
                'issuer':p.metadata.get('company_name'),'form':p.metadata.get('form_type'),'report_date':p.metadata.get('report_date'),
                'source_url':p.metadata.get('source_url'),'locator':p.source_location.model_dump(mode='json'),
                'row_label':p.metadata.get('row_label'),'extraction_status':p.extraction_status,'content':p.text[:3000]})
        if r.status!='OK':
            status={'NEEDS_CLARIFICATION':'NEEDS_CLARIFICATION','INVALID_INPUT':'INVALID_INPUT','UNSUPPORTED':'UNSUPPORTED_OPERATION'}.get(r.status,'INSUFFICIENT_EVIDENCE')
            answer=stop(status,r.failure_code or 'RETRIEVAL_SCOPE_'+r.status)
        elif use_llm:answer=stop('UNSUPPORTED_OPERATION','LLM_MODE_NOT_ENABLED_OR_VERIFIED')
        elif self.context is None:answer=stop('INSUFFICIENT_EVIDENCE','REAL_D2_SOURCE_CONTEXT_UNSUPPORTED_SIZE')
        else:
            resolution=ScopeResolutionResultV1.model_validate_json(r.scope_json);intent=resolution.query_intent
            expected_op={'RELATIVE_CHANGE':'PERCENT_CHANGE','PERCENTAGE_POINTS':'PERCENTAGE_POINTS','DIFFERENCE':'ABS_CHANGE'}.get(intent.comparison_operation)
            periods=resolution.resolved_scope.requested_periods
            metric_names={m.canonical.casefold() for m in intent.metric_mentions if m.relationship in {'EXACT','SYNONYM'}}
            if expected_op and expected_op!=operation:answer=stop('NEEDS_CLARIFICATION','QUESTION_OPERATION_FILTER_CONFLICT')
            elif len(metric_names)!=1:answer=stop('NEEDS_CLARIFICATION','SINGLE_EXACT_METRIC_REQUIRED')
            elif len(periods)!=(1 if operation=='EXTRACT' else 2):answer=stop('NEEDS_CLARIFICATION','EXPLICIT_OBSERVATION_PERIODS_REQUIRED')
            else:
                metric=next(iter(metric_names));wanted={(p.kind,p.year,p.quarter,str(p.end) if p.end else None,p.months) for p in periods}
                matches=[]
                basis=next((v for word,v in [('fair value','FAIR_VALUE'),('carrying','CARRYING_VALUE'),('basic','BASIC_EPS'),('diluted','DILUTED_EPS')] if word in intent.normalized_question),None)
                for hit in r.results:
                    e=self.evidence_lookup(hit.candidate)
                    if e is None or e.row_label.casefold()!=metric:continue
                    for c in e.cells:
                        if c.value is not None and c.period and period_key(c.period) in wanted and (not basis or c.measurement_basis==basis):matches.append((e,c))
                if len(matches)!=len(wanted):answer=stop('NEEDS_CLARIFICATION','AMBIGUOUS_OR_MISSING_SOURCE_CELL')
                else:
                    matches.sort(key=lambda pair:(pair[1].period.year or 0,pair[1].period.quarter or 0,pair[1].period.end or ''))
                    parents=[self.context.parent(cid) for cid in dict.fromkeys(e.parent_chunk_id for e,_ in matches)]
                    bundle=build_evidence_bundle(parents,self.context)
                    request=NumericRequestV1(operation=operation,metric=matches[0][0].row_label,
                        measurement_basis=basis,cell_ids=tuple(c.evidence_id for _,c in matches))
                    answer=answer_from_bundle(request,bundle,self.context)
                    if answer.status=='SUPPORTED' and not all(verify_claim(request,c,bundle,self.context) for c in answer.claims):
                        answer=stop('CONFLICTED_EVIDENCE','CLAIM_POSTVERIFICATION_FAILED')
        return {'interface_version':'financial-research-api/v1','source_type':self.source_type,'retrieval_status':r.status,
            'effective_mode':r.effective_mode,'generation':r.generation,'manifest_hash':r.manifest_hash,
            'failure_code':r.failure_code,'trace':r.trace,'timings_ms':dict(r.timings_ms),'evidence':citations,
            'answer':answer.model_dump(mode='json'),'limitations':['Research prototype; source correspondence is not financial certification.']}


class DemoResearchBackend(ResearchBackend):
    source_type='SYNTHETIC_DEMO'
    def __init__(self,root):
        root=Path(root).resolve();marker=root/'ownership.json'
        if root.exists() and (not marker.is_file() or json.loads(marker.read_text()).get('owner')!=OWNER):raise ValueError('RESEARCH_OWNERSHIP_REQUIRED')
        if not root.exists():
            root.mkdir(parents=True);marker.write_text(json.dumps({'owner':OWNER,'synthetic_demo':True}))
        cases=[
            ('Consolidated Income Statement','USD amounts in millions',['FY2025','FY2024'],'Net sales',['100','90']),
            ('Consolidated Balance Sheet','USD amounts in thousands',['As of January 31, 2025','As of January 31, 2024'],'Current liabilities',['(125.50)','90']),
            ('Consolidated Statements of Cash Flows','USD amounts in millions',['FY2025','FY2024'],'Net income',['25','20']),
            ('Net Income Per Common Share','USD amounts in millions, except per share data',['FY2025','FY2024'],'Basic EPS',['2.74','2.42']),
            ('Segment Reporting','USD amounts in millions',['FY2025','USD change','Percent change'],'Segment A operating income',['139','51','58%']),
            ('Note 7 Fair Value Measurements','USD amounts in millions',['As of January 31, 2025 / Carrying amount','As of January 31, 2025 / Fair value'],'Long-term debt',['38,166','36,777']),
        ]
        html='<html><body>'+''.join('<h1>'+title+'</h1><p>'+unit+'</p><table><tr><th>Metric</th>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr><tr><td>'+row+'</td>'+''.join('<td>'+v+'</td>' for v in values)+'</tr></table>' for title,unit,headers,row,values in cases)+'</body></html>'
        raw=html.encode();raw_hash=sha256(raw).hexdigest()
        m=FilingMetadata(filing_id='sec:0000000202:0000000202-25-000001',cik='0000000202',accession_number='0000000202-25-000001',
            company_name='D4 Synthetic Issuer',form_type='10-K',filing_date='2026-03-01',report_date='2025-01-31',
            primary_document='synthetic-d4.htm',source_url='https://example.invalid/synthetic-d4.htm',raw_content_hash=raw_hash,
            parser_version=PARSER_VERSION,chunker_version=CHUNKER_VERSION,ingestion_version=INGESTION_VERSION,document_status='READY')
        f=parse_sec_html(raw,m);m.normalized_content_hash=sha256(normalized_filing_text(f).encode()).hexdigest();chunks=chunk_filing(f)
        generation=digest({'synthetic':'d4-demo-v1','raw_hash':raw_hash});manifest=digest({'synthetic':True,'raw_hash':raw_hash})
        b=SourceBindingV1(dataset_id='synthetic-d4-v1',manifest_hash=manifest,generation_id=generation,filing_id=m.filing_id,
            raw_hash=raw_hash,normalized_hash=m.normalized_content_hash,metadata_hash=digest(m.model_dump(mode='json')),
            parent_hashes=tuple(sorted((p.chunk_id,digest(p.model_dump(mode='json'))) for p in chunks)))
        self.context=context_from_snapshot(raw,m,b)
        columns=[]
        for p in chunks:
            if p.kind!='table':continue
            e=build_table_evidence(p,self.context).evidence
            if e is None:continue
            for c in e.cells:
                if c.period:
                    cp=c.period
                    columns.append({'period':{'kind':cp.kind,'year':cp.year,'quarter':cp.quarter,'end':cp.end,'months':cp.months,'raw':' / '.join(cp.raw_labels)},'source_ref':c.locator.structural_path})
        self.catalog=CorpusCatalogV1(dataset_id=b.dataset_id,manifest_hash=manifest,generation_id=generation,provenance='EXPLICIT_SYNTHETIC_DEMO_NOT_SEC',
            issuers=[{'cik':m.cik,'company_name':m.company_name}],filings=[{'filing_id':m.filing_id,'cik':m.cik,'accession':m.accession_number,
                'form':'10-K','extraction_status':'READY','column_periods':columns,'column_periods_complete':True}])
        lexical=LexicalIndex(root/'demo.sqlite3')
        try:record=lexical.generation(b.dataset_id,generation)
        except ValueError:record=None
        if record is None or record['state']!='READY':
            lexical.start(b.dataset_id,generation,{'synthetic':True});lexical.add(generation,[{'chunk':p.model_dump(mode='json'),'source':{'synthetic':True}} for p in chunks]);lexical.seal(generation);lexical.publish(b.dataset_id,generation)
        self.adapter=DemoAdapter(lexical,[self.context])

    def evidence_lookup(self,hit):
        p=self.context.parent(hit.chunk_id)
        return build_table_evidence(p,self.context).evidence if p is not None else None
