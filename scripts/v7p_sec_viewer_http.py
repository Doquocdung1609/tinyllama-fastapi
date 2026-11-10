"""Actual authenticated SEC viewer HTTP and clone-only fault injection."""
import argparse,json,os,secrets,shutil,sqlite3,subprocess,sys,time
from pathlib import Path
from hashlib import sha256
import requests
from app.product.sec_search import SecResearchIndex
from app.product.sec_viewer import reference,server_key,decode_reference

PARENT='fin_9fadb8b8f3b78592782f972a63a9e7ed'
RAW='3d638bc025ef9643317d539f63c3891c8db9b47e35a8edd8040928704d0703f1'
QUESTION='What were HD total assets as of August 2, 2026?'


def main():
    p=argparse.ArgumentParser();p.add_argument('--sec-root',type=Path,required=True);p.add_argument('--vector-root',type=Path,required=True);args=p.parse_args()
    root=Path.cwd().resolve();source=args.sec_root.resolve();vectors=args.vector_root.resolve()
    s=requests.Session();s.headers['Authorization']='Bearer '+Path('tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    base='http://127.0.0.1:18110/studio';records=[]
    answer=s.post(base+'/sec/analysis',json={'question':QUESTION,'ticker':'HD'},timeout=120);answer.raise_for_status();answer=answer.json()
    assert answer['status']=='SUPPORTED' and answer['values']==['109384000000']
    r=s.post(base+'/sec/evidence',json={'reference':answer['citations'][0]['source_reference']},timeout=120);r.raise_for_status();control=r.json()
    assert control['status']=='VERIFIED_LOCAL_SEC_SNAPSHOT' and control['source_sha256']==RAW
    assert control['selected_cell']['raw_value']=='109,384' and control['selected_cell']['period_end']=='2026-08-02'
    records.append({'case':'SEC-01','http':r.status_code,'pass':True,'response':control})
    assert requests.post(base+'/sec/evidence',json={'reference':'not-authorized'},timeout=15).status_code==401
    # Only bounded necessary snapshot files; no accepted Qdrant collection copied/opened.
    files=[f for name in ('raw','structured','chunks','frozen_v1') for f in (source/name).rglob('*') if f.is_file()]
    size=sum(f.stat().st_size for f in files)+(source/'lexical_v1.sqlite3').stat().st_size
    assert size<100_000_000 and shutil.disk_usage(root).free>size+128*1024**2
    clone=root/'tmp/topic3'/('a7-source-faults-'+secrets.token_hex(4));assert clone.is_relative_to(root/'tmp/topic3');clone.mkdir()
    sec=clone/'sec';sec.mkdir();vec=clone/'vectors';vec.mkdir()
    for f in files:
        target=sec/f.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
    shutil.copyfile(source/'ownership.json',sec/'ownership.json');shutil.copyfile(vectors/'generation_manifest.json',vec/'generation_manifest.json')
    with sqlite3.connect((source/'lexical_v1.sqlite3').as_uri()+'?mode=ro',uri=True) as original,sqlite3.connect(sec/'lexical_v1.sqlite3') as copied:original.backup(copied)
    with sqlite3.connect(sec/'lexical_v1.sqlite3') as db:
        for cid,generation,text in db.execute('SELECT cid,generation,source FROM members').fetchall():
            f=json.loads(text)
            for k in ('raw_path','structured_path','chunks_path'):f[k]=str(sec/Path(f[k]).resolve().relative_to(source))
            db.execute('UPDATE members SET source=? WHERE cid=? AND generation=?',(json.dumps(f),cid,generation))
    token=secrets.token_urlsafe(32);env=os.environ.copy();env.update(STUDIO_API_TOKEN=token,STUDIO_WORKSPACE_DIR=str(clone/'workspace'),STUDIO_SEC_RESEARCH_ROOT=str(sec),STUDIO_SEC_VECTOR_ROOT=str(vec),TOPIC3_RESEARCH_ROOT=str(sec))
    for key,name in [('QDRANT_PATH','legacy-qdrant'),('UPLOAD_DIR','uploads'),('PROCESSED_DIR','processed'),('FINANCIAL_CORPUS_DIR','legacy-corpus')]:env[key]=str(clone/name)
    env['CONVERSATION_DB']=str(clone/'conversations.sqlite3');env['FINANCIAL_REGISTRY_DB']=str(clone/'legacy-corpus/registry.sqlite3')
    client=requests.Session();client.headers['Authorization']='Bearer '+token;test='http://127.0.0.1:18112/studio'
    log=(clone/'api.log').open('w');process=subprocess.Popen([sys.executable,'-m','uvicorn','main:app','--host','127.0.0.1','--port','18112'],env=env,stdout=log,stderr=log)
    try:
        for _ in range(60):
            try:
                if client.get('http://127.0.0.1:18112/health',timeout=2).status_code==200:break
            except requests.RequestException:pass
            time.sleep(.5)
        a=client.post(test+'/sec/analysis',json={'question':QUESTION,'ticker':'HD'},timeout=120);a.raise_for_status();a=a.json()
        ref=a['citations'][0]['source_reference'];observed=a['source_cells'][0]
        def check(name,ref=ref,expected=None):
            r=client.post(test+'/sec/evidence',json={'reference':ref},timeout=120);body=r.json()
            if expected:assert r.status_code==409 and body=={'detail':{'code':expected}},(name,r.status_code,body)
            else:assert r.status_code==200 and body['status']=='VERIFIED_LOCAL_SEC_SNAPSHOT'
            records.append({'case':name,'http':r.status_code,'response':body if expected else {'status':body['status'],'raw_sha256':body['source_sha256']},'pass':True})
        check('CLONE_UNTAMPERED_CONTROL')
        index=SecResearchIndex(sec,vec,sec);frozen=index.by_id[PARENT]['frozen'];path=Path(frozen['raw_path']);assert path.resolve().is_relative_to(clone)
        original=path.read_bytes()
        try:path.write_bytes(original+b'\n<!-- isolated tamper -->');check('SEC-03_RAW_TAMPER',''+ref,'SOURCE_HASH_MISMATCH')
        finally:path.write_bytes(original)
        check('RESTORED_CONTROL')
        key=server_key(clone/'workspace')
        for name,change in [('SEC-04_WRONG_PERIOD',{'period_end':'2025-08-02'}),('SEC-05_WRONG_LOCATOR',{'column':999})]:
            bad=reference(index,PARENT,key,{**observed,**change});check(name,bad,'SOURCE_LOCATOR_UNRESOLVED')
        other=next(cid for cid,item in index.by_id.items() if item['chunk'].filing_id!=observed['filing_id'])
        data=decode_reference(ref,key);data.update(parent_id=other,raw_hash=index.by_id[other]['frozen']['raw_hash'])
        import base64,hmac
        encoded=base64.urlsafe_b64encode(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).decode().rstrip('=')
        check('SEC-04_WRONG_FILING',encoded+'.'+hmac.new(key.encode(),encoded.encode(),sha256).hexdigest(),'SOURCE_LOCATOR_UNRESOLVED')
        hidden=path.with_name(path.name+'.isolated-missing')
        try:path.rename(hidden);check('SEC-06_SOURCE_MISSING',ref,'SOURCE_BYTES_NOT_AVAILABLE')
        finally:hidden.rename(path)
        manifest=vec/'generation_manifest.json';saved=manifest.read_bytes()
        try:
            value=json.loads(saved);value['state']='FAILED';manifest.write_text(json.dumps(value));check('FAILED_GENERATION',ref,'SOURCE_GENERATION_MISMATCH')
        finally:manifest.write_bytes(saved)
        for name,payload in [('ARBITRARY_PATH',{'reference':ref,'path':'../../outside'}),('ARBITRARY_URL',{'reference':ref,'url':'https://example.invalid'}),('OVERSIZE',{'reference':'x'*5000})]:
            r=client.post(test+'/sec/evidence',json=payload,timeout=15);assert r.status_code==422;records.append({'case':name,'http':422,'pass':True})
        check('FINAL_RESTORED_CONTROL');index.close()
        assert sha256(path.read_bytes()).hexdigest()==RAW
    finally:
        process.terminate();process.wait(timeout=15);log.close()
    output={'version':'v7p-a7-live-http/v1','source':{'issuer':control['issuer'],'accession':control['accession'],'raw_sha256':RAW,'normalized_sha256':control['normalized_sha256'],'source_relative_path':str(path.relative_to(sec)),'generation':control['generation'],'manifest_hash':control['manifest_hash']},'control':control,'cases':records,'copied_bytes':size,'fault_environment':'new bounded clone; isolated Uvicorn18112; no original source mutation','passed':len(records),'original_source_unchanged':sha256((source/path.relative_to(sec)).read_bytes()).hexdigest()==RAW}
    Path('docs/topic3_v7p/V7P_REAL_SEC_VIEWER_HTTP_RESULTS.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':len(records),'copied_bytes':size,'original_source_unchanged':output['original_source_unchanged']}))

if __name__=='__main__':main()
