"""Real localhost acceptance. No mocks, gold/index mutation, or secret logging."""
import argparse,csv,json,time,statistics
from decimal import Decimal
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/faith_r_product_v2'
DOCS=json.loads((OUT/'before.json').read_text(encoding='utf-8'))['documents']
D={label:next(d['id'] for d in DOCS if name in d['filename']) for label,name in [('HPG','hpg'),('BIDV','BID'),('AAPL','AAPL')]}
CASES=[]
def add(doc,q,expected='VERIFIED_ANSWER',values=None,pages=None,thread=None,endpoint='chat',tag=''):
    CASES.append(dict(id=f'V2-{len(CASES)+1:02}',doc=doc,question=q,expected=expected,values=values,pages=pages,thread=thread,endpoint=endpoint,tag=tag))
add('HPG','Đây là báo cáo tài chính riêng công ty mẹ hay báo cáo hợp nhất? Hãy dẫn trang nguồn.','SOURCE_SUPPORTED_NON_NUMERIC',pages=[1,2],thread='hpg1',tag='VI_OCR_META')
add('HPG','Tìm bảng cân đối kế toán riêng công ty mẹ Hòa Phát quý IV/2025.','SOURCE_SUPPORTED_NON_NUMERIC',pages=[2],thread='hpg2',tag='VI_OCR_META')
add('HPG','Tìm dòng tổng cộng tài sản cuối năm 2025.','SOURCE_SUPPORTED_NON_NUMERIC',pages=[3],thread='hpg2',tag='VI_OCR_META')
add('HPG','Lợi nhuận sau thuế của công ty mẹ Hòa Phát quý IV năm 2025 là bao nhiêu?','REQUIRES_SOURCE_REVIEW',pages=[5],tag='VI_OCR_META')
add('HPG','Lợi nhuận sau thuế hợp nhất năm 2025 là bao nhiêu?','UNSUPPORTED_SCOPE',thread='hpg1',tag='ADVERSARIAL')
add('HPG','Tóm tắt tài liệu đang chọn và dẫn nguồn.','SOURCE_SUPPORTED_NON_NUMERIC',tag='VI_OCR_META')
add('HPG','Tổng cộng tài sản riêng cuối năm 2025 là bao nhiêu?','REQUIRES_SOURCE_REVIEW',tag='VI_OCR_META')
add('HPG','BIDV lợi nhuận sau thuế chưa phân phối năm 2024 là bao nhiêu?','QUERY_CONTEXT_CONFLICT',tag='ADVERSARIAL')
add('HPG','Tìm báo cáo kết quả hoạt động kinh doanh riêng.','SOURCE_SUPPORTED_NON_NUMERIC',pages=[5],tag='VI_OCR_META')
add('BIDV','Tìm dòng lợi nhuận sau thuế chưa phân phối năm 2024.','SOURCE_SUPPORTED_NON_NUMERIC',pages=[4,7],thread='bidv1',tag='VI_OCR_META')
add('BIDV','Hai mức điều chỉnh của riêng ngân hàng và hợp nhất chênh lệch bao nhiêu?',values=['1114'],pages=[4,7],thread='bidv1',tag='ARITHMETIC')
add('BIDV','Lợi nhuận sau thuế chưa phân phối riêng năm 2024 sau điều chỉnh là bao nhiêu?',values=['34235054'],pages=[4],tag='EXTRACT')
add('BIDV','Lợi nhuận sau thuế chưa phân phối hợp nhất năm 2024 sau điều chỉnh là bao nhiêu?',values=['36264506'],pages=[7],tag='EXTRACT')
add('BIDV','Điều chỉnh lợi nhuận sau thuế chưa phân phối riêng năm 2024 tương đương bao nhiêu phần trăm số đã công bố?',values=['0.21'],pages=[4],tag='ARITHMETIC')
add('BIDV','Điều chỉnh lợi nhuận sau thuế chưa phân phối hợp nhất năm 2024 tương đương bao nhiêu phần trăm số đã công bố?',values=['0.20'],pages=[7],tag='ARITHMETIC')
add('BIDV','Những số liệu nào được điều chỉnh trong tài liệu?','PARTIAL_VERIFIED',tag='VI_OCR_META')
add('BIDV','Lợi nhuận sau thuế chưa phân phối riêng năm 2023 là bao nhiêu?','REQUIRES_SOURCE_REVIEW',tag='ADVERSARIAL')
add('AAPL',"What were Apple's FY2025 total net sales?",values=['416161'],pages=[32],thread='apple1')
add('AAPL','And in FY2024? How much did it grow in dollars and percent?',values=['25126','6.43'],pages=[32],thread='apple1',tag='ARITHMETIC')
add('AAPL','What percentage of FY2025 net sales came from Services?',values=['26.23'],tag='ARITHMETIC',thread='apple2')
add('AAPL','And in FY2024?',values=['24.59'],thread='apple2')
add('AAPL','What percentage of FY2024 net sales came from Services?',values=['24.59'],tag='ARITHMETIC')
add('AAPL','Which is higher, Services or Products gross margin in FY2025, and by how many percentage points?',values=['38.60'],pages=[27],tag='ARITHMETIC')
add('AAPL','Compare Services and Products gross margin percentages in FY2024.',values=['36.70'],pages=[27],tag='ARITHMETIC')
add('AAPL','What were total net sales in FY2024?',values=['391035'],pages=[32])
add('AAPL','What was net income in FY2025?',values=['112010'],pages=[32],thread='apple3')
add('AAPL','And in FY2024?',values=['93736'],pages=[32],thread='apple3')
add('AAPL','What was net income absolute difference FY2024 to FY2025?',values=['18274'],tag='ARITHMETIC')
add('AAPL','What was net income growth in FY2024 to FY2025?',values=['19.50'],tag='ARITHMETIC')
add('AAPL','What was net margin in FY2025?',values=['26.92'],tag='ARITHMETIC')
add('AAPL','Sum Products and Services net sales in FY2025.',values=['416161'],tag='ARITHMETIC')
add('AAPL','Do Products plus Services equal total net sales FY2025?',values=['0'],tag='ARITHMETIC')
add('AAPL','How much did Services net sales grow from FY2024 to FY2025?',values=['13.51'],tag='ARITHMETIC')
add('AAPL','Are U.S. sales and Americas segment sales the same metric in FY2025?',pages=[25,51],tag='GEOGRAPHY')
add('AAPL','Doanh thu thuần Apple năm 2025 là bao nhiêu triệu USD?',values=['416161'],tag='VI_NUMERIC')
add('AAPL','Tỷ trọng doanh thu Services năm 2025 chiếm bao nhiêu phần trăm?',values=['26.23'],tag='ARITHMETIC')
add('AAPL','What were Microsoft total net sales in FY2025?','QUERY_CONTEXT_CONFLICT',tag='ADVERSARIAL')
add('AAPL','What were total net sales in FY2026?','REQUIRES_SOURCE_REVIEW',tag='ADVERSARIAL')
add('AAPL','What were total net sales in Q4 FY2025?','REQUIRES_SOURCE_REVIEW',tag='ADVERSARIAL')
add('AAPL','What were total net sales FY2025 in EUR?','REQUIRES_SOURCE_REVIEW',tag='ADVERSARIAL')
add('AAPL','What were total net sales FY2025 in VND?','REQUIRES_SOURCE_REVIEW',tag='ADVERSARIAL')
add('AAPL','What were separate parent-company net sales FY2025?','UNSUPPORTED_SCOPE',tag='ADVERSARIAL')
add('AAPL','What was total net sales FY2025?',values=['416161'],thread='switch1')
add('HPG','And in FY2024?','REQUIRES_SOURCE_REVIEW',thread='switch1',tag='SOURCE_SWITCH')
for doc,q,pages in [('BIDV','Tìm dòng lợi nhuận sau thuế chưa phân phối năm 2024.',[4,7]),('HPG','Tìm bảng cân đối kế toán riêng công ty mẹ Hòa Phát quý IV/2025.',[2]),('AAPL','What were total net sales in FY2025?',[32])]:
    add(doc,q,'SOURCE_SUPPORTED_NON_NUMERIC' if doc!='AAPL' else 'VERIFIED_ANSWER',pages=pages,endpoint='query',tag='SEARCH')
    add(doc,q,'SOURCE_SUPPORTED_NON_NUMERIC' if doc!='AAPL' else 'VERIFIED_ANSWER',pages=pages,endpoint='compare',tag='LAB')
add('SEC','What was Apple total net sales FY2025?','SOURCE_UNAVAILABLE',tag='SEC_BLOCKED')
add('SEC','What was Apple net income FY2024?','SOURCE_UNAVAILABLE',tag='SEC_BLOCKED')

add('BIDV','Kiểm tra lợi nhuận sau thuế chưa phân phối riêng năm 2024: số đã công bố cộng điều chỉnh có bằng số trình bày lại không?',values=['0'],pages=[4],tag='ARITHMETIC')

def run():
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='real-e2e');parser.add_argument('--ids');args=parser.parse_args()
    session=requests.Session();session.headers['Authorization']='Bearer '+(ROOT/'tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    threads={};records=[]
    for c in CASES:
        if args.ids and c['id'] not in args.ids.split(','):continue
        docs=[D[c['doc']]] if c['doc']!='SEC' else []
        request={'question':c['question'],'document_ids':docs,'source':'USER_UPLOADS' if docs else 'US_SEC'}
        if c['doc']=='SEC':request['ticker']='AAPL'
        if c['thread'] and c['thread'] in threads:request['session_id']=threads[c['thread']]
        if c['endpoint']!='chat':request={'query':c['question'],'document_ids':docs,'source':'USER_UPLOADS','search_profile':'auto','top_k':5}
        start=time.perf_counter();r=session.post('http://127.0.0.1:18110/studio/'+c['endpoint'],json=request,timeout=180);elapsed=(time.perf_counter()-start)*1000
        response=r.json();answer=response if c['endpoint']=='chat' else (response.get('candidate',response) or {}).get('financial_evidence',{})
        if c['thread'] and response.get('session_id'):threads[c['thread']]=response['session_id']
        actual=answer.get('answer_status',answer.get('status'));values=answer.get('values',[]);pages={v.get('page') for v in answer.get('citations',[])}
        checks={'http':r.status_code==200,'status':actual==c['expected'],'values':c['values'] is None or [Decimal(v) for v in values]==[Decimal(v) for v in c['values']], 'pages':c['pages'] is None or set(c['pages'])<=pages,'numeric_gate':not values or answer.get('independent_verification',{}).get('status')=='VERIFIED'}
        outcome='PASS' if all(checks.values()) else 'FAIL'
        if outcome=='PASS' and c['expected'] in {'REQUIRES_SOURCE_REVIEW','PARTIAL_VERIFIED'}:outcome='PARTIAL'
        if c['doc']=='SEC' and checks['http'] and actual=='SOURCE_UNAVAILABLE':outcome='BLOCKED'
        records.append({**c,'request':request,'http':r.status_code,'elapsed_ms':round(elapsed,2),'outcome':outcome,'checks':checks,'actual':actual,'response':response})
        print(c['id'],outcome,actual,values,sorted(p for p in pages if p),answer.get('reason'),flush=True)
        (OUT/(args.name+'.json')).write_text(json.dumps({'mocked':False,'gold_status':'SOURCE_FIRST_DEVELOPMENT_NOT_HUMAN_HOLDOUT','records':records},ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['id','doc','endpoint','thread','tag','question','expected','actual','outcome','values','pages','elapsed_ms','checks']
    with (OUT/(args.name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items() if k in fields} for row in records)
    print('TOTAL',len(records),{status:sum(r['outcome']==status for r in records) for status in ['PASS','FAIL','PARTIAL','BLOCKED']})
if __name__=='__main__':run()
