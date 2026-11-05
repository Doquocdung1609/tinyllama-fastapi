from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from app.product.sec_library import FederatedIndex, federated_search, for_hit
from app.table_evidence.real_source import _source_period
from scripts.fis_v3_sec47_audit import scan


def duration(start, end):
    return {'xbrli:startdate': start, 'xbrli:enddate': end}


@pytest.mark.parametrize('start,end,label,months', [
    ('2026-02-16','2026-05-10','12 Weeks Ended May 10, 2026',3),
    ('2025-09-01','2026-05-10','36 Weeks Ended May 10, 2026',9),
    ('2026-05-04','2026-08-02','Three Months Ended August 2, 2026',3),
    ('2026-02-02','2026-08-02','Six Months Ended August 2, 2026',6),
])
def test_product_period_checks_source_column(start,end,label,months):
    assert _source_period(duration(start,end),[label],product_mode=True)==('DURATION',start,end,months)


def test_product_period_rejects_ytd_in_quarter_column():
    with pytest.raises(ValueError,match='HEADER_XBRL_WEEK_CONFLICT'):
        _source_period(duration('2025-09-01','2026-05-10'),['12 Weeks Ended May 10, 2026'],product_mode=True)


def test_federation_uses_partition_rank_and_keeps_reference_owner():
    a=SimpleNamespace(identity={'generation':'a'},catalog_rows=[],by_id={'a1':1,'a2':2})
    b=SimpleNamespace(identity={'generation':'b'},catalog_rows=[],by_id={'b1':3})
    idx=FederatedIndex([a,b])
    local={'a':[{'chunk_id':'a1','rank':1,'score':1},{'chunk_id':'a2','rank':2,'score':100}],
           'b':[{'chunk_id':'b1','rank':1,'score':-200}]}
    result=federated_search(idx,lambda part:{'results':local[part.identity['generation']]},2)
    assert [r['chunk_id'] for r in result['results']]==['a1','b1']
    assert for_hit(idx,result['results'][1]) is b


def test_audit_recovers_renamed_raw_and_repacked_zip(tmp_path):
    content=[b'<html>a</html>',b'<html>bb</html>']
    manifest={'source_packages':{},'sources':[
        {'accession':str(i),'byte_size':len(raw),'sha256':sha256(raw).hexdigest(),
         'source_zip_member':f'original{i}.htm','source_url':f'https://www.sec.gov/{i}.htm'}
        for i,raw in enumerate(content)
    ]}
    (tmp_path/'document.saved').write_bytes(content[0])
    with zipfile.ZipFile(tmp_path/'other-name.zip','w') as archive:
        archive.writestr('changed/name.html',content[1])
    found,mismatches,conflicts=scan([tmp_path],manifest,{}, {})
    assert found=={'0':(tmp_path/'document.saved',None),'1':(tmp_path/'other-name.zip','changed/name.html')}
    assert not mismatches and not conflicts
