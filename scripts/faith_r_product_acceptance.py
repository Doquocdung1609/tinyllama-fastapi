"""Real local HTTP acceptance. No uploads, index changes, model installs or secret output."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import requests
import copy
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

Q1='BIDV năm 2024 có những số liệu nào được điều chỉnh sau kiểm toán?'
Q2='Tìm dòng lợi nhuận sau thuế chưa phân phối trong bảng điều chỉnh báo cáo tài chính BIDV năm 2024'
Q2B='Tìm dòng "Lợi nhuận sau thuế chưa phân phối" trong tài liệu đang chọn. Cho biết các đoạn nguồn liên quan và trang PDF.'
Q3='Trong hai bảng này, mức điều chỉnh của riêng ngân hàng và hợp nhất khác nhau bao nhiêu?'

def run(args):
    s=requests.Session();s.headers['Authorization']='Bearer '+args.token_file.read_text(encoding='utf-8-sig').strip()
    base=args.url.rstrip('/')+'/studio';out={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'url':args.url,'records':[],'paired':[]}
    def call(route,body):
        t=perf_counter();r=s.post(base+'/'+route,json=body,timeout=120)
        data=r.json();out['records'].append({'route':route,'request':body,'http':r.status_code,'elapsed_ms':round((perf_counter()-t)*1000,2),'response':data})
        r.raise_for_status();return data
    docs=s.get(base+'/documents',timeout=30).json()['documents'];out['documents']=docs
    bid=next(d for d in docs if 'BID' in d['filename']);hpg=next(d for d in docs if 'hpg' in d['filename'].lower());apple=next(d for d in docs if 'AAPL' in d['filename'])
    cases=[(bid,q) for q in (Q1,Q2,Q2B)]+[(hpg,q) for q in (
        'Tìm dòng tổng tài sản của công ty mẹ Hòa Phát trong tài liệu.',
        'Tóm tắt báo cáo riêng công ty mẹ Hòa Phát và dẫn nguồn.',
        'Giải thích phạm vi công ty mẹ trong báo cáo Hòa Phát.',
        'Tìm bằng chứng báo cáo hợp nhất Hòa Phát trong tài liệu đang chọn.',
        'Lợi nhuận sau thuế công ty mẹ Hòa Phát năm 2025 là bao nhiêu?')]+[(apple,q) for q in (
        'Summarize the selected Apple annual report with sources.',
        'What were Apple total net sales in fiscal 2025?',
        'Doanh thu thuần Apple năm tài chính 2025 là bao nhiêu?',
        'Find the total net sales table in Apple fiscal 2025.',
        'What was Apple net income growth from fiscal 2024 to fiscal 2025?')]+[(bid,q) for q in (
        'Tìm dòng lợi nhuận sau thuế chưa phân phối riêng ngân hàng năm 2024.',
        'Tìm dòng lợi nhuận sau thuế chưa phân phối hợp nhất năm 2024.',
        'Đơn vị trình bày trong tài liệu BIDV là gì?',
        'Giải thích các cột số liệu đã công bố và số trình bày lại.',
        'Tìm dòng dự phòng rủi ro cho vay khách hàng trong bảng điều chỉnh.',
        'Tóm tắt tài liệu BIDV năm 2024 và dẫn nguồn.')]
    q2b=None
    for d,q in cases:
        a=call('chat',{'question':q,'document_ids':[d['id']]})
        print(d['id'][:8],a['status'],[h.get('page') for h in a.get('citations',[])],flush=True)
        assert a.get('session_id')
        if q in (Q2,Q2B):
            assert a['status']=='SOURCE_EXCERPTS' and {4,7}<={h['page'] for h in a['citations']}
            assert all(h.get('numeric_status')=='CELL_VERIFIED' for h in a['citations'])
        if q==Q2B:q2b=a
    follow=call('chat',{'question':Q3,'document_ids':[bid['id']],'session_id':q2b['session_id']})
    assert follow['status']=='SUPPORTED' and follow['values']==['1114'],follow
    wrong=call('chat',{'question':'Doanh thu Hòa Phát năm 2024 là bao nhiêu?','document_ids':[bid['id']]})
    assert wrong['status']=='QUERY_CONTEXT_CONFLICT' and not wrong['citations']
    persisted=s.get(base+'/chat/'+q2b['session_id'],timeout=30).json()
    assert len(persisted['turns'])==2 and len(persisted['messages'])==4
    out['durable_session_id']=q2b['session_id']
    search=call('query',{'query':Q2B,'document_ids':[bid['id']],'source':'USER_UPLOADS','search_profile':'auto'})
    assert [h['citation_id'] for h in search['results']]==[h['citation_id'] for h in q2b['citations']]
    assert search['algorithm_executed']=='FAITH_R_PRODUCT_V1_PDF_ROW_UNION_RERANK'
    call('chat',{'question':'Explain Apple revenue FY2025','source':'US_SEC','ticker':'AAPL'})
    if args.paired:
        for d,q in [(bid,Q1),(bid,Q2),(bid,Q2B),(hpg,cases[3][1]),(apple,cases[11][1])]:
            for profile,mode in [('baseline','bm25'),('baseline','dense'),('baseline','hybrid'),('production_v3','hybrid'),('faith_r_product_v1','hybrid')]:
                t=perf_counter();r=s.post(base+'/query',json={'query':q,'document_ids':[d['id']],'source':'USER_UPLOADS','search_profile':profile,'mode':mode},timeout=120)
                data=r.json();out['paired'].append({'question':q,'document_id':d['id'],'profile':profile,'mode':mode,'http':r.status_code,
                    'elapsed_ms':round((perf_counter()-t)*1000,2),'pages':[h.get('page') for h in data.get('results',[])],
                    'rows':[h.get('row_label') for h in data.get('results',[])],'response':data})
                print('paired',profile,mode,r.status_code,out['paired'][-1]['pages'],flush=True)
    for d in docs:
        r=s.get(base+f"/documents/{d['id']}/file",timeout=30);r.raise_for_status()
        assert sha256(r.content).hexdigest()==d['sha256']
    out['source_integrity']='UNCHANGED_SHA256_ALL_THREE_PDFS'
    # Independent original-file safety probes; no table data or corpus is edited.
    from app.product.native_adjustments import verify_rows,comparison_answer
    class ReadOnlySource:
        def document(self,document_id):return next(d for d in docs if d['id']==document_id)
        def source_file(self,document_id):
            path=args.workspace/'files'/f'{document_id}.pdf'
            assert sha256(path.read_bytes()).hexdigest()==self.document(document_id)['sha256']
            return path
    source=ReadOnlySource();out['native_safety_probes']=[]
    for name in ('altered_digit','wrong_row','wrong_scope','wrong_period','unrelated_heading','ocr'):
        h=copy.deepcopy(q2b['citations'][0])
        if name=='altered_digit':h['source_cells'][0]['text']+='9'
        elif name=='wrong_row':h['row_label']='Unrelated accounting metric'
        elif name=='wrong_scope':h['statement_scope']='CONSOLIDATED'
        elif name=='wrong_period':h['report_period']='2023'
        elif name=='unrelated_heading':h['scope_provenance']['page']=1
        elif name=='ocr':h['extraction_method']='OCR';h.pop('adjustment_verification',None);h['numeric_status']='UNVERIFIED'
        checked=verify_rows(source,[h])[0]
        assert checked.get('numeric_status')!='CELL_VERIFIED',name
        out['native_safety_probes'].append({'probe':name,'status':'CORRECTLY_NOT_VERIFIED'})
    assert comparison_answer(Q3+' in EUR',q2b['citations']) is None
    out['native_safety_probes'].append({'probe':'unsupported_currency','status':'CORRECTLY_ABSTAINED'})
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: real HTTP acceptance; report',args.output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',default='http://127.0.0.1:18110')
    p.add_argument('--token-file',type=Path,default=Path('tmp/studio-runtime/access-token.txt'))
    p.add_argument('--output',type=Path,default=Path('reports/faith_r_product/after.json'));p.add_argument('--paired',action='store_true')
    p.add_argument('--workspace',type=Path,default=Path('studio_workspace/react-product-20261028'))
    run(p.parse_args())
