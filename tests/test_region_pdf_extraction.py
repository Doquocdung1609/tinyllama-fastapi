"""Synthetic source-geometry regressions;real source recovery is measured separately."""
import io,json
from pathlib import Path
from unittest.mock import Mock
import pytest
import pymupdf
from PIL import Image,ImageDraw,ImageFont

from app.product import pdf_extract_v3r as region
from app.product.workspace import PdfWorkspace,DIMENSION
from app.product.derived_workspace import DerivedPdfWorkspace


class Vectors:
    def identity(self):return {'model':'SYNTHETIC_TEST_ONLY'}
    def embed(self,texts,query=False):return [[1.]+[0.]*(DIMENSION-1) for _ in texts]


def mixed_pdf():
    image=Image.new('RGB',(1100,650),'white');draw=ImageDraw.Draw(image);font=ImageFont.load_default(size=24)
    for i in range(8):
        draw.text((30,25+i*70),f'Financial source row {i}    123,450    145,600',fill='black',font=font)
        draw.line((25,65+i*70,1060,65+i*70),fill='black',width=1)
    stream=io.BytesIO();image.save(stream,format='PNG');pdf=pymupdf.open();page=pdf.new_page()
    page.insert_text((40,60),'Consolidated financial statements Example. This long native header does not represent the embedded table below.')
    page.insert_image(pymupdf.Rect(40,160,560,500),stream=stream.getvalue())
    return pdf


def ocr_words(box):
    words=[]
    for i in range(6):
        y=box.y0+25+i*35
        for text,x0,x1 in [(f'Financial row {i}',box.x0+10,box.x0+130),('123,450',box.x0+250,box.x0+290),('145,600',box.x0+370,box.x0+410)]:
            words.append({'text':text,'box':[x0,y,x1,y+9],'confidence':93.,'source':'OCR','line':[i,0]})
    return words,{'engine':'SYNTHETIC_TEST_ONLY','correction_clockwise':0}


def test_native_header_cannot_hide_unrepresented_table_image(monkeypatch):
    pdf=mixed_pdf();ocr=Mock(side_effect=lambda page,box,language:ocr_words(box));monkeypatch.setattr(region,'_ocr_region',ocr)
    result=region.extract_page(pdf[0],1);pdf.close()
    assert ocr.call_count==1 and result['method']=='REGION_FUSION'
    assert result['regions'][0]['features']['unrepresented_ink_fraction']>.9
    assert result['regions'][0]['kind']=='TABLE_IMAGE_CANDIDATE'
    assert '123,450' in result['text'] and len(result['tables'])>=6
    assert all(c['financial_evidence_status']=='FINANCIAL_EVIDENCE_REVIEW_PENDING' for r in result['tables'] for c in r['cells'])
    assert result['fusion']['native_words']>0


def test_clean_native_source_is_not_ocrd(monkeypatch):
    pdf=pymupdf.open();p=pdf.new_page();p.insert_text((40,50),'Native financial source Total assets 123,450 at year end 2025.')
    ocr=Mock(side_effect=AssertionError('Native source must not invoke OCR'));monkeypatch.setattr(region,'_ocr_region',ocr)
    result=region.extract_page(p,1);pdf.close()
    assert result['method']=='NATIVE' and '123,450' in result['text'] and not ocr.called


def test_duplicate_fusion_keeps_native_and_retains_numeric_ocr_overlap():
    native=[{'text':'Assets','box':[10,10,50,20],'source':'NATIVE','confidence':None}]
    ocr=[{'text':'Assets','box':[10,10,50,20],'source':'OCR','confidence':90},
         {'text':'noise','box':[80,10,150,23],'source':'OCR','confidence':0},
         {'text':'123,450','box':[85,11,145,21],'source':'OCR','confidence':80}]
    words,duplicates,conflicts=region._fuse(native,ocr)
    assert duplicates==1 and sum(w['text']=='Assets' for w in words)==1
    assert any(w['text']=='123,450' for w in words),'OCR-on-OCR overlap must not erase a numeric cell'


@pytest.mark.parametrize('angle',[0,90,180,270])
def test_reading_transform_roundtrips_source_box(angle):
    from app.product.pdf_extract import inverse_box
    source=[20,30,60,80];reading=region._reading(source,angle,200,300)
    assert inverse_box(reading,angle,200,300)==source


def test_sparse_logo_does_not_become_financial_table(monkeypatch):
    image=Image.new('RGB',(150,150),'white');draw=ImageDraw.Draw(image);draw.ellipse((15,15,135,135),outline='red',width=5)
    stream=io.BytesIO();image.save(stream,format='PNG');pdf=pymupdf.open();p=pdf.new_page();p.insert_text((40,50),'A source with a decorative circular stamp and no financial table.')
    p.insert_image(pymupdf.Rect(100,120,180,200),stream=stream.getvalue());ocr=Mock(return_value=([],{}));monkeypatch.setattr(region,'_ocr_region',ocr)
    result=region.extract_page(p,1);pdf.close()
    assert not any(r['kind']=='TABLE_IMAGE_CANDIDATE' for r in result['regions'])
    assert result['regions'][0]['status']=='DECORATIVE_OR_SPARSE_IMAGE'


def test_failed_region_is_visible_even_when_native_header_is_indexed(tmp_path,monkeypatch):
    pdf=mixed_pdf();raw=pdf.tobytes();pdf.close();monkeypatch.setattr(region,'_ocr_region',Mock(side_effect=ValueError('SYNTHETIC_OCR_FAILURE')))
    w=DerivedPdfWorkspace(tmp_path/'derived',embedder=Vectors())
    try:
        doc=w.add_pdf('mixed.pdf',raw,'Example','TEST','2025');result=w.process(doc['id'])
        assert result['status']=='READY','Legacy technical status remains compatible'
        assert result['processing_status']=='PROCESSING_COMPLETE'
        assert result['extraction_coverage_status']=='EXTRACTION_COVERAGE_WARNING'
        assert 'REGION_OCR_FAILED' in result['coverage_warnings']
        assert result['financial_evidence_status']=='FINANCIAL_EVIDENCE_REVIEW_PENDING'
        assert w.extraction_status(doc['id'])['extraction_coverage_status']=='EXTRACTION_COVERAGE_WARNING'
    finally:w.close()


def test_legacy_workspace_cannot_be_upgraded_in_place(tmp_path):
    legacy=PdfWorkspace(tmp_path/'legacy',embedder=Vectors());legacy.close()
    before=(tmp_path/'legacy/index.sqlite3').read_bytes()
    with pytest.raises(ValueError,match='NEW_DERIVED'):DerivedPdfWorkspace(tmp_path/'legacy',embedder=Vectors())
    assert before==(tmp_path/'legacy/index.sqlite3').read_bytes()


def test_derived_manifest_is_content_addressed_and_checkpoint_remains_immutable(tmp_path,monkeypatch):
    pdf=mixed_pdf();raw=pdf.tobytes();pdf.close();monkeypatch.setattr(region,'_ocr_region',lambda page,box,language:ocr_words(box))
    w=DerivedPdfWorkspace(tmp_path/'derived',embedder=Vectors())
    try:
        doc=w.add_pdf('mixed.pdf',raw,'Example','TEST','2025');result=w.process(doc['id'])
        assert result['status']=='READY'
        assert result['extraction_coverage_status']=='EXTRACTION_COVERAGE_WARNING','Mock OCR represents only part of the actual source raster'
        manifest=w.root/'generations'/(result['derived_generation']+'.json');before=manifest.read_bytes()
        assert w.process(doc['id'])['derived_generation']==result['derived_generation']
        assert manifest.read_bytes()==before and w.source_file(doc['id']).read_bytes()==raw
        page=w.page_evidence(doc['id'],1)
        assert page['table_layout_version']=='TABLE_LAYOUT_V3R_REGIONS_V2_FRAGMENTS'
        assert page['quality']['status']=='OCR_EXTRACTED_NOT_CERTIFIED'
        manifest.write_bytes(b'corrupted test manifest')
        with pytest.raises(ValueError,match='MANIFEST_INTEGRITY_FAILED'):w.document(doc['id'])
    finally:w.close()


def test_native_derived_processing_completion_does_not_claim_cell_review(tmp_path):
    pdf=pymupdf.open();p=pdf.new_page();p.insert_text((40,60),'Native financial statement source Total assets 123,450 at year end 2025. Explicit local source for tests.')
    raw=pdf.tobytes();pdf.close();w=DerivedPdfWorkspace(tmp_path/'native-derived',embedder=Vectors())
    try:
        d=w.add_pdf('native.pdf',raw,'Example','TEST','2025');result=w.process(d['id'])
        assert result['processing_status']=='PROCESSING_COMPLETE'
        assert result['extraction_coverage_status']=='EXTRACTION_COMPLETE'
        assert result['financial_evidence_status']=='FINANCIAL_EVIDENCE_REVIEW_PENDING'
    finally:w.close()


def test_high_confidence_fragment_cannot_replace_complete_amount(monkeypatch):
    import pytesseract
    pdf=mixed_pdf();p=pdf[0];box=pymupdf.Rect(40,160,560,500)
    primary={'text':'123,456,789','box':[250,200,330,210],'confidence':20.,'source':'OCR','rx':210,'ry':40,'rw':80,'rh':10}
    fragment={**primary,'text':'123','box':[250,200,265,210],'confidence':99.,'rw':15}
    monkeypatch.setattr(region.legacy,'ocr_capability',lambda:{'status':'READY'})
    monkeypatch.setattr(pytesseract,'image_to_osd',lambda *a,**k:{'orientation_conf':0})
    monkeypatch.setattr(region,'_ocr_pass',lambda *a,**k:[dict(primary)] if a[4]==3 else [dict(fragment)])
    words,engine=region._ocr_region(p,box,'eng');pdf.close()
    assert any(w['text']=='123,456,789' for w in words)
    assert not any(w['text']=='123' for w in words)
