"""HTTP negatives on explicitly source-derived test PDFs, never original bytes."""
import argparse,json,time,hashlib
from pathlib import Path
import pymupdf,requests

def main():
    p=argparse.ArgumentParser();p.add_argument('--apple',type=Path,required=True);args=p.parse_args()
    s=requests.Session();s.headers['Authorization']='Bearer '+Path('tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    base='http://127.0.0.1:18110/studio';records=[]
    original=args.apple
    assert hashlib.sha256(original.read_bytes()).hexdigest()=='3eb270b22acb7d8d8e9c32a43dc221dec3345f8e4bca02755fdbc1ee16c823de'
    for kind in ['UNKNOWN_CURRENCY','UNKNOWN_SCOPE','MIXED_UNVERIFIED_PERIOD']:
        with pymupdf.open(original) as source:
            test=pymupdf.open();test.insert_pdf(source,from_page=0,to_page=0);test.insert_pdf(source,from_page=31,to_page=31)
        # Deliberately omit source p30 presentation-currency declaration. Dollar
        # signs and issuer nationality must not authenticate USD.
        if kind=='UNKNOWN_SCOPE':
            page=test[1]
            for rect in page.search_for('CONSOLIDATED STATEMENTS OF OPERATIONS'):page.add_redact_annot(rect,fill=(1,1,1))
            page.apply_redactions();page.insert_text((40,30),'USD in millions')
        raw=test.tobytes();test.close()
        upload=s.post(base+'/documents',files={'file':('source-derived-negative-'+kind+'.pdf',raw,'application/pdf')},timeout=30)
        assert upload.status_code==202;doc=upload.json()
        for _ in range(120):
            doc=s.get(base+'/documents/'+doc['id'],timeout=10).json()
            if doc['status'] in {'READY','FAILED'}:break
            time.sleep(1)
        assert doc['status']=='READY',doc.get('error_code')
        q='Net income growth fiscal 2024 to 2025?' if kind=='MIXED_UNVERIFIED_PERIOD' else 'Net income fiscal 2025?'
        r=s.post(base+'/chat',json={'question':q,'document_ids':[doc['id']]},timeout=120);answer=r.json()
        assert r.status_code==200 and answer.get('status')!='SUPPORTED' and not answer.get('values')
        deleted=s.delete(base+'/documents/'+doc['id'],params={'confirm':doc['id']},timeout=20)
        assert deleted.status_code==200
        records.append({'case':kind,'label':'SOURCE_DERIVED_NEGATIVE_FIXTURE_NOT_ORIGINAL_FILING','source_sha256':hashlib.sha256(raw).hexdigest(),'http_status':r.status_code,'response':answer,'removed_only_new_fixture':True,'pass':True})
    Path('docs/topic3_v7p/V7P_SOURCE_BOUNDARY_HTTP.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':len(records)}))

if __name__=='__main__':main()
