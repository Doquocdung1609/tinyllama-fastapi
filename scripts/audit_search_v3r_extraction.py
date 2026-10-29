"""Source-image audit;never modifies PDF,old checkpoint or reviewed facts."""
import json,hashlib,sqlite3,sys,time,re,threading
from pathlib import Path
import pymupdf,psutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.product.pdf_extract_v3r import extract_page,_raster_features,_ocr_region,_reading
from app.product.pdf_extract import _lines,table_candidates,folded
import argparse
parser=argparse.ArgumentParser(description="Reproduce bounded original-image V3R development extraction audit.")
parser.add_argument('--parent',action='append',required=True)
parser.add_argument('--output',required=True)
parser.add_argument('--raw-directory',required=True)
a=parser.parse_args()
if Path(a.output).exists() or Path(a.raw_directory).exists():raise ValueError('NEW_AUDIT_OUTPUT_REQUIRED')
outdir=Path(a.raw_directory);outdir.mkdir(parents=True)
catalog=json.loads(Path('docs/search_v3/SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
catalog += [{'ticker':'HPG','sha256':'4a92af827aaf1e73e017544d0ff20d0d14ae4d368bd9c90d5d6d60a28af8b447'},
 {'ticker':'BIDV','sha256':'2bed2b3c312c8149e6a2ff6ab80c694a4c710e82f65b1c35a1a943eae4fa32a6'}]
catalog={s['ticker']:s for s in catalog};roots=a.parent
for source in catalog.values():
 matches=[Path(root,'files',source['sha256'][:32]+'.pdf') for root in roots]
 source['path']=str(next(p for p in matches if p.is_file()))

def prior(s,n):
 for root in roots:
  with sqlite3.connect(Path(root,'index.sqlite3').resolve().as_uri()+'?immutable=1',uri=True) as db:
   row=db.execute('SELECT payload,payload_hash FROM page_evidence WHERE document_id=? AND page=?',(s['sha256'][:32],n)).fetchone()
  if row:
   assert hashlib.sha256(row[0].encode()).hexdigest()==row[1]
   data=json.loads(row[0]);assert data['source_sha256']==s['sha256'];return {**data,'_parent_sha':row[1]}
 raise ValueError('Missing prior source checkpoint')
done=threading.Event();samples=[];process=psutil.Process();cpu0=process.cpu_times();childcpu={}
def sample():
 while not done.is_set():
  children=[]
  for p in process.children(recursive=True):
   try:
    c=p.cpu_times();childcpu[p.pid]=max(childcpu.get(p.pid,0),c.user+c.system);children.append(p.memory_info().rss)
   except psutil.Error:pass
  samples.append({'rss':process.memory_info().rss,'children_rss':sum(children),'available_ram':psutil.virtual_memory().available});done.wait(.2)
worker=threading.Thread(target=sample,daemon=True);worker.start();records=[];start=time.perf_counter()
try:
 for ticker,nums in [('HPG',[3,5]),('BIDV',[3,6]),('CEO',[2,4]),('FOX',[3,5]),('SAMSUNG',[6,9]),('REE',[3]),('SEM',[7,8,9])]:
  s=catalog[ticker];raw=Path(s['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==s['sha256']
  with pymupdf.open(s['path']) as pdf:
   for n in nums:
    old=prior(s,n);result=extract_page(pdf[n-1],n,old);result['source_sha256']=s['sha256'];raw=(json.dumps(result,ensure_ascii=False,sort_keys=True)+'\n').encode();(outdir/f'{ticker}-p{n}.json').write_bytes(raw)
    row={'ticker':ticker,'page':n,'source_sha256':s['sha256'],'derived_checkpoint_sha256':hashlib.sha256(raw).hexdigest(),'regions':[{k:r.get(k) for k in ['id','box','kind','status','ocr_words']} for r in result['regions']],
     'coverage_status':result['extraction_coverage_status'],'warnings':result['coverage_warnings'],'elapsed_ms':result['timings_ms']['region_extraction'],'candidate_rows':len(result['tables']),
     'source_coordinate_boxes_in_page':all(0<=w['box'][0]<=w['box'][2]<=result['width']+1 and 0<=w['box'][1]<=w['box'][3]<=result['height']+1 for l in result['lines'] for w in l['words']),
     'native_words':result['fusion']['native_words'],'ocr_or_prior_words':result['fusion']['ocr_or_prior_words'],'duplicates_merged':result['fusion']['duplicates_merged'],
     'reviewed_cells':sum(c.get('verification')=='REVIEWED' for r in result['tables'] for c in r['cells'])}
    records.append(row);print(ticker,n,row['candidate_rows'],round(row['elapsed_ms']),row['coverage_status'],flush=True)
 refs=[q['relevant'][0] for q in map(json.loads,Path('docs/search_v3/SEARCH_V3_QRELS.jsonl').read_text(encoding='utf-8').splitlines()) if q['id'].startswith('v3f') and len(q['relevant'])==1 and q['relevant'][0].get('metric') and q['relevant'][0]['source_sha256']==catalog['SEM']['sha256']]
 checked=[];windows={'assets':(355,378),'cash_equivalents':(132,151),'inventory':(200,220),'liabilities':(315,335),'equity':(418,436),'pretax_income':(225,244),'net_income':(286,305)}
 for ref in refs:
  p=json.loads((outdir/f"SEM-p{ref['page']}.json").read_text(encoding='utf-8'));matches=[];digits=re.sub(r'\D','',ref['expected_display'])
  for row in p['tables']:
   for cell in row['cells']:
    if re.sub(r'\D','',cell['text'])!=digits:continue
    b=cell.get('box');year=cell.get('period_year_candidate');currency=cell.get('currency_candidate');y0,y1=windows[ref['metric']]
    checks={'value_digits':True,'label_matches_original':folded(ref['span']) in folded(row['row_label']),
     'current_year_column':bool(year and year['text']=='2025'),'currency_KRW':bool(currency and currency['unit']=='KRW'),
     'source_cell_window':bool(b and 285<=b[0]<=b[2]<=345 and y0<=b[1]<=b[3]<=y1),
     'unreviewed':cell['financial_evidence_status']=='FINANCIAL_EVIDENCE_REVIEW_PENDING'}
    matches.append({'raw':cell['text'],'source_display':ref['expected_display'],'row_label':row['row_label'],'row_id':row['id'],'column_index':cell['column_index'],'box':b,
     'confidence':cell['confidence'],'period_year_candidate':year,'currency_candidate':currency,'checks':checks,'raw_format_exact':cell['text']==ref['expected_display']})
  checked.append({'metric':ref['metric'],'page':ref['page'],'matches':matches,'status':'PASS_BOUNDED' if any(all(c['checks'].values()) for c in matches) else 'FAIL'})
 negatives=[]
 for ticker,n,box,name in [('FOX',1,[100,10,180,95],'company_logo'),('CEO',3,[350,595,500,710],'corporate_stamp'),('CEO',3,[85,655,250,745],'signature')]:
  s=catalog[ticker]
  with pymupdf.open(s['path']) as pdf:
   page=pdf[n-1];rect=pymupdf.Rect(box);features=_raster_features(page,rect,[]);rows=[]
   if features['text_like']:
    words,engine=_ocr_region(page,rect,'vie+eng')
    for w in words:
     b=_reading(w['box'],engine['correction_clockwise'],page.rect.width,page.rect.height);w.update(rx=b[0],ry=b[1],rw=b[2]-b[0],rh=b[3]-b[1])
    rows=table_candidates(_lines(words),n,engine['correction_clockwise'])
   financial=[r for r in rows if sum(bool(c['text']) for c in r['cells'])>=2]
   negatives.append({'source_sha256':s['sha256'],'page':n,'box':box,'case':name,'text_like':features['text_like'],'financial_candidate':len(financial)>=3,'status':'PASS' if len(financial)<3 else 'FAIL'})
finally:
 done.set();worker.join(timeout=2)
cpu1=process.cpu_times()
report={'annotation_status':'PROVISIONAL_AGENT_ANNOTATED_NOT_INDEPENDENT_HUMAN_REVIEW','source_pages':records,'SEM_seven_checked_cells':checked,'negative_regions':negatives,
 'gate_B_D':'PASS_BOUNDED' if all(r['status']=='PASS_BOUNDED' for r in checked) and all(r['status']=='PASS' for r in negatives) else 'PARTIAL',
 'resources':{'elapsed_s':time.perf_counter()-start,'parent_peak_rss':max(r['rss'] for r in samples),'parent_plus_ocr_peak_rss':max(r['rss']+r['children_rss'] for r in samples),
 'minimum_free_ram':min(r['available_ram'] for r in samples),'parent_cpu_s':cpu1.user+cpu1.system-cpu0.user-cpu0.system,'sampled_child_cpu_s_lower_bound':sum(childcpu.values()),'extractor_gpu_used':False},
 'limits':'Digit-equivalent OCR candidates are source/row/year/currency/window checked. Raw separators are not silently corrected;no numeric cell becomes REVIEWED. Source windows manually checked on original images;no independent human review.'}
Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('GATE',report['gate_B_D'],[(r['metric'],r['status']) for r in checked],flush=True)
