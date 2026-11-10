"""CPU-only PaddleOCR probe. Run in a separate environment on 300 DPI renders."""
import argparse
import json
from pathlib import Path
from time import perf_counter

from PIL import Image
import psutil


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('pages',nargs='+',type=int)
    args=parser.parse_args()
    from paddleocr import PaddleOCR
    start=perf_counter()
    engine=PaddleOCR(device='cpu',lang='vi',ocr_version='PP-OCRv6',
        text_detection_model_name='PP-OCRv6_small_det',
        text_recognition_model_name='PP-OCRv6_small_rec',
        use_doc_orientation_classify=False,use_doc_unwarping=False,
        use_textline_orientation=False,enable_mkldnn=False,cpu_threads=2,
        text_det_limit_side_len=2600,text_det_limit_type='max')
    init_seconds=perf_counter()-start
    for page in args.pages:
        path=args.output/f'input-{page}.png'
        started=perf_counter()
        result=next(iter(engine.predict(str(path)))).json['res']
        words=[]
        with Image.open(path) as rendered:
            width,height=rendered.size
        for text,confidence,poly in zip(result['rec_texts'],result['rec_scores'],result['rec_polys'],strict=True):
            x0,y0=min(pt[0] for pt in poly),min(pt[1] for pt in poly)
            x1,y1=max(pt[0] for pt in poly),max(pt[1] for pt in poly)
            scale=72/300
            # Preserve raw polygon and an approximate rectangle. This probe's
            # reading coordinates are rotated when the input image was rotated.
            words.append({'text':text,'confidence':confidence*100,'rx':x0*scale,'ry':y0*scale,
                          'rw':(x1-x0)*scale,'rh':(y1-y0)*scale,'box':[v*scale for v in (x0,y0,x1,y1)]})
        rss=psutil.Process().memory_info()
        payload={'engine':'PP-OCRv6_small','coordinate_space':'300_DPI_CORRECTED_IMAGE_POINTS',
                 'words':words,'raw':result,'init_seconds':init_seconds,'seconds':perf_counter()-started,
                 'peak_rss_bytes':getattr(rss,'peak_wset',None),'input_size':[width,height]}
        (args.output/f'paddle-{page}.json').write_text(json.dumps(payload,ensure_ascii=False,default=lambda v:v.tolist()),
                                                      encoding='utf-8')
        print(page,payload['seconds'],len(words),payload['peak_rss_bytes'],flush=True)


if __name__=='__main__':
    main()
