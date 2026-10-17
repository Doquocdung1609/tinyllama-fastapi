# Phase 1 baseline audit

## Scope and checkpoint

- Audit started from commit `f72895072ca1bb6cfdd341bad646e5d3b78c6ffe` on branch `main`.
- Recoverable checkpoint: `checkpoints/phase1-20261012-191457`.
- The checkpoint contains the base commit, Git status, production document metadata, Qdrant status, and a SQLite conversation backup. It does not copy model files.
- Production at checkpoint: Qdrant online, collection `knowledgebase`, 1,947 vectors, dimension 768, cosine distance; 3 document records; 1 persistent conversation.
- Production Qdrant and SQLite were never used by the benchmark uploads. All destructive and upload tests used `tmp/phase1_api` and API port 8002.

## Confirmed starting state

| Area | Confirmed result |
|---|---|
| Historical automated baseline | 62 passed, 3 skipped |
| FastAPI / Streamlit | Running on loopback ports 8000 / 8501 |
| Ollama | Online; `qwen2.5:3b` and `nomic-embed-text` available |
| OCR | Tesseract 5.4.0.20240606; `vie` and `eng` inference verified |
| GPU | NVIDIA GeForce GTX 1650 Ti, 4,096 MB VRAM |
| RAM | 7.84 GB total; less than 1 GB commonly available during the audit |
| Production data | 1,947 vectors, 3 documents, 1 conversation |
| Existing chart benchmark | 9 PASS, 3 PARTIAL |

Tessdata SHA-256:

- `vie.traineddata`: `B6B49293D95D0B6DBD8780174627E82C75BE957B6F4ED9862155540D6B00BB45`
- `eng.traineddata`: `7D4322BD2A7749724879683FC3912CB542F19906C83BCC1A52132556427170B2`

## Files inspected

The audit covered the required PDF, chunking, calculation, RAG, conversation, Qdrant and API services; Streamlit client and application entry point; test suite; requirements; conversation benchmark; prior quality, OCR, chart and generalization reports.

## Reproduce

```powershell
git show f72895072ca1bb6cfdd341bad646e5d3b78c6ffe
Get-Content checkpoints/phase1-20261012-191457/qdrant-status.json
Get-Content checkpoints/phase1-20261012-191457/documents.json
.\.venv\Scripts\python.exe -m pip check
```

`pip check` returned `No broken requirements found`. The full installed package snapshot is in `reports/phase1_dependencies.txt`.

