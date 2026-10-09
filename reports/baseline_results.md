# Baseline results

Captured before the master-prompt changes.

## Core

- FastAPI and Streamlit were running locally.
- Eight tabs existed.
- Reload blank-page regression had already been repaired using `runpy.run_path`.
- Original unit suite: 10 tests passed after restricting pytest discovery to `tests/`; placing a raw checkpoint inside the project had initially caused duplicate-module collection errors.
- PDF: 249 pages, 1,053 chunks, embedding dimension 768.

## RAG sample baseline

| Case | Score/result | Evidence |
|---|---:|---|
| RAG-Q01 | 3/10 FAIL | Retrieved pages 87, 149, 242, 105, 144 instead of page 155. |
| RAG-Q09 | 6/10 FAIL | Retrieved pages 214–215 but omitted the essential consent/data-sharing relationship. |
| RAG-Q12 | 9/10 PASS | Retrieved page 237 and answered 69%. |
| RAG-Q15 | 10/10 PASS | At threshold 0.95 returned no source and refused correctly. |

Observed RAG wall time for these samples ranged from about 12 to 185 seconds. The score used here is the manual rubric in `TEST_CASES_PDF_FINTECH.md`.

## Optional media baseline

- Text-to-image: BLOCKED because torch/diffusers/accelerate and a local model were missing.
- Image-to-video: BLOCKED because dependencies/model were missing and 4 GB VRAM is below a safe SVD configuration.
- FFmpeg was available but no separately labelled motion mode existed.
