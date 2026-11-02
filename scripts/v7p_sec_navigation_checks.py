"""Live shared Search/QA resolver and restart-reference checks, no embeddings."""
import json
from pathlib import Path
import requests

def main():
    s=requests.Session();s.headers['Authorization']='Bearer '+Path('tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip();base='http://127.0.0.1:18110/studio';records=[]
    old=json.loads(Path('tmp/topic3/a7-before-restart.json').read_text())['reference']
    r=s.post(base+'/sec/evidence',json={'reference':old},timeout=120);r.raise_for_status();v=r.json()
    assert v['selected_cell']['raw_value']=='109,384';records.append({'case':'REFERENCE_VALID_AFTER_REAL_WINDOWS_LAUNCHER_RESTART','status':r.status_code,'source_sha256':v['source_sha256'],'pass':True})
    for profile in ('baseline','production_v3'):
        r=s.post(base+'/query',json={'query':'HD total assets','source':'US_SEC','issuer':'HD','mode':'bm25','top_k':1,'search_profile':profile},timeout=120);r.raise_for_status();found=r.json()
        hit=found['results'][0];r=s.post(base+'/sec/evidence',json={'reference':hit['source_reference']},timeout=120);r.raise_for_status();view=r.json()
        assert view['parent_id']==hit['chunk_id'] and view['source_sha256']==hit['source_sha256'] and view['selected_cell'] is None
        records.append({'case':'SEARCH_'+profile,'status':r.status_code,'parent_id':view['parent_id'],'source_sha256':view['source_sha256'],'view_status':view['status'],'no_unrequested_numeric_verification':True,'pass':True})
    r=s.post(base+'/sec/analysis',json={'question':'What were PG net sales for the three months ended September 30, 2026?','ticker':'PG'},timeout=120);r.raise_for_status();answer=r.json()
    assert answer['status']=='SUPPORTED' and answer['citations']
    r=s.post(base+'/sec/evidence',json={'reference':answer['citations'][0]['source_reference']},timeout=120);r.raise_for_status();view=r.json()
    assert view['selected_cell']['period_end']=='2026-09-30' and view['selected_cell']['row_label'].casefold()=='net sales'
    records.append({'case':'PG_NET_SALES_SOURCE_VIEW','http_status':r.status_code,'pass':True,'response':view})
    Path('docs/topic3_v7p/V7P_A7_ADDITIONAL_HTTP.json').write_text(json.dumps({'passed':len(records),'cases':records},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':len(records),'pg_value':view['selected_cell']['raw_value'],'pg_raw_sha256':view['source_sha256']}))

if __name__=='__main__':main()
