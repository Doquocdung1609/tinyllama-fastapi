# Real browser demo QA — Windows 11, 2026-11-01

Tested with the local Prebuilt launcher and the isolated `tmp/topic3/demo-workspace`. Login used the launcher-generated local token without recording its value. A managed stop/restart was performed; FastAPI and Ollama indicators returned online and both PDFs stayed READY.

| Step | Observed result | Status |
|---|---|---|
| Fresh launch/login | App opened at port 18110; 2 PDFs, 87 chunks, SEC/OCR ready. | PASS |
| Upload Hòa Phát PDF | Real 4.90 MB file accepted through browser; tracked document showed MIXED, 24/24 pages and READY. Same file was already indexed, so this is also an idempotent reupload, not a new cold OCR timing. | PASS with timing limit |
| BIDV Vietnamese answer | Page 1 quotation about State Audit, five source citations. | PASS |
| Open PDF evidence | Original BIDV PDF page 1 of 8 rendered in viewer. | PASS |
| Hòa Phát unit question | Source page 24 contains Q4 2025/2024 and VND. OCR answer remains unreviewed. | PARTIAL |
| Live comparison | Same question/scope; screenshot run BM25 20.58 ms, Dense 294.09 ms, Hybrid 119.60 ms. An earlier run measured 15.46/94.05/104.16 ms. | PASS |
| Historical Lab | Eight saved arms shown with explicit non-live status, corpus and provisional labels. | PASS |
| SEC verified cell | Home Depot 2026-08-02 assets 109,384 million USD, normalized 109,384,000,000 USD. | PASS |
| Unsupported year | BIDV 2037 numeric request refused, values/citations empty after repair. | PASS |
| Managed restart | App and PDF/SEC sources loaded again. | PASS |

Actual browser captures: [home](screenshots/01-home.png), [BIDV answer](screenshots/02-bidv-answer.png), [PDF source](screenshots/03-bidv-source.png), [Research Lab](screenshots/04-research-lab.png), [live comparison](screenshots/05-live-compare.png), [unsupported year](screenshots/06-absent-year-refusal.png), [verified SEC cell](screenshots/07-sec-verified.png), [upload](screenshots/08-hpg-upload.png), [Hòa Phát unit](screenshots/09-hpg-unit-answer.png).

One post-demo Windows snapshot (API listener PID 10716): API private memory 626.4 MB, working set 262.8 MB, process-reported peak working set 274.1 MB; C: free 64.38 GB; physical memory free 2.23/15.23 GB. This is a process/sample reading, not a whole-system peak or an OCR peak. No cold OCR-only processing duration was measured in V4 because the uploaded PDF was already indexed. Prior resource measurements in PR #29 are not presented as new measurements.
