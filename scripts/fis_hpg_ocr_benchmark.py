"""Local HPG OCR comparison. Uses a source-image transcription for scoring."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from time import perf_counter

import pymupdf
import requests

from app.product.pdf_extract import folded, inverse_box
from app.product.pdf_ocr_financial_v2 import extract_page, reconstruct

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT/'reports/hpg_ocr/visual_gold.json'


def edits(a,b):
    previous=list(range(len(b)+1))
    for i, first in enumerate(a,1):
        current=[i]
        for j, second in enumerate(b,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(first!=second)))
        previous=current
    return previous[-1]


def matching(rows, code, label):
    if code:
        exact=[row for row in rows if row.get('item_code')==code]
        if len(exact)==1:
            return exact[0]
    ranked=sorted((edits(folded(label),folded(row['row_label']))/max(len(label),len(row['row_label']),1),i)
                  for i,row in enumerate(rows))
    return rows[ranked[0][1]] if ranked and ranked[0][0]<.39 else None


def score(page,gold):
    matched=correct=bound=cer=wer=characters=tokens=0
    comparisons=[]
    for code,label,*amounts in gold['rows']:
        row=matching(page.get('tables',[]),code,label)
        matched+=bool(row)
        recognized=row['row_label'] if row else ''
        cer+=edits(label,recognized)
        wer+=edits(label.split(),recognized.split())
        characters+=len(label)
        tokens+=len(label.split())
        cells=row.get('cells',[]) if row else []
        for i,expected in enumerate(amounts):
            candidate=cells[i] if i<len(cells) else {}
            read=candidate.get('text','')
            hit=read==expected
            correct+=hit
            binding=(candidate.get('period'),candidate.get('unit'))==(gold['periods'][i],gold['unit']) and bool(candidate.get('box'))
            bound+=binding
            comparisons.append({'row':label,'item_code':code,'period':gold['periods'][i],'gold':expected,
                'read':read,'exact':hit,'bound':binding,'label_read':recognized,'box':candidate.get('box')})
    return {'rows_found':matched,'rows_total':len(gold['rows']),'exact':correct,
            'cells':len(comparisons),'column_period_unit_bound':bound,'label_cer':cer/characters,
            'label_wer':wer/tokens,'comparisons':comparisons}


def baseline_page(client,base_url,workspace,docid,number,output):
    reply=client.get(f'{base_url}/studio/documents/{docid}/pages/{number}/evidence',timeout=40)
    reply.raise_for_status()
    raw=reply.content
    page=json.loads(raw.decode('utf-8',errors='strict'))
    with closing(sqlite3.connect(f'{(workspace/"index.sqlite3").resolve().as_uri()}?mode=ro',uri=True)) as db:
        saved,payload_hash=db.execute('SELECT payload,payload_hash FROM page_evidence WHERE document_id=? AND page=?',(docid,number)).fetchone()
    assert sha256(saved.encode('utf-8')).hexdigest()==payload_hash
    assert page['text']==json.loads(saved)['text']
    (output/f'baseline-{number}.json').write_bytes(raw)
    (output/f'baseline-{number}.txt').write_text(page['text'],encoding='utf-8-sig')
    return page


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:18110')
    parser.add_argument('--workspace',type=Path,default=ROOT/'studio_workspace/react-product-20261028')
    parser.add_argument('--reuse-candidate',action='store_true')
    parser.add_argument('--compare-workspace',type=Path)
    parser.add_argument('--out',type=Path,default=ROOT/'tmp/ocr-hpg-repair')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    gold=json.loads(SAMPLE.read_text(encoding='utf-8-sig'))
    docid=gold['document_id']
    source=args.workspace/'files'/(docid+'.pdf')
    source_hash=sha256(source.read_bytes()).hexdigest()
    assert source_hash.startswith(docid)
    token=(ROOT/'tmp/studio-runtime/access-token.txt').read_text(encoding='utf-8-sig').strip()
    with requests.Session() as client,pymupdf.open(source) as pdf:
        client.headers['Authorization']='Bearer '+token
        summary={}
        prior_path=args.out/'ab-summary.json'
        prior=json.loads(prior_path.read_text(encoding='utf-8')) if prior_path.is_file() else {}
        for number,page_gold in gold['pages'].items():
            n=int(number)
            baseline=baseline_page(client,args.url,args.workspace,docid,n,args.out)
            candidate_path=args.out/f'candidate-{n}.json'
            if args.reuse_candidate:
                candidate=json.loads(candidate_path.read_text(encoding='utf-8'))
                seconds=prior[number]['candidate_seconds']
            else:
                start=perf_counter()
                candidate=extract_page(pdf[n-1],n)
                seconds=round(perf_counter()-start,3)
                candidate_path.write_text(json.dumps(candidate,ensure_ascii=False,indent=2),encoding='utf-8')
            entry={'split':page_gold['split'],'strict_utf8_sqlite_match':True,'candidate_seconds':seconds,
                   'baseline':score(baseline,page_gold),'candidate':score(candidate,page_gold)}
            summary[number]=entry
            paddle_file=args.out/f'paddle-{n}.json'
            if paddle_file.is_file():
                paddle=json.loads(paddle_file.read_text(encoding='utf-8'))
                entry['paddle']=score({'tables':reconstruct(paddle['words'],n)},page_gold)
                entry['paddle_seconds']=paddle['seconds']
                entry['paddle_peak_rss_bytes']=paddle.get('peak_rss_bytes')
                if args.compare_workspace:
                    comparison=args.compare_workspace/'ocr-comparison'/docid
                    with closing(sqlite3.connect(f'{(args.compare_workspace/"index.sqlite3").resolve().as_uri()}?mode=ro',uri=True)) as db:
                        saved,checkpoint_hash=db.execute('SELECT payload,payload_hash FROM page_evidence WHERE document_id=? AND page=?',(docid,n)).fetchone()
                    if sha256(saved.encode('utf-8')).hexdigest()!=checkpoint_hash or json.loads(saved)['source_sha256']!=source_hash:
                        raise ValueError('OCR_COMPARISON_SOURCE_MISMATCH')
                    angle=candidate['engine']['correction_clockwise']
                    width,height=(i*72/300 for i in paddle['input_size'])
                    original_width,original_height=(height,width) if angle in {90,270} else (width,height)
                    source_words=[]
                    for word in paddle['words']:
                        x0,y0,x1,y1=inverse_box(word['box'],angle,original_width,original_height)
                        box=[x0*candidate['width']/original_width,y0*candidate['height']/original_height,
                             x1*candidate['width']/original_width,y1*candidate['height']/original_height]
                        source_words.append({'text':word['text'],'box':box,'confidence':word['confidence']})
                    comparison.mkdir(parents=True,exist_ok=True)
                    (comparison/f'{n}.json').write_text(json.dumps({'source_sha256':source_hash,'page':n,
                        'checkpoint_sha256':checkpoint_hash,'engine':paddle['engine'],'words':source_words},ensure_ascii=False),encoding='utf-8')

            (args.out/'ab-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
            print(n, candidate['engine'], [(key,entry[key]['exact'],entry[key]['cells'],entry[key]['column_period_unit_bound'])
                   for key in ('baseline','candidate','paddle') if key in entry],seconds,flush=True)
    assert sha256(source.read_bytes()).hexdigest()==source_hash


if __name__=='__main__':
    main()
