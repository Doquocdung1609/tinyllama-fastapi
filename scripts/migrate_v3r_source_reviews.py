"""Carry audited prior reviews only for identical raw-PDF cells;never certify new OCR."""
import argparse,json,hashlib,sqlite3,sys
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.product.derived_workspace import DerivedPdfWorkspace
from app.product.analysis import FactReview,review_fact,eligible_facts


def migrate(root,parents,output):
    output=Path(output)
    if output.exists():raise ValueError('NEW_REVIEW_CONTINUITY_RESULT_REQUIRED')
    w=DerivedPdfWorkspace(Path(root));events=[];seen=set()
    try:
        for parent in parents:
            database=Path(parent,'index.sqlite3').resolve();wal=Path(str(database)+'-wal')
            if wal.exists() and wal.stat().st_size:raise ValueError('STOP_PARENT_FIRST')
            with sqlite3.connect(database.as_uri()+'?immutable=1',uri=True) as db:
                rows=db.execute('SELECT payload FROM reviewed_facts').fetchall()
                for (raw,) in rows:
                    old=json.loads(raw)
                    if old['audit_hash'] in seen:continue
                    seen.add(old['audit_hash']);body={k:v for k,v in old.items() if k!='audit_hash'}
                    digest=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                    stored=db.execute('SELECT payload FROM fact_review_history WHERE event_hash=?',(digest,)).fetchone()
                    if digest!=old['audit_hash'] or not stored or json.loads(stored[0])!=old:raise ValueError('PARENT_SOURCE_REVIEW_AUDIT_INVALID')
                    doc=w.document(old['document_id']);event={'parent_review_hash':digest,'document_id':old['document_id'],'status':'NOT_CARRIED'}
                    if not doc or doc['sha256']!=old['source_sha256']:
                        events.append({**event,'reason':'SOURCE_NOT_PRESENT'});continue
                    page=w.page_evidence(doc['id'],old['page']);matches=[]
                    for row in page['tables']:
                        for col,cell in enumerate(row['cells']):
                            if cell.get('box') and cell['text']==old['source_display'] and all(abs(a-b)<.01 for a,b in zip(cell['box'],old['box'])):matches.append((row,col))
                    if len(matches)!=1:
                        events.append({**event,'reason':'EXACT_CELL_IDENTITY_NOT_UNIQUE'});continue
                    row,col=matches[0];fields={k:old[k] for k in FactReview.model_fields if k in old};fields.update(row_id=row['id'],column_index=col)
                    try:new=review_fact(w,doc['id'],FactReview(**fields))
                    except ValueError as exc:
                        events.append({**event,'reason':str(exc)});continue
                    # A second immutable event records lineage,not an invented new human review.
                    new.update(review_origin='INHERITED_IDENTICAL_RAW_PDF_CELL_REVIEW',parent_review_audit_hash=digest,
                        financial_evidence_status='FINANCIAL_EVIDENCE_REVIEWED',review_scope='SINGLE_PREVIOUSLY_REVIEWED_CELL_ONLY')
                    body={k:v for k,v in new.items() if k!='audit_hash'};new['audit_hash']=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest();encoded=json.dumps(new,ensure_ascii=False)
                    with closing(w._connect()) as current,current:
                        current.execute('INSERT OR IGNORE INTO fact_review_history VALUES(?,?,?)',(new['audit_hash'],new['id'],encoded))
                        current.execute('UPDATE reviewed_facts SET payload=? WHERE id=?',(encoded,new['id']))
                    events.append({**event,'status':'CARRIED_EXACT_AUDIT_LINEAGE','new_review_hash':new['audit_hash'],'row_id':row['id'],'column_index':col,'source_sha256':doc['sha256']})
        for doc_id in {e['document_id'] for e in events if e['status']=='CARRIED_EXACT_AUDIT_LINEAGE'}:eligible_facts(w,[doc_id])
        output.write_text(json.dumps({'events':events,'limits':'No new OCR cell was auto-reviewed.Only exact prior source-image/cell/format/box identity plus current header/scope/unit validation can inherit a local audited review.Not independent human adjudication.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Exact inherited review records',sum(e['status']=='CARRIED_EXACT_AUDIT_LINEAGE' for e in events),'/',len(events))
    finally:w.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--parent',action='append',required=True);p.add_argument('--output',required=True);a=p.parse_args();migrate(a.root,a.parent,a.output)
