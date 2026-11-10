"""Record live Chat V5 answers without writing any reviewed facts."""
import argparse
import json
from pathlib import Path

import requests

DOCUMENT='4a92af827aaf1e73e017544d0ff20d0d'
QUESTIONS=[
    ('liabilities','Nợ phải trả của công ty mẹ Hòa Phát tại 31/12/2025 là bao nhiêu?'),
    ('assets','Tổng tài sản công ty mẹ Hòa Phát tại 31/12/2025 là bao nhiêu? Đã được người dùng kiểm duyệt chưa?'),
    ('revenue','Doanh thu thuần quý IV/2025 và cả năm 2025 của Hòa Phát là bao nhiêu?'),
    ('cash','Lưu chuyển tiền thuần từ hoạt động kinh doanh năm 2025 là bao nhiêu?'),
    ('deposit','Tiền gửi ngân hàng đầu năm 2025 trong thuyết minh Hòa Phát là bao nhiêu? OCR ban đầu và đọc lại khác nhau thế nào?'),
    ('dash','Dấu gạch trong cột dự phòng ở trang 13 có đồng nghĩa số 0 không?'),
    ('definition','Giải thích lưu chuyển tiền thuần từ hoạt động kinh doanh là gì.'),
    ('locator','Ô tổng tài sản tại 31/12/2025 ở trang nào?'),
    ('review','Nợ phải trả ngày 31/12/2025 đã được kiểm duyệt chưa?'),
    ('calculation','Tính tỷ lệ nợ phải trả trên tổng tài sản tại 31/12/2025.'),
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:18112')
    parser.add_argument('--output',type=Path,default=Path('tmp/chat-v5/after.json'))
    args=parser.parse_args()
    token=Path('tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    results={}
    with requests.Session() as client:
        client.headers['Authorization']='Bearer '+token
        for name,question in QUESTIONS:
            reply=client.post(args.url+'/studio/chat',json={'question':question,'document_ids':[DOCUMENT]},timeout=60)
            reply.raise_for_status()
            results[name]=reply.json()
            print(name,results[name]['status'],flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
