"""Live source-bound fixture checks. Requires an isolated clone and reviewed owner sources."""
from pathlib import Path
import sys,json,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.product.derived_workspace import DerivedPdfWorkspace as PdfWorkspace
from app.product.search_v3r import FinancialSearchV3R as FinancialSearchV2
from app.product.analysis import AnalysisRequest,numeric_answer
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if not (args.root/'derived-generation.json').exists():raise ValueError('EXPERIMENT_CLONE_REQUIRED')
if args.output.exists():raise ValueError('OUTPUT_ALREADY_EXISTS')
w=PdfWorkspace(args.root);v=FinancialSearchV2(w,args.root/'v3r-owner-fixture-sidecar')
h='4a92af827aaf1e73e017544d0ff20d0d';b='2bed2b3c312c8149e6a2ff6ab80c694a'
cases=[
 (h,'Tổng tài sản công ty mẹ Hòa Phát ngày 31/12/2025',{'metric':'assets','period':'2025-12-31','statement_scope':'SEPARATE','unit':'VND'}),
 (h,'Tổng tài sản công ty mẹ Hòa Phát ngày 01/01/2025',{'metric':'assets','period':'2025-01-01','statement_scope':'SEPARATE','unit':'VND'}),
 (h,'Nợ phải trả công ty mẹ Hòa Phát ngày 31/12/2025',{'metric':'liabilities','period':'2025-12-31','statement_scope':'SEPARATE','unit':'VND'}),
 (h,'Vốn chủ sở hữu công ty mẹ Hòa Phát ngày 31/12/2025',{'metric':'equity','period':'2025-12-31','statement_scope':'SEPARATE','unit':'VND'}),
 (b,'Tổng tài sản hợp nhất BIDV số trình bày lại ngày 31/12/2024',{'metric':'assets','period':'2024-12-31','statement_scope':'CONSOLIDATED','basis':'RESTATED','unit':'TRIEU_VND'}),
 (b,'Tổng tài sản hợp nhất BIDV số đã công bố ngày 31/12/2024',{'metric':'assets','period':'2024-12-31','statement_scope':'CONSOLIDATED','basis':'ORIGINAL','unit':'TRIEU_VND'}),
 (b,'Tổng tài sản hợp nhất BIDV mức điều chỉnh ngày 31/12/2024',{'metric':'assets','period':'2024-12-31','statement_scope':'CONSOLIDATED','basis':'ADJUSTMENT','unit':'TRIEU_VND'}),
 (h,'Tổng tài sản riêng HPG năm 2031',None),(h,'Tổng tài sản hợp nhất HPG năm 2025',None),
 (h,'Tổng tài sản BIDV ngày 31/12/2024',None),(b,'Tổng tài sản BIDV năm 2024',None),
 (b,'Tổng tài sản hợp nhất BIDV năm 2024',None),(h,'Tổng tài sản riêng HPG năm 2025',None),
 (h,'Rủi ro phải thu khó đòi và dự phòng',None),(h,'Tổng tài sản của ACME ngày 31/12/2025',None),
 (h,'Total assets of Apple separate as of 31/12/2025',None),
 (h,'total assets of missing company separate as of 31/12/2025',None)]
out=[]
try:
 for doc,q,expected in cases:
  result=v.search(q,'bm25',5,[doc]);facts=[f for hit in result['results'] if hit['numeric_answer_eligible'] for f in hit['reviewed_facts']]
  correct=bool(facts) and all(all(f[k]==value for k,value in expected.items()) for f in facts) if expected else not facts
  out.append({'query':q,'expected':expected,'status':'PASS' if correct else 'FAIL','claimed_facts':[{k:f[k] for k in ['metric','period','statement_scope','basis','unit','source_display','source_sha256','audit_hash']} for f in facts],'evidence_status':result['evidence_status'],'reason':result.get('reason')})
 numeric=[]
 for question,doc,operation,expected,overrides in [
  ('Tổng tài sản công ty mẹ Hòa Phát tăng bao nhiêu so với đầu năm 2025?',h,'ABS_CHANGE','16877702175961',{}),
  ('Kiểm tra tổng tài sản hợp nhất BIDV: số đã công bố cộng điều chỉnh có khớp số trình bày lại năm 2024?',b,'RESTATEMENT_CHECK','0',{'current_period':'2024-12-31','statement_scope':'CONSOLIDATED'}),
  ('Tổng tài sản công ty mẹ Hòa Phát năm 2031?',h,'EXTRACT',None,{})]:
  request=AnalysisRequest(question=question,document_ids=[doc],mode='numeric',operation=operation,current_period='2025-12-31',previous_period='2025-01-01',**overrides) if not overrides else AnalysisRequest(**{'question':question,'document_ids':[doc],'mode':'numeric','operation':operation,'previous_period':'2025-01-01',**overrides})
  result=numeric_answer(w,request);ok=result['values']==[expected] if expected is not None else result['status']=='INSUFFICIENT_EVIDENCE'
  numeric.append({'question':question,'status':'PASS' if ok else 'FAIL','answer_status':result['status'],'values':result['values'],'unit':result.get('unit')})
 result={'source_fact_cases':out,'numeric_cases':numeric,'metric_basis_period_correctness':sum(c['status']=='PASS' for c in out if c['expected'])/7,
  'numeric_claim_abstention_correctness':sum(c['status']=='PASS' for c in out if not c['expected'])/sum(not c['expected'] for c in out),
  'unsupported_numeric_answer_rate':sum(bool(c['claimed_facts']) for c in out if not c['expected'])/sum(not c['expected'] for c in out),
  'scope':'17 bounded real-source guard cases,7 reviewed gold cells; separate from retrieval Recall and not a general financial accuracy estimate.'}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print([(r['status'],r['query']) for r in out]);assert all(r['status']=='PASS' for r in out+numeric)
finally:w.close()
