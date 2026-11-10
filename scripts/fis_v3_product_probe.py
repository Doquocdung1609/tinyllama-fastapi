"""Live V3 regression ledger. Credentials are read locally and never recorded."""
import argparse,json,time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
QUESTIONS=[
 'Trong năm tài chính 2025, khu vực nào của Apple giảm doanh thu so với 2024? Giảm bao nhiêu triệu USD, giảm bao nhiêu phần trăm, và vì sao?',
 'Theo tôi, doanh thu Greater China năm 2025 là 69.377 triệu USD. Tôi nói đúng không?',
 'Trong 100 USD doanh thu Apple năm 2025 thì khoảng bao nhiêu USD đến từ Services?',
 'Biên lợi nhuận gộp Services FY2025 cao hơn Products bao nhiêu điểm phần trăm? Nếu dùng phần trăm tăng tương đối thì có giống nhau không?',
 'Doanh thu tại Hoa Kỳ của Apple năm 2025 có bằng khu vực Americas không? Nếu không, khác nhau thế nào?',
 'Cứ 100 đồng doanh thu Apple năm 2025 thì mấy đồng thuộc dịch vụ?',
 'Services đóng góp bao nhiêu trong tổng số doanh thu FY2025?',
 'Trong mỗi 100 USD doanh thu FY2025 có bao nhiêu USD từ Services?',
 'Compare FY2025 Services and Products gross margins in percentage points and relative percent.',
 'Services so với Products FY2025: chênh lệch biên lợi nhuận gộp theo điểm phần trăm và phần trăm tương đối?',
]
def main():
 a=argparse.ArgumentParser();a.add_argument('--name',default='before');args=a.parse_args()
 out=ROOT/'reports/fis_product_v3';out.mkdir(exist_ok=True,parents=True)
 headers={'Authorization':'Bearer '+(ROOT/'tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()}
 records=[]
 for i,q in enumerate(QUESTIONS,1):
  req={'question':q,'document_ids':['3eb270b22acb7d8d8e9c32a43dc221de']};start=time.perf_counter()
  r=requests.post('http://127.0.0.1:18110/studio/chat',headers=headers,json=req,timeout=150)
  body=r.json();records.append({'id':f'A{i:02}','request':req,'http':r.status_code,'elapsed_ms':round((time.perf_counter()-start)*1000,2),'response':body})
  print(i,r.status_code,body.get('answer_status'),body.get('values'),body.get('reason'),flush=True)
  (out/(args.name+'.json')).write_text(json.dumps({'mocked':False,'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
