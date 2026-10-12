# Local OCR setup

- Engine: Tesseract 5.4.0.20240606 (`C:\Program Files\Tesseract-OCR\tesseract.exe`).
- The verified winget installer completed without an interactive elevation prompt and selected `Program Files` despite the attempted workspace-local target. The application therefore exposes `TESSERACT_CMD` explicitly and keeps `vie.traineddata` in the project tessdata directory.
- Languages: `vie`, `eng`, `osd`; project tessdata is configured through `TESSDATA_PREFIX=tools/tessdata`.
- Python: pytesseract 0.3.13 and OpenCV headless 4.14.0.94.
- Routing: native text first; low-text/image pages render at 300 DPI and run CPU OCR. Word bounding boxes and confidence are mapped back to PDF coordinates.
- Scanned tables use conservative word alignment and are accepted only when numeric confidence is sufficient.
- Real API results: Vietnamese scan, bilingual scanned table and image-only chart all reached READY; no cloud API or vision model was used.
