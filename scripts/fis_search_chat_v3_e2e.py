"""Real source-bound Search/Chat acceptance; no mocks or research-data writes."""
import csv,json,time,argparse
from pathlib import Path
from decimal import Decimal
import requests
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/fis_search_chat_v3'
D={'BIDV':'2bed2b3c312c8149e6a2ff6ab80c694a','HPG':'4a92af827aaf1e73e017544d0ff20d0d','AAPL':'3eb270b22acb7d8d8e9c32a43dc221de'}
SEARCH={'BIDV':'Tìm dòng lợi nhuận sau thuế chưa phân phối năm 2024.','HPG':'Tìm bảng cân đối kế toán riêng HPG cuối năm 2025.','AAPL':'Greater China net sales FY2025 FY2024'}
CASES=[]
def add(doc,q,values=None,status='VERIFIED_ANSWER',thread=None,contains=None,tag=''):
 CASES.append({'id':f'C{len(CASES)+1:02}','doc':doc,'question':q,'expected_values':values,'expected_status':status,'thread':thread,'contains':contains or [],'tag':tag})
add('AAPL','Trong FY2025, khu vực kinh doanh nào của Apple giảm doanh thu so với FY2024 dù tổng doanh thu tăng? Nêu cả hai giá trị, mức giảm tuyệt đối, tỷ lệ và giải thích từ báo cáo.',['-2575','-3.85','25126','6.43'],contains=['Greater China','64.377','66.952','iPhone','Mac'],tag='MULTIPART')
add('AAPL',"I believe Apple's FY2025 Greater China net sales were $69,377 million. Can you confirm?",['64377'],contains=['incorrect','Greater China','64,377'],tag='SEMANTIC_TRAP')
add('AAPL','What percentage of FY2025 total net sales came from Services? Show values and calculation.',['26.23'])
add('AAPL','What were Services net sales in FY2025?',['109158'],thread='services')
add('AAPL','And in FY2024?',['96169'],thread='services')
add('AAPL','So how much did Services grow in absolute terms and percentage?',['12989','13.51'],thread='services',tag='MULTIPART')
add('AAPL','Are FY2025 U.S. net sales and Americas segment sales the same? Give both amounts and explain.',contains=['151,790','178,353','North and South America'],tag='MULTIPART')
add('AAPL','Compare FY2025 Services and Products gross margin percentages. Difference in percentage points?',['38.60'],contains=['75.4','36.8','38.60'],tag='MULTIPART')
add('AAPL','What were effective tax rates FY2025 and FY2024? Explain the drivers stated in the filing.',['24.1','15.6','-8.50'],contains=['State Aid Decision','24.1','15.6'],tag='MULTIPART')
add('AAPL','What are FY2026 total net sales according to the FY2025 filing selected?',[],status='REQUIRES_SOURCE_REVIEW',contains=['2026','does not verify'],tag='SEMANTIC_TRAP')
add('BIDV','Tìm dòng lợi nhuận sau thuế chưa phân phối năm 2024.',[],status='SOURCE_SUPPORTED_NON_NUMERIC',thread='bidv',contains=['4','7'])
add('BIDV','Mức điều chỉnh của riêng ngân hàng và hợp nhất khác nhau bao nhiêu? Giải thích cách tính.',['1114'],thread='bidv',tag='MULTIPART')
add('BIDV','Số đã công bố + mức điều chỉnh = số trình bày lại của riêng ngân hàng?',['0'],thread='bidv',tag='MULTIPART')
add('BIDV','Liệt kê các khoản điều chỉnh của BIDV năm 2024 theo báo cáo riêng và hợp nhất.',status='PARTIAL_VERIFIED')
add('HPG','Đây là báo cáo riêng công ty mẹ hay báo cáo hợp nhất?',[],status='SOURCE_SUPPORTED_NON_NUMERIC',contains=['riêng','công ty mẹ'])
add('HPG','Tìm bảng cân đối kế toán riêng HPG cuối năm 2025.',[],status='SOURCE_SUPPORTED_NON_NUMERIC',contains=['2'])
add('HPG','Lợi nhuận sau thuế Q4/2025 của công ty mẹ là bao nhiêu?',[],status='REQUIRES_SOURCE_REVIEW',contains=['OCR'],tag='OCR')
add('HPG','Cho số lợi nhuận sau thuế hợp nhất của tập đoàn từ báo cáo riêng này.',[],status='UNSUPPORTED_SCOPE',tag='SCOPE')
add('AAPL','Compare total net sales and net income FY2025.',['416161','112010'],tag='MULTIPART')
add('AAPL','How much did Greater China net sales grow in absolute terms and percentage FY2024 to FY2025?',['-2575','-3.85'],tag='SEMANTIC_TRAP')
add('AAPL','Explain why Services net sales grew in FY2025 compared with FY2024.',['12989'],contains=['advertising','App Store','cloud services'],tag='MULTIPART')
add('AAPL','What were total net sales FY2025 in EUR?',[],status='REQUIRES_SOURCE_REVIEW',tag='FX')
add('HPG','What were Apple total net sales FY2025?',[],status='QUERY_CONTEXT_CONFLICT',tag='WRONG_ISSUER')
add('AAPL','What were total net sales FY2025?',['416161'],thread='switch')
add('HPG','And in FY2024?',[],status='REQUIRES_SOURCE_REVIEW',thread='switch',tag='SOURCE_SWITCH')
add('AAPL','Compare Services and Products net sales FY2025.',['109158','307003'],tag='MULTIPART')

def run():
 parser=argparse.ArgumentParser();parser.add_argument('--name',default='real');parser.add_argument('--chat-only',action='store_true');parser.add_argument('--ids');args=parser.parse_args()
 session=requests.Session();session.headers['Authorization']='Bearer '+(ROOT/'tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip();records=[];threads={}
 def post(path,payload):
  t=time.perf_counter();response=session.post('http://127.0.0.1:18110/studio/'+path,json=payload,timeout=180);return response.status_code,response.json(),round((time.perf_counter()-t)*1000,2)
 if not args.chat_only:
  for doc,q in SEARCH.items():
   for method in ['bm25','dense','hybrid','faith']:
    for k in [5,10,20]:
     request={'query':q,'document_ids':[D[doc]],'source':'USER_UPLOADS','mode':method if method!='faith' else 'hybrid','search_profile':'baseline' if method!='faith' else 'faith_r_product_v1','top_k':k}
     http,r,ms=post('query',request);ids=[h.get('evidence_id',h.get('citation_id',h.get('chunk_id'))) for h in r.get('results',[])];count=len(ids)
     expected_profile=request['search_profile'];checks={'http':http==200,'requested_top_k':r.get('requested_top_k')==k,'returned_count':r.get('returned_count')==count,'max_k':count<=k,'mode':r.get('mode_executed')==request['mode'],'profile':r.get('search_profile_executed')==expected_profile,'no_duplicates':len(ids)==len(set(ids)),'honest_limit':not r.get('candidate_count') or count==k or bool(r.get('truncation_reason'))}
     if method!='faith' and (r.get('candidate_count') or 0)>=k:checks['raw_topk_count']=count==k
     if method=='faith' and doc=='BIDV':checks['source_pages']={4,7}<={h['page'] for h in r.get('results',[])}
     rec={'id':f'S{len(records)+1:02}','kind':'search','doc':doc,'request':request,'http':http,'elapsed_ms':ms,'checks':checks,'outcome':'PASS' if all(checks.values()) else 'FAIL','response':r};records.append(rec);print(rec['id'],rec['outcome'],method,k,count,r.get('candidate_count'),flush=True)
  for doc,extra in [('AAPL',{'issuer':'BIDV'}),('BIDV',{'period':'2099'}),('AAPL',{'query':'zzzz_unavailable_metric_xyz'})]:
   req={'query':SEARCH[doc],'source':'USER_UPLOADS','document_ids':[D[doc]],'mode':'bm25','search_profile':'baseline','top_k':5,**extra};http,r,ms=post('query',req);checks={'http':http==200,'empty':r.get('returned_count')==0,'no_results_status':r.get('retrieval_status')=='NO_RESULTS'};records.append({'id':f'S{len(records)+1:02}','kind':'search','doc':doc,'request':req,'http':http,'elapsed_ms':ms,'checks':checks,'outcome':'PASS' if all(checks.values()) else 'FAIL','response':r})
  probes=[
   ('valid_period',{'query':SEARCH['BIDV'],'document_ids':[D['BIDV']],'period':'2024'},lambda r:r.get('returned_count',0)>0),
   ('valid_issuer',{'query':SEARCH['BIDV'],'document_ids':[D['BIDV']],'issuer':'BIDV'},lambda r:r.get('returned_count',0)>0),
   ('scope_filter',{'query':SEARCH['BIDV'],'document_ids':[D['BIDV']],'statement_scope':'CONSOLIDATED'},lambda r:bool(r.get('results')) and all(h.get('statement_scope')=='CONSOLIDATED' for h in r['results'])),
   ('all_source_isolation',{'query':'Apple total net sales FY2025','document_ids':[],'search_profile':'faith_r_product_v1','mode':'hybrid'},lambda r:bool(r.get('results')) and {h['document_id'] for h in r['results']}=={D['AAPL']}),
   ('issuer_conflict',{'query':'Apple total net sales FY2025','document_ids':[D['HPG']],'search_profile':'faith_r_product_v1'},lambda r:r.get('retrieval_status')=='CLARIFY_SCOPE' and not r.get('results')),
   ('SEC_unavailable',{'query':'Apple total net sales FY2025','source':'US_SEC','search_profile':'faith_r_product_v1','document_ids':[]},lambda r:r.get('retrieval_status')=='SOURCE_UNAVAILABLE' and not r.get('results'))]
  for tag,extra,validate in probes:
   req={'query':SEARCH['BIDV'],'source':'USER_UPLOADS','mode':'bm25','search_profile':'baseline','top_k':5,**extra};http,r,ms=post('query',req);checks={'http':http==200,'source_semantics':validate(r)};outcome='PASS' if all(checks.values()) else 'FAIL'
   if outcome=='PASS' and tag=='SEC_unavailable':outcome='BLOCKED'
   records.append({'id':f'S{len(records)+1:02}','kind':'search','doc':tag,'request':req,'http':http,'elapsed_ms':ms,'checks':checks,'outcome':outcome,'response':r});print(records[-1]['id'],outcome,tag,flush=True)
 for c in CASES:
  if args.ids and c['id'] not in args.ids.split(','):continue
  req={'question':c['question'],'document_ids':[D[c['doc']]],'session_id':threads.get(c['thread']) if c['thread'] else None};http,r,ms=post('chat',req)
  if c['thread'] and r.get('session_id'):threads[c['thread']]=r['session_id']
  vals=r.get('values',[]);status=r.get('answer_status',r.get('status'));checks={'http':http==200,'status':status==c['expected_status'],'exact_values':c['expected_values'] is None or [Decimal(v) for v in vals]==[Decimal(v) for v in c['expected_values']],'on_topic':all(v in r.get('answer','') for v in c['contains']),'numeric_gate':not vals or r.get('independent_verification',{}).get('status')=='VERIFIED','semantic_complete':status!='VERIFIED_ANSWER' or r.get('semantic_question_coverage',{}).get('status')=='COMPLETE'}
  if c['id']=='C03':checks['actual_operands']={o['value_raw'] for o in r.get('operands',[])}=={'109,158','416,161'}
  if c['tag']=='SOURCE_SWITCH':checks['reset']=r.get('conversation_reset') is True
  outcome='PASS' if all(checks.values()) else 'FAIL'
  if outcome=='PASS' and status in {'PARTIAL_VERIFIED','REQUIRES_SOURCE_REVIEW'}:outcome='PARTIAL'
  records.append({**c,'kind':'chat','request':req,'http':http,'elapsed_ms':ms,'checks':checks,'outcome':outcome,'response':r});print(c['id'],outcome,status,vals,r.get('reason'),flush=True)
  (OUT/(args.name+'.json')).write_text(json.dumps({'mocked':False,'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
 (OUT/(args.name+'.json')).write_text(json.dumps({'mocked':False,'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
 print('TOTAL',len(records),{s:sum(r['outcome']==s for r in records) for s in ['PASS','PARTIAL','FAIL','BLOCKED']})
if __name__=='__main__':run()
