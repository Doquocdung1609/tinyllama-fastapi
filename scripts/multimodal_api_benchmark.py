"""Upload synthetic PDF fixtures and run the bound T01-T20 real API benchmark."""
from __future__ import annotations
import csv,json,re,sys,time,unicodedata
from pathlib import Path
import requests
sys.stdout.reconfigure(encoding='utf-8')
API='http://127.0.0.1:8002'; ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/'tests'/'fixtures'/'pdfs'; REPORT=ROOT/'reports'; MAP=REPORT/'multimodal_fixture_documents.json'
FIXTURES=['A_text_only_vi.pdf','B_mixed_text_table.pdf','C_financial_statement.pdf','D_bar_line_charts.pdf','E_pie_chart.pdf','F_process_diagram.pdf','G_scanned_document.pdf','H_multi_column.pdf','I_multipage_table.pdf','J_mixed_vi_en.pdf']
CASES=[
 ('T01','B_mixed_text_table.pdf','Trong bảng doanh thu kiểm thử, năm nào có giá trị cao nhất?',['2024','125'],1,'table','supported'),
 ('T02','B_mixed_text_table.pdf','Tính tốc độ tăng trưởng doanh thu từ năm 2023 đến năm 2024 trong bảng.',['25%'],1,'table','supported'),
 ('T03','B_mixed_text_table.pdf','So sánh lợi nhuận năm 2023 và 2024 trong bảng số liệu.',['12','16','2024'],1,'table','supported'),
 ('T04','C_financial_statement.pdf','Trong năm 2024, chỉ tiêu nào trong bảng có giá trị lớn nhất?',['Tổng tài sản','1.400'],1,'table','supported'),
 ('T05','D_bar_line_charts.pdf','Biểu đồ cột doanh thu thể hiện xu hướng tăng hay giảm qua các năm?',['tăng','2022','2024'],1,'chart','supported'),
 ('T06','D_bar_line_charts.pdf','Nhận xét sự khác biệt giữa Chuỗi A và Chuỗi B trên biểu đồ đường.',['Chuỗi A','tăng','Chuỗi B','giảm'],2,'chart','supported'),
 ('T07','E_pie_chart.pdf','Nhóm nào chiếm tỷ trọng cao nhất trong biểu đồ tròn?',['Cá nhân','50%'],1,'chart','supported'),
 ('T08','F_process_diagram.pdf','Giải thích quy trình được thể hiện trong sơ đồ theo đúng thứ tự.',['Tiếp nhận hồ sơ','Thẩm định','Phê duyệt','Giải ngân'],1,'figure','supported'),
 ('T09','B_mixed_text_table.pdf','Tổng hợp thông tin ở bảng và đoạn văn giải thích ngay bên dưới.',['doanh thu','lợi nhuận','tăng'],1,'table','supported'),
 ('T10','I_multipage_table.pdf','Trong bảng kéo dài qua hai trang, mã A30 có giá trị bao nhiêu và ở trang nào?',['A30','300','trang 2'],2,'table','supported'),
 ('T11','G_scanned_document.pdf','Trích xuất doanh thu và lợi nhuận năm 2024 từ bảng trong PDF scan.',['không cung cấp đủ thông tin'],1,'ocr_text','blocked'),
 ('T12','C_financial_statement.pdf','Tính tỷ lệ thanh toán hiện hành năm 2024 từ tài sản ngắn hạn và nợ ngắn hạn.',['2'],1,'table','supported'),
 ('T13','D_bar_line_charts.pdf','Nếu không dùng giá trị ước lượng từ chiều cao cột, hãy cho biết xu hướng chung của doanh thu.',['tăng'],1,'chart','supported'),
 ('T14','D_bar_line_charts.pdf','Đối chiếu nhãn số doanh thu năm 2024 với biểu đồ cột cùng trang.',['2024','125'],1,'chart','supported'),
 ('T15','C_financial_statement.pdf','Vốn chủ sở hữu năm 2024 là bao nhiêu?',['không cung cấp'],1,'table','unsupported'),
 ('T16','J_mixed_vi_en.pdf','Đọc đúng đơn vị của Revenue và Margin trong bảng song ngữ.',['USD million','percent'],1,'table','supported'),
 ('T17','C_financial_statement.pdf','Điều chỉnh giảm năm 2024 là số âm hay số dương, và giá trị bao nhiêu?',['âm','30'],1,'table','supported'),
 ('T18','D_bar_line_charts.pdf','Trong biểu đồ nhiều chuỗi, giá trị Chuỗi A năm 2024 là bao nhiêu?',['Chuỗi A','120'],2,'chart','supported'),
 ('T19','C_financial_statement.pdf','Hãy chỉ ra nguồn trang và vùng bảng hỗ trợ giá trị Tổng nợ năm 2024.',['550','trang 1'],1,'table','supported'),
 ('T20','B_mixed_text_table.pdf','Kết hợp đoạn văn và bảng để nhận xét doanh thu và lợi nhuận giai đoạn 2023-2024.',['doanh thu','lợi nhuận','tăng'],1,'table','partial'),
]
def norm(s):
 s=unicodedata.normalize('NFKD',s.casefold().replace('đ','d'));s=''.join(c for c in s if not unicodedata.combining(c));return re.sub(r'\s+',' ',s)
def match(answer,expected): return all(norm(x) in norm(answer) for x in expected)
def upload_all():
 mapping={}
 for name in FIXTURES:
  with (FIX/name).open('rb') as f:
   r=requests.post(API+'/documents/upload',files={'file':(name,f,'application/pdf')},timeout=600)
  r.raise_for_status(); doc=r.json(); did=doc['document_id']
  for _ in range(240):
   detail=requests.get(f'{API}/documents/{did}',timeout=30).json()
   if detail.get('status') in ('READY','FAILED','ERROR'): break
   time.sleep(.5)
  mapping[name]={'document_id':did,'detail':detail}
  print('UPLOAD',name,detail.get('status'),detail.get('chunks'),detail.get('modality_summary'),flush=True)
 MAP.write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
 return mapping
def main():
 requests.get(API+'/health',timeout=10).raise_for_status()
 mapping=upload_all()
 rows=[]; details=[]
 for cid,name,q,expected,page,modality,support in CASES:
  did=mapping[name]['document_id']; payload={'question':q,'top_k':5,'score_threshold':.55,'document_id':did,'generate_answer':True}
  started=time.perf_counter(); res=requests.post(API+'/rag/query',json=payload,timeout=360); elapsed=time.perf_counter()-started
  res.raise_for_status(); data=res.json(); answer=data.get('answer','')
  supporting=data.get('supporting_sources',[]); included=data.get('included_prompt_context',[])
  source_match=any(x.get('document_id')==did and int(x.get('page',0))==page for x in supporting)
  modality_match=any((x.get('modality') or 'text')==modality for x in included)
  limitation='không cung cấp' in answer.casefold() or 'không đủ' in answer.casefold()
  if support=='blocked': correct=limitation and mapping[name]['detail'].get('modality_summary',{}).get('ocr_status')=='BLOCKED_ENGINE_UNAVAILABLE'
  elif support=='unsupported': correct=limitation
  else: correct=match(answer,expected) and not limitation
  citation_ok=(not supporting if support in ('blocked','unsupported') else source_match)
  cv=data.get('calculation_validation') or {}
  row={'test_id':cid,'fixture':name,'document_id':did,'page':page,'expected_modality':modality,'support_status':support,
       'ground_truth':' | '.join(expected),'answer_correct':correct,'citation_correct':citation_ok,'modality_in_prompt':modality_match,
       'supporting_pages':','.join(str(x.get('page')) for x in supporting),'supporting_modalities':','.join(str(x.get('modality')) for x in supporting),
       'source_ids':','.join(str(x.get('source_id')) for x in supporting),'bbox_present':any(x.get('bbox') for x in supporting),
       'calculation_verified':bool(cv.get('verified')),'total_ms':data.get('timings',{}).get('total_ms',round(elapsed*1000,1)),
       'generation_ms':data.get('timings',{}).get('generation_ms',0),'status':'PASS' if correct and citation_ok and (modality_match or support in ('blocked','unsupported')) else ('BLOCKED' if support=='blocked' else 'FAIL'),
       'answer':answer.replace('\n',' ')[:1800]}
  rows.append(row)
  details.append({'case':{'id':cid,'fixture':name,'question':q,'expected':expected,'page':page,'modality':modality,'support':support},'request':payload,
                  'result':row,'selected_evidence':data.get('selected_evidence',[]),'included_prompt_context':included,
                  'claim_grounding':data.get('claim_grounding',{}),'calculation_validation':cv,'citation_validation':data.get('citation_validation',{}),'timings':data.get('timings',{})})
  with (REPORT/'multimodal_rag_benchmark.csv').open('w',newline='',encoding='utf-8-sig') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  (REPORT/'multimodal_rag_benchmark_details.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
  print(cid,row['status'],round(elapsed,1),answer[:100].replace('\n',' '),flush=True)
 return 0
if __name__=='__main__': raise SystemExit(main())
