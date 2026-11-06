"""Reproducible OCR V3 scoring; never writes review records or reads Chat facts."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from time import perf_counter

import psutil
import pymupdf

from app.product import pdf_ocr_financial_v2 as v2, pdf_ocr_financial_v3 as v3
from scripts.fis_hpg_ocr_benchmark import score

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def measures(page, gold):
    result=score(page,gold)
    matrix=result['comparisons']
    result.update(found=sum(bool(c['read']) for c in matrix),
                  dash_found=sum(c['gold']=='-' and c['exact'] for c in matrix),
                  dash_total=sum(c['gold']=='-' for c in matrix))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shs',type=Path)
    parser.add_argument('hpg_workspace',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'tmp/ocr-v3/evaluation.json')
    args=parser.parse_args()
    gold=read(ROOT/'reports/hpg_ocr_v3/shs_visual_gold.json')
    hpg=read(ROOT/'reports/hpg_ocr/visual_gold.json')
    assert sha256(args.shs.read_bytes()).hexdigest()==gold['sha256']
    report={'independent_shs':{},'hpg':{}}
    with pymupdf.open(args.shs) as pdf:
        for number, spec in gold['pages'].items():
            page=pdf[int(number)-1]
            result=report['independent_shs'][number]={}
            for engine in (v2,v3):
                start=perf_counter()
                extracted=engine.extract_page(page,int(number))
                result[engine.VERSION]=dict(measures(extracted,spec),seconds=perf_counter()-start)
    connection=sqlite3.connect(f'{(args.hpg_workspace.resolve()/"index.sqlite3").as_uri()}?mode=ro',uri=True)
    with connection:
        for number,spec in hpg['pages'].items():
            raw,digest=connection.execute('SELECT payload,payload_hash FROM page_evidence WHERE document_id=? AND page=?',
                (hpg['document_id'],int(number))).fetchone()
            assert sha256(raw.encode()).hexdigest()==digest
            report['hpg'][number]=dict(measures(json.loads(raw),spec),split=spec['split'])
    connection.close()
    report['peak_process_rss_bytes']=getattr(psutil.Process().memory_info(),'peak_wset',None)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for key,section in report.items():
        if isinstance(section,dict):
            for number,item in section.items():
                print(key,number,{k:(v['exact'],v['cells'],v['dash_found'],v['dash_total']) for k,v in item.items() if isinstance(v,dict)}
                      if 'exact' not in item else (item['exact'],item['cells'],item['dash_found'],item['dash_total']))
    print('peak_process_rss_bytes',report['peak_process_rss_bytes'])


if __name__=='__main__':
    main()
