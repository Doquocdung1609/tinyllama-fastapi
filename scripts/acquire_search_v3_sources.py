"""Download hash-pinned public evaluation PDFs into a new directory; never overwrite."""
import argparse,hashlib,json
from pathlib import Path
import requests


def acquire(manifest,destination):
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('NEW_SOURCE_DIRECTORY_REQUIRED')
    records=json.loads(Path(manifest).read_text(encoding='utf-8'))
    if not isinstance(records,list):raise ValueError('SOURCE_MANIFEST_LIST_REQUIRED')
    destination.mkdir(parents=True)
    for source in records:
        url=source['url']
        if not url.startswith('https://'):raise ValueError('HTTPS_SOURCE_REQUIRED')
        name=source['sha256']+'.pdf';target=destination/name
        if target.exists():raise ValueError('DUPLICATE_SOURCE_SHA')
        response=requests.get(url,timeout=90);response.raise_for_status();data=response.content
        if not data.startswith(b'%PDF') or hashlib.sha256(data).hexdigest()!=source['sha256']:raise ValueError('SOURCE_BYTES_CHANGED;KEEP_PRIOR_LABELS_AND_REVIEW_NEW_VERSION')
        target.write_bytes(data)
        print(source['ticker'],source['sha256'],len(data))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',default='docs/search_v3/SOURCE_MANIFEST.json');p.add_argument('--destination',required=True);a=p.parse_args();acquire(a.manifest,a.destination)
