"""Optional isolated Paddle OCR worker for bounded source cell crops."""
import json
from pathlib import Path
import sys

from paddleocr import PaddleOCR


if __name__ == '__main__':
    folder = Path(sys.argv[1])
    engine = PaddleOCR(device='cpu',lang='vi',ocr_version='PP-OCRv6',
        text_detection_model_name='PP-OCRv6_small_det',text_recognition_model_name='PP-OCRv6_small_rec',
        use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,
        enable_mkldnn=False,cpu_threads=2,text_det_limit_side_len=640,text_det_limit_type='max')
    result = {}
    for path in sorted(folder.glob('*.png')):
        words = next(iter(engine.predict(str(path)))).json['res']['rec_texts']
        result[path.stem] = ' '.join(words)
    (folder/'result.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
