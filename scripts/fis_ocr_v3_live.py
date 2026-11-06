"""Live extraction, retrieval and chat measurements. Never submits review data."""
import json
from pathlib import Path

import requests

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'tmp/ocr-v3'
ID='4a92af827aaf1e73e017544d0ff20d0d'
CASES=[
    ('assets','Tổng cộng tài sản công ty mẹ là bao nhiêu tại ngày 31/12/2025?',3,'270','Tổng cộng tài sản','31/12/2025'),
    ('liabilities','Nợ phải trả công ty mẹ là bao nhiêu tại ngày 31/12/2025?',4,'300','Nợ phải trả','31/12/2025'),
    ('revenue-quarter','Doanh thu thuần quý IV/2025 là bao nhiêu?',5,'10','Doanh thu thuần','Q4 2025'),
    ('revenue-year','Doanh thu thuần cả năm 2025 là bao nhiêu?',5,'10','Doanh thu thuần','FY 2025'),
    ('income-quarter','Lợi nhuận sau thuế quý IV/2025 là bao nhiêu?',5,'60','Lợi nhuận sau thuế','Q4 2025'),
    ('income-year','Lợi nhuận sau thuế cả năm 2025 là bao nhiêu?',5,'60','Lợi nhuận sau thuế','FY 2025'),
    ('cash','Dòng tiền hoạt động kinh doanh cả năm 2025 là bao nhiêu?',6,'20','Lưu chuyển tiền thuần','FY 2025'),
    ('deposit','Tiền gửi ngân hàng đầu năm 2025 trang 12 là bao nhiêu?',12,None,'Tiền gửi ngân hàng','01/01/2025'),
    ('dash','Tìm dòng Điện máy Gia dụng trang 13, dự phòng đầu năm 2025.',13,None,'Điện máy Gia dụng','01/01/2025 Dự phòng'),
]


def main():
    from app.product.pdf_extract import folded
    from scripts.fis_hpg_ocr_benchmark import matching
    client=requests.Session()
    client.headers['Authorization']='Bearer '+(ROOT/'tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()

    def call(port,path,payload=None):
        url=f'http://127.0.0.1:{port}/studio{path}'
        response=client.get(url,timeout=55) if payload is None else client.post(url,json=payload,timeout=55)
        response.raise_for_status()
        return response.json()

    report={'generations':{},'chat':{},'controls':{}}
    for port in (18111,18112):
        report['generations'][port]=results={}
        page_cache={p:call(port,f'/documents/{ID}/pages/{p}/evidence') for p in {row[2] for row in CASES}}
        for name,query,number,code,label,period in CASES:
            evidence=page_cache[number]
            row=next((r for r in evidence['tables'] if folded(label) in folded(r['row_label'])),None) if not code else None
            row=row or matching(evidence['tables'],code,label)
            cell=next((c for c in row['cells'] if c.get('period')==period),None) if row else None
            search=call(port,'/query',{'query':query,'source':'USER_UPLOADS','document_ids':[ID],
                            'mode':'hybrid','search_profile':'faith_r_product_v1','top_k':5})
            targets=[h for h in search['results'] if row and h['page']==number and h.get('row_id')==row['id']]
            exact_cells=[h for h in targets if cell and cell.get('box') and h.get('column_id')==cell.get('cell_id') and h.get('box')==cell['box']]
            results[name]={'target_rank':min((h['rank'] for h in targets),default=None),
                           'cell_rank':min((h['rank'] for h in exact_cells),default=None),
                           'hits':[{k:h.get(k) for k in ('rank','page','row_id','column_id','row_label','box')} for h in search['results']]}
            print(port,name,results[name]['target_rank'],results[name]['cell_rank'],flush=True)
    facts=call(18112,f'/documents/{ID}/facts')['facts']
    report['review_ledger_count']=len(facts)
    for name,query,*_ in CASES:
        report['chat'][name]=call(18112,'/chat',{'question':query,'document_ids':[ID]})
    for name,query in [
        ('revenue-both','Doanh thu thuần quý IV/2025 và cả năm 2025 là bao nhiêu?'),
        ('income-both','Lợi nhuận sau thuế quý IV/2025 và cả năm 2025 là bao nhiêu?'),
    ]:
        report['chat'][name]=call(18112,'/chat',{'question':query,'document_ids':[ID]})
    for name,doc,query in [
        ('apple','3eb270b22acb7d8d8e9c32a43dc221de','Doanh thu Services Apple FY2025 là bao nhiêu?'),
        ('bidv','2bed2b3c312c8149e6a2ff6ab80c694a','Năm 2024, lợi nhuận sau thuế chưa phân phối: mức điều chỉnh của riêng ngân hàng và hợp nhất khác nhau bao nhiêu?'),
    ]:
        report['controls'][name]=call(18110,'/chat',{'question':query,'document_ids':[doc]})
    (OUTPUT/'live.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
