"""Additive SQLite migration for workspace-owned chat history, including legacy turns."""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from hashlib import sha256
import json

def now():return datetime.now(timezone.utc).isoformat()
def owner(w):return sha256(str(w.root.resolve()).encode()).hexdigest()

@contextmanager
def connect(w):
    with closing(w._connect()) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS financial_chat_sessions(id TEXT PRIMARY KEY,scope TEXT NOT NULL,payload TEXT NOT NULL)')
        columns={r['name'] for r in db.execute('PRAGMA table_info(financial_chat_sessions)')}
        for name,decl in {'title':"TEXT NOT NULL DEFAULT ''",'created_at':"TEXT NOT NULL DEFAULT ''",'updated_at':"TEXT NOT NULL DEFAULT ''",'document_ids':"TEXT NOT NULL DEFAULT '[]'",'owner':"TEXT NOT NULL DEFAULT ''"}.items():
            if name not in columns:db.execute(f'ALTER TABLE financial_chat_sessions ADD COLUMN {name} {decl}')
        db.execute("UPDATE financial_chat_sessions SET owner=?,created_at=CASE WHEN created_at='' THEN ? ELSE created_at END,updated_at=CASE WHEN updated_at='' THEN ? ELSE updated_at END WHERE owner=''",(owner(w),now(),now()))
        for row in db.execute("SELECT id,payload FROM financial_chat_sessions WHERE document_ids='[]'").fetchall():
            history=json.loads(row['payload'])
            docs=sorted({c['document_id'] for h in history for c in h.get('response',{}).get('citations',[]) if c.get('document_id')})
            if docs:db.execute('UPDATE financial_chat_sessions SET document_ids=? WHERE id=?',(json.dumps(docs),row['id']))
        yield db

def public(row,detail=False):
    history=json.loads(row['payload']); docs=json.loads(row['document_ids'])
    value={k:row[k] for k in ('id','title','created_at','updated_at')}
    value.update(document_ids=docs,message_count=len(history)*2)
    if not value['title']:value['title']=(history[0]['question'][:80] if history else 'Hội thoại mới')
    if detail:
        from app.product.ocr_reviewed_answer import readable_history
        turns=[];messages=[]
        for i,turn in enumerate(history):
            original=turn.get('response',{})
            response=readable_history(original)
            turns.append({**turn,'response':response} if response is not original else turn)
            saved=turn.get('messages',[
                {'id':row['id']+f':{i}:user','role':'user','text':turn['question'],'created_at':turn.get('created_at')},
                {'id':row['id']+f':{i}:assistant','role':'assistant','text':response.get('answer',''),'created_at':turn.get('created_at')}])
            messages.extend({**message,'text':response['answer']}
                            if response is not original and message.get('role')=='assistant'
                            else message for message in saved)
        value.update(turns=turns,messages=messages)
    return value

def save(w,session,scope,history,documents):
    with connect(w) as db:
        title=history[0]['question'][:80] if history else 'Hội thoại mới';stamp=now()
        db.execute('''INSERT INTO financial_chat_sessions(id,scope,payload,title,created_at,updated_at,document_ids,owner)
            VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET scope=excluded.scope,payload=excluded.payload,
            updated_at=excluded.updated_at,document_ids=excluded.document_ids''',
            (session,scope,json.dumps(history,ensure_ascii=False),title,stamp,stamp,json.dumps(documents),owner(w)))
