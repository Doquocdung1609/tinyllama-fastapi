"""Live V4 checks. Writes observed answers and timing, excluding credentials."""
import json
from pathlib import Path
from time import perf_counter, sleep
import requests

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'tmp/studio-runtime'
BASE='http://127.0.0.1:18110'


def main():
    client=requests.Session()
    for _ in range(80):
        try:
            if client.get(BASE+'/health',timeout=2).ok:
                break
        except requests.RequestException:
            pass
        sleep(2)
    client.headers['Authorization']='Bearer '+(RUNTIME/'access-token.txt').read_text(encoding='utf-8-sig').strip()
    sec=client.get(BASE+'/studio/sec/catalog',timeout=90).json()['filings']
    docs=client.get(BASE+'/studio/documents',timeout=90).json()['documents']
    ids=lambda ticker:[f['filing_id'] for f in sec if f['ticker']==ticker]
    pdf=lambda part:next(d['id'] for d in docs if part in (d['filename']+' '+(d.get('issuer') or '')).upper())
    cases=[]
    def case(name,question,ticker,files=None,expect=(),route='chat'):
        cases.append((name,route,dict(question=question,**({'source':'US_SEC'} if route=='chat' else {}),
                    ticker=ticker,filing_ids=files or ids(ticker)),expect))
    case('cost-quarter','COST net sales for the three months ended 2026-05-10','COST')
    case('cost-quarter-warm','COST net sales for the three months ended 2026-05-10','COST')
    case('cost-12w','COST net sales for 12 weeks ended 2026-05-10','COST')
    case('cost-36w','COST net sales for 36 weeks ended 2026-05-10','COST')
    case('cost-prior','COST net sales for 12 weeks ended 2025-05-11','COST')
    case('cost-assets','COST total assets as of 2026-05-10','COST')
    case('hd-13w','HD net sales for 13 weeks ended 2026-08-02','HD',expect=('47861',))
    case('hd-26w','HD net sales for 26 weeks ended 2026-08-02','HD',expect=('89626',))
    case('hd-assets','HD total assets as of 2026-08-02','HD',expect=('109384',))
    case('hd-ambiguous','HD net sales as of 2026-08-02','HD')
    case('pg-cross-generation','Compare PG net sales for the three months ended 2026-03-31 and 2026-09-30','PG',expect=('23276',))
    case('pg-prior-year','Compare PG net sales for the three months ended 2025-09-30 and 2026-09-30','PG',expect=('22386','23276'))
    case('issuer-conflict','Compare net sales in the selected filings','',ids('PG')+ids('HD'))
    cases.append(('federated-search','query',{'source':'US_SEC','query':'PG net sales','mode':'bm25','top_k':10,
                  'filing_ids':ids('PG'),'search_profile':'faith_r_product_v1'},()))
    cases.append(('pdf-multi','chat',{'question':'Tìm bảng cân đối kế toán trong các PDF đang chọn và dẫn nguồn.',
                   'document_ids':[pdf('AAPL'),pdf('BIDV')]},()))
    cases.append(('pdf-apple','chat',{'question':'Trong 100 USD doanh thu Apple năm 2025 có bao nhiêu USD từ Services?',
                   'document_ids':[pdf('AAPL')]},()))
    for name,ticker,question in [('apple','AAPL','So sánh doanh thu Apple FY2024 và FY2025'),
                                  ('microsoft','MSFT','So sánh lợi nhuận ròng Microsoft FY2024 và FY2025')]:
        if len(ids(ticker))>1:
            case(name,question,ticker)
    records=[]
    for name,route,data,expected in cases:
        start=perf_counter()
        try:
            response=client.post(BASE+'/studio/'+route,json=data,timeout=45)
            body=response.json()
            record={'case':name,'http':response.status_code,'status':body.get('status'),'reason':body.get('reason',body.get('detail')),
                'answer':body.get('answer'),'values':body.get('values'),'timings_ms':body.get('timings_ms'),
                'cells':body.get('source_cells'),'citations':body.get('citations',body.get('results',[])),
                'expected_source_values':expected}
        except requests.RequestException as exc:
            record={'case':name,'error':type(exc).__name__}
        record['seconds']=round(perf_counter()-start,3)
        records.append(record)
        print(record['case'],record.get('http'),record.get('status'),record.get('reason'),record['seconds'],flush=True)
        (RUNTIME/'v4-live.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
