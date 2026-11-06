"""Run source-bound V6 probes without writing reviewed facts."""
import argparse
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import psutil
import requests

DOC='4a92af827aaf1e73e017544d0ff20d0d'
BIDV='2bed2b3c312c8149e6a2ff6ab80c694a'
EXTRA={
 'capital_equity':'Phân biệt vốn góp của chủ sở hữu và tổng vốn chủ sở hữu tại ngày 31/12/2025.',
 'shares':'Đối chiếu vốn góp cuối 2025 với số cổ phiếu đang lưu hành và mệnh giá ở trang 20–21.',
 'income':'So sánh doanh thu bán hàng, giảm trừ, doanh thu thuần và giá vốn quý IV/2025 ở trang 5 và 22.',
 'explanation':'Đọc trang 24 và giải thích nguyên nhân lợi nhuận quý IV/2025 tăng theo công bố của công ty.',
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:18112')
    parser.add_argument('--controls',default='http://127.0.0.1:18113')
    parser.add_argument('--output',type=Path,default=Path('tmp/chat-v6/acceptance.json'))
    args=parser.parse_args()
    questions=json.loads(Path('reports/chat_v6/queries.json').read_text(encoding='utf-8-sig'))
    token=Path('tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    process_file=Path('tmp/ocr-v3-runtime/processes.json')
    records=json.loads(process_file.read_text(encoding='utf-8-sig'))['processes'] if process_file.exists() else []
    results={}
    with requests.Session() as client:
        client.headers['Authorization']='Bearer '+token
        def call(base,name,question,doc):
            start=perf_counter();key=uuid4().hex
            reply=client.post(base+'/studio/chat',json={'question':question,'document_ids':[doc],'progress_id':key},timeout=60)
            reply.raise_for_status()
            elapsed=perf_counter()-start
            progress=client.get(base+'/studio/chat/progress/'+key,timeout=15)
            progress.raise_for_status()
            rss=[]
            if base==args.url:
                for record in records:
                    try:
                        process=psutil.Process(record['pid'])
                        if 'uvicorn' in ' '.join(process.cmdline()):
                            memory=process.memory_info()
                            rss.append({'rss':memory.rss,'peak_working_set':getattr(memory,'peak_wset',None)})
                    except (psutil.NoSuchProcess,psutil.AccessDenied):
                        continue
            results[name]={'question':question,'seconds':elapsed,'answer':reply.json(),
                           'progress':progress.json(),'api_memory':rss,'system_available_ram':psutil.virtual_memory().available}
            print(name,round(elapsed,3),results[name]['answer'].get('document_coverage'),flush=True)
        for name,question in {**questions,**EXTRA}.items():
            call(args.url,name,question,DOC)
        call(args.controls,'held_out_bidv','Kiểm kê từng trang của PDF BIDV. Cho biết mục chính và tình trạng đọc của mỗi trang, có dẫn nguồn.',BIDV)
        mapping=client.get(args.url+f'/studio/documents/{DOC}/page-map',timeout=30)
        mapping.raise_for_status()
        results['page_map']=mapping.json()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
