# OCR accuracy audit

CER/WER use normalized Unicode text and Levenshtein distance.

| Sample | CER | WER | Target | Result |
|---|---:|---:|---:|---|
| VI-clean | 0.98% | 4.55% | ≤5% CER | PASS |
| VI-table | 15.85% | 58.14% | ≤5% CER | FAIL |
| EN-table | 1.07% | 3.33% | ≤3% CER | PASS |

All 12 numeric cells in the Vietnamese and English scanned tables matched exactly (100%).
The Vietnamese table prose misses several accents, so its whole-page CER target fails while its numeric extraction and RAG calculation pass.
The image-only chart supports exact labels that OCR can read; the 2022 label and some unit characters remain unreliable, so full arbitrary chart interpretation is PARTIAL.
