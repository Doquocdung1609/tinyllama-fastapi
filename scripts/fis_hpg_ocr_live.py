"""Live OCR V2 checks using only the locally indexed, original HPG PDF."""
import json
from pathlib import Path
from time import perf_counter

import requests

root=Path(__file__).resolve().parents[1]
out=root/'tmp/ocr-hpg-repair'
gold=json.loads((root/'reports/hpg_ocr/visual_gold.json').read_text(encoding='utf-8-sig'))
doc=gold['document_id']
base='http://127.0.0.1:18111/studio'
original='http://127.0.0.1:18110/studio'


def main():
    token=(root/'tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    with requests.Session() as client:
        client.headers['Authorization']='Bearer '+token
        records=[]
        def record(name,route,payload,server=base):
            started=perf_counter()
            try:
                response=client.post(server+route,json=payload,timeout=65)
                body=response.json()
                entry={'case':name,'http':response.status_code,'seconds':perf_counter()-started,'body':body}
            except requests.RequestException as exc:
                entry={'case':name,'error':type(exc).__name__,'seconds':perf_counter()-started}
            records.append(entry)
            (out/'live.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            body=entry.get('body',{})
            print(name,entry.get('http'),body.get('status'),body.get('values'),round(entry['seconds'],2),flush=True)
            return body

        for mode,profile in [('bm25','baseline'),('dense','baseline'),('hybrid','baseline'),('bm25','faith_r_product_v1')]:
            record(mode+'-'+profile,'/query',{'query':'Tổng cộng tài sản công ty mẹ Hòa Phát 31/12/2025',
                   'source':'USER_UPLOADS','document_ids':[doc],'mode':mode,'search_profile':profile,'top_k':5})
        for name,q in [
            ('assets','Tìm dòng Tổng cộng tài sản công ty mẹ tại ngày 31/12/2025. Trích giá trị gốc và trang.'),
            ('revenue','Doanh thu thuần quý IV/2025 và cả năm 2025 là bao nhiêu?'),
            ('income','Lợi nhuận sau thuế quý IV/2025 là bao nhiêu?'),
            ('cash','Đọc tổng tiền lưu chuyển thuần từ hoạt động kinh doanh năm 2025, bao gồm dấu âm.'),
            ('investments','Bảng đầu tư vào các công ty con trang 13 có những công ty nào và số liệu kỳ nào?'),
            ('fixed-assets','Tài sản cố định hữu hình đầu năm 2025 là bao nhiêu?'),
        ]:
            record(name,'/chat',{'question':q,'document_ids':[doc]})
        page=client.get(base+f'/documents/{doc}/pages/4/evidence',timeout=35).json()
        review_row=next((r for r in page.get('tables',[]) if r.get('item_code')=='300'),None)
        if review_row:
            expected=gold['pages']['4']['rows'][0][2]
            assert review_row['cells'][0]['period']=='31/12/2025'
            record('review-liabilities',f'/documents/{doc}/facts/review',
                {'page':4,'row_id':review_row['id'],'column_index':0,'metric':'liabilities','period':'2025-12-31',
                 'column_label':'31/12/2025','statement_scope':'SEPARATE','unit':'VND','convention':'vi_VN',
                 'source_image_reviewed':True,'reviewed_display':expected})
            record('chat-reviewed-liabilities','/chat',{'question':'Nợ phải trả công ty mẹ là bao nhiêu tại ngày 31/12/2025?',
                   'document_ids':[doc]})
        page=client.get(base+f'/documents/{doc}/pages/3/evidence',timeout=35).json()
        assets=next(r for r in page['tables'] if r.get('item_code')=='270')
        _,label,amount,_=next(r for r in gold['pages']['3']['rows'] if r[0]=='270')
        review_payload={'page':3,'row_id':assets['id'],'column_index':0,'metric':'assets',
            'period':'2025-12-31','column_label':'31/12/2025','statement_scope':'SEPARATE',
            'unit':'VND','convention':'vi_VN','source_image_reviewed':True,
            'reviewed_label':label,'reviewed_display':amount}
        record('review-assets-wrong-column',f'/documents/{doc}/facts/review',{**review_payload,'column_index':1})
        record('review-assets',f'/documents/{doc}/facts/review',review_payload)
        record('chat-reviewed-assets','/chat',{'question':'Tổng cộng tài sản công ty mẹ là bao nhiêu tại ngày 31/12/2025?',
            'document_ids':[doc]})
        for name,docid,q in [
            ('apple','3eb270b22acb7d8d8e9c32a43dc221de','Doanh thu Services Apple FY2025 là bao nhiêu?'),
            ('bidv','2bed2b3c312c8149e6a2ff6ab80c694a','Năm 2024, lợi nhuận sau thuế chưa phân phối: mức điều chỉnh của riêng ngân hàng và hợp nhất khác nhau bao nhiêu?'),
        ]:
            record(name,'/chat',{'question':q,'document_ids':[docid]},original)


if __name__=='__main__':
    main()
