from hashlib import sha256
import pymupdf
import pytest
from app.product.native_financial_tables import recover_native_tables


def source(tmp_path,unit='USD in millions',heading='CONSOLIDATED STATEMENTS OF OPERATIONS',header=True):
    pdf=pymupdf.open();page=pdf.new_page()
    page.insert_text((40,50),heading)
    page.insert_text((40,70),unit)
    if header:
        page.insert_text((290,100),'2025');page.insert_text((410,100),'2024')
    page.insert_text((40,120),'Net income');page.insert_text((290,120),'(125)');page.insert_text((410,120),'90')
    p=tmp_path/'other-company.pdf';p.write_bytes(pdf.tobytes());pdf.close()
    return p,sha256(p.read_bytes()).hexdigest()


def test_generic_negative_value_geometry_and_source_binding(tmp_path):
    p,h=source(tmp_path)
    tables=recover_native_tables(p,[1],h,{1:['retrieved-original-chunk']})
    c=tables[0]['cells'][0]
    assert c['value']=='-125' and c['year']==2025
    assert c['currency']=='USD' and c['scale']=='1000000'
    assert c['statement_scope']=='CONSOLIDATED'
    assert c['retrieved_chunk_ids']==['retrieved-original-chunk']
    assert c['box'] and c['header_box'] and c['source_sha256']==h
    assert tables[0]['verification_status']=='CANDIDATES_NOT_ELIGIBLE_FACTS'


def test_unknown_unit_and_scope_are_not_promoted(tmp_path):
    p,h=source(tmp_path,unit='Amounts shown below',heading='STATEMENTS OF OPERATIONS')
    c=recover_native_tables(p,[1],h)[0]['cells'][0]
    assert c['currency']=='UNKNOWN' and c['scale'] is None
    assert c['statement_scope']=='UNKNOWN' and c['status']=='TABLE_CONTEXT_INCOMPLETE'


def test_header_missing_means_no_cells(tmp_path):
    p,h=source(tmp_path,header=False)
    assert recover_native_tables(p,[1],h)==[]


def test_tampered_pdf_rejected_before_geometry(tmp_path):
    p,h=source(tmp_path);p.write_bytes(p.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='NATIVE_SOURCE_HASH_MISMATCH'):
        recover_native_tables(p,[1],h)
