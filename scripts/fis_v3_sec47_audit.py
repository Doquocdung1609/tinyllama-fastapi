"""Read exact source manifest via Git; never open evaluation labels or research DBs."""
import csv,json,subprocess,zipfile
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/fis_product_v3'
def main():
 raw=subprocess.check_output(['git','show','4677339ac4da5a62685212cac718223fe30582ae:docs/topic3_v7a_g3/V7A_G3S_SEC47_RAW_SOURCE_MANIFEST.json'],cwd=ROOT)
 m=json.loads(raw);records=[]
 for s in m['sources']:
  package=m['source_packages'][s['origin_package']];p=Path(package['path']);available=False;reason='DECLARED_SOURCE_PACKAGE_MISSING'
  if p.is_file():
   if sha256(p.read_bytes()).hexdigest()!=package['sha256']:reason='PACKAGE_HASH_CONFLICT'
   else:
    with zipfile.ZipFile(p) as z:
     try:available=sha256(z.read(s['source_zip_member'])).hexdigest()==s['sha256'];reason='SOURCE_HASH_VERIFIED' if available else 'RAW_HASH_CONFLICT'
     except KeyError:reason='ZIP_MEMBER_MISSING'
  records.append({'ticker':s['ticker'],'cik':s['cik'],'accession':s['accession'],'form':s['form'],'report_end':s['report_date'],'filing_date':'NOT_IN_SOURCE_MANIFEST',
   'source_url':s['source_url'],'raw_sha256':s['sha256'],'raw_bytes':s['byte_size'],'raw_available':available,'parse_result':'NOT_VERIFIED','lexical_membership':'NOT_IMPORTED','vector_generation':'NONE',
   'product_eligibility':'SOURCE_READY_NEEDS_INDEX' if available else 'SOURCE_NOT_AVAILABLE','reason':reason})
 OUT.mkdir(parents=True,exist_ok=True)
 with (OUT/'SEC47_SOURCE_READINESS.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=records[0].keys());w.writeheader();w.writerows(records)
 (OUT/'SEC47_AUDIT.json').write_text(json.dumps({'manifest_sha256':sha256(raw).hexdigest(),'checkpoint':'4677339ac4da5a62685212cac718223fe30582ae','filings':len(records),'companies':len({r['ticker'] for r in records}),'ready':0,'source_available':sum(r['raw_available'] for r in records),'records':records},indent=2),encoding='utf-8')
 print('Audited',len(records),'filings; no research data modified.')
if __name__=='__main__':main()
