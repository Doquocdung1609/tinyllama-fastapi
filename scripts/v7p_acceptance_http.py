"""Exposed Apple product regressions over authenticated real HTTP; never G2."""
import argparse
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from time import perf_counter,sleep
import requests

APPLE_SHA='3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de'
QUESTIONS=[
    "What was Apple's net income in fiscal year 2025?",
    'Which geographic segment generated the highest net sales in fiscal year 2025, and how much did it generate?',
    "Calculate Apple's year-over-year total net sales growth rate from fiscal 2024 to fiscal 2025. Show the calculation and round to two decimal places."
]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:18110')
    parser.add_argument('--apple',type=Path,required=True);parser.add_argument('--token-file',type=Path,default=Path('tmp/studio-runtime/access-token.txt'))
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--output',type=Path,default=Path('docs/topic3_v7p/V7P_REAL_APPLE_3_CASES_E2E.json'))
    args=parser.parse_args();raw=args.apple.read_bytes()
    assert sha256(raw).hexdigest()==APPLE_SHA,'Unexpected source PDF'
    token=args.token_file.read_text(encoding='utf-8-sig').strip();session=requests.Session()
    session.headers['Authorization']='Bearer '+token
    base=args.base_url.rstrip('/');records=[]
    def call(name,path,body,expected_value=None,expect_refusal=False):
        if path=='/chat' and 'session_id' not in body:body={**body,'session_id':sha256(('v7p-product-regression-'+name).encode()).hexdigest()[:32]}
        started=perf_counter();response=session.post(base+'/studio'+path,json=body,timeout=120)
        result=response.json();passed=response.status_code==200
        if expected_value is not None:passed=passed and result.get('status')=='SUPPORTED' and result.get('values')==[expected_value]
        if expect_refusal:passed=passed and result.get('status')!='SUPPORTED' and not result.get('values')
        records.append({'case':name,'request':body,'http_status':response.status_code,'response':result,
                        'latency_ms':round((perf_counter()-started)*1000,2),'pass':passed})
        print(name,response.status_code,result.get('status'),flush=True)
        assert passed,f'{name}: {response.status_code} {result.get("status")} {result.get("reason")}'
        return result
    docs=session.get(base+'/studio/documents',timeout=20).json()['documents']
    doc=next((d for d in docs if d['sha256']==APPLE_SHA),None)
    if doc is None:
        response=session.post(base+'/studio/documents',files={'file':(args.apple.name,raw,'application/pdf')},timeout=30)
        assert response.status_code==202;doc=response.json()
    for _ in range(240):
        doc=session.get(base+'/studio/documents/'+doc['id'],timeout=20).json()
        if doc['status'] in {'READY','FAILED'}:break
        sleep(1)
    assert doc['status']=='READY',doc.get('error_code')
    doc_ids=[doc['id']]
    for i,(q,value) in enumerate(zip(QUESTIONS,['112010','178353','6.43'])):
        answer=call('APPLE-'+str(i+1),'/chat',{'question':q,'document_ids':doc_ids},value)
        assert answer['citations']
        assert all(c['verification_status']=='CELL_VERIFIED' and c['source_sha256']==APPLE_SHA and c['cell_bbox'] and c['header_bbox'] and c['retrieved_chunk_ids'] for c in answer['citations'])
        if i==0:assert answer['citations'][0]['page']==32
        if i==1:assert len(answer['citations'])==5 and answer['winner']=='Americas'
        if i==2:
            assert {c['fiscal_year'] for c in answer['citations']}=={2024,2025}
            assert all(c['currency']=='USD' and Decimal(c['scale'])==1000000 for c in answer['citations'])
    for period in ('2025','2025-09-27','FY2025'):
        call('MATCHING_ADVANCED_'+period,'/chat',{'question':QUESTIONS[0],'document_ids':doc_ids,
            'constraints':{'metric':'net_income','operation':'EXTRACT','statement_scope':'CONSOLIDATED','current_period':period}},'112010')
    call('ISSUER_INHERITED','/chat',{'question':'Net income fiscal 2025?','document_ids':doc_ids},'112010')
    for name,q,extra in [
        ('FUTURE_YEAR',"What was Apple's net income in fiscal year 2037?",{}),
        ('WRONG_COMPANY',"What was Microsoft's net income in fiscal year 2025?",{}),
        ('QUARTER','What was net income in Q2 FY2025?',{}),
        ('QUALIFIED_METRIC','What was net income attributable to common shareholders in 2025?',{}),
        ('CAPEX','What was total CAPEX in 2025?',{}),
        ('REQUESTED_EUR','Net income fiscal 2025 in EUR?',{}),
        ('UNQUALIFIED_REVENUE','Revenue fiscal 2025?',{}),
        ('WRONG_SEGMENT_METRIC','Which segment had highest net income fiscal 2025?',{}),
        ('RESTATED_FILTER',QUESTIONS[0],{'basis':'RESTATED'}),
        ('WRONG_SCOPE','Net income in separate financial statements for 2025?',{}),
        ('EXPLICIT_METRIC',QUESTIONS[2],{'metric':'assets'}),
        ('EXPLICIT_OPERATION',QUESTIONS[2],{'operation':'EXTRACT'}),
        ('EXPLICIT_SCOPE',QUESTIONS[0],{'statement_scope':'SEPARATE'}),
        ('EXPLICIT_DATE',QUESTIONS[0],{'current_period':'2025-12-31'})]:
        call(name,'/chat',{'question':q,'document_ids':doc_ids,'constraints':extra},expect_refusal=True)
    first=call('FOLLOWUP_SEED','/chat',{'question':'Total net sales fiscal 2025?','document_ids':doc_ids},'416161')
    call('FOLLOWUP_GROWTH','/chat',{'question':'So với năm 2024 tăng bao nhiêu phần trăm?','document_ids':doc_ids,'session_id':first['session_id']},'6.43')
    call('FOLLOWUP_EXACT_PRIOR','/chat',{'question':'Còn năm 2024?','document_ids':doc_ids,'session_id':first['session_id']},'391035')
    call('NARRATIVE','/chat',{'question':'What does the report say about risk factors?','document_ids':doc_ids})
    call('COMPANY_RESEARCH','/chat',{'question':'Nghiên cứu doanh nghiệp dựa trên tài liệu đã chọn','document_ids':doc_ids})
    found=session.post(base+'/studio/query',json={'query':QUESTIONS[0],'source':'USER_UPLOADS','document_ids':doc_ids,'search_profile':'auto'},timeout=120).json()
    assert found['financial_evidence']['values']==['112010']
    assert found['financial_evidence']['evidence_contract']==records[0]['response']['evidence_contract']
    for endpoint in ('/studio/documents','/studio/documents/'+doc['id']+'/file'):
        assert requests.get(base+endpoint,timeout=20).status_code in (401,503)
    assert session.post(base+'/studio/chat',json={'question':'Net income 2025?','document_ids':[]},timeout=10).status_code==422
    invalid=session.post(base+'/studio/documents',files={'file':('broken.pdf',b'%PDF-not-a-document','application/pdf')},timeout=20)
    assert invalid.status_code==422
    source=args.workspace.resolve()/'files'/f"{doc['id']}.pdf"
    assert source.is_file() and sha256(source.read_bytes()).hexdigest()==APPLE_SHA
    try:
        source.write_bytes(raw+b'one-byte-tamper')
        response=session.post(base+'/studio/chat',json={'question':QUESTIONS[0],'document_ids':doc_ids},timeout=20)
        assert response.status_code==409 and not response.json().get('values')
        records.append({'case':'ISOLATED_SOURCE_TAMPER','http_status':response.status_code,'response':response.json(),'pass':True})
    finally:source.write_bytes(raw)
    with sqlite3.connect(args.workspace/'index.sqlite3') as db:
        reviewed=db.execute('SELECT count(*) FROM reviewed_facts').fetchone()[0]
    assert reviewed==0,'No manually seeded facts allowed'
    payload={'source_sha256':APPLE_SHA,'document_id':doc['id'],'manual_reviewed_fact_count':reviewed,
        'search_profile':found['search_profile'],'generation':found['generation'],'cases':records,
        'summary':{'passed':sum(r['pass'] for r in records),'failed':sum(not r['pass'] for r in records)}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload['summary']))


if __name__=='__main__':main()
