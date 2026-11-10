"""Build a separate, resumable OCR V2 index from an existing Studio PDF."""
import argparse
from contextlib import closing
from hashlib import sha256
from pathlib import Path
import sqlite3

from app.product.ocr_financial_workspace import AdaptiveFinancialOcrWorkspace, FinancialOcrWorkspace


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path)
    parser.add_argument('target',type=Path)
    parser.add_argument('document_id')
    parser.add_argument('--adaptive',action='store_true')
    args=parser.parse_args()
    baseline,target=args.baseline.resolve(),args.target.resolve()
    if baseline==target or target.is_relative_to(baseline):
        parser.error('target must be a separate workspace')
    with closing(sqlite3.connect(f'{(baseline/"index.sqlite3").as_uri()}?mode=ro',uri=True)) as db:
        row=db.execute('SELECT filename,sha256,issuer,document_type,report_period FROM documents WHERE id=?',
                       (args.document_id,)).fetchone()
    if row is None:
        parser.error('baseline document not found')
    filename,expected_hash,issuer,document_type,period=row
    raw=(baseline/'files'/f'{args.document_id}.pdf').read_bytes()
    if sha256(raw).hexdigest()!=expected_hash:
        raise ValueError('BASELINE_SOURCE_HASH_MISMATCH')
    workspace=(AdaptiveFinancialOcrWorkspace if args.adaptive else FinancialOcrWorkspace)(target)
    try:
        registered=workspace.add_pdf(filename,raw,issuer,document_type,period)
        result=workspace.process(registered['id'])
        print({key:result[key] for key in ('id','status','stage','pages','chunks','error_code')},flush=True)
        if result['status']!='READY':
            raise SystemExit(1)
    finally:
        workspace.close()


if __name__=='__main__':
    main()
