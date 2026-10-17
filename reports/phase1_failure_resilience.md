# Phase 1 failure resilience

Tested commit: `fe0462bbd777740138dd50488572dde2950d090a`

Command: `PYTHONPATH=. python scripts/phase1_resilience.py`

| Case | Status | Actual evidence |
|---|---:|---|
| Empty PDF | PASS | HTTP 422: {"detail":"Tệp PDF rỗng."} |
| Renamed non-PDF content | PASS | HTTP 415: {"detail":"Nội dung tệp không có chữ ký PDF hợp lệ."} |
| Corrupt PDF | PASS | {"upload": 200, "state": "FAILED", "error": "Failed to open file 'C:\\\\Users\\\\Admin\\\\Desktop\\\\AI_thay_Hieu\\\\tinyllama-fastapi\\\\tmp\\\\phase1_api\\\\uploads\\\\c32847794888b6cf8a4592aab4bfb514_corrupt.pdf' as type pdf."} |
| Password-protected PDF | PASS | {"state": "FAILED", "error": "PDF được bảo vệ bằng mật khẩu; hãy cung cấp bản đã mở khóa để xử lý."} |
| Upload over configured limit | PASS | HTTP 413: {"detail":"Dung lượng PDF vượt quá 50 MB."} |
| Duplicate upload | PASS | {"document_id": "e3ed2a35ccc751d3251d75b854f3de97", "filename": "A_text_only_vi.pdf", "path": "C:\\Users\\Admin\\Desktop\\AI_thay_Hieu\\tinyllama-fastapi\\tmp\\phase1_api\\uploads\\e3ed2a35ccc751d3251d75b854f3de97_A_text_only_vi.pdf", "status": "EXTRACTING", "pages": 0, "chunks": 0, "indexed_at": null, "error": null, "embedding_progress": {"completed": 0, "total": 0}, "content_hash": "e3ed2a35ccc751d3251d75b854f3de97a95e56e10d8dd6fd7f55e2203bb7b5f1", "status_updated_at": "2026-10-12T17:53:39.150 |
| Two simultaneous document requests | PASS | 200:Tỷ lệ thanh toán hiện hành = Tài sản ngắn hạn / Nợ ngắn hạn = 750 triệu đồng / 375 triệu đồng = 2 lầ; 200:Biên lợi nhuận gộp = Lợi nhuận gộp / Doanh thu thuần = 500 triệu đồng / 1.25 tỷ đồng = 40%. [phase1_ |
| Browser reload during document job | PASS | reprocess=200; reload=200; content-type=text/html; charset=utf-8 |
| PDF prompt injection | PASS | answer=Verified revenue for 2024 is 77 million VND. [prompt_injection.pdf, trang 1]; citations=[{'filename': 'prompt_injection.pdf', 'page': 1, 'chunk_id': '0518519952a036ddcbd0a5ae4d71a701-00000', 'document_id': '0518519952a036ddcbd0a5ae4d71a701', 'modality': 'text', 'source_id': 'text:p1:chars0-92', 'bbox': None, 'evidence_id': 'E1'}] |
| Ollama unavailable | PASS | {"online": false, "model": "qwen2.5:3b", "model_available": false, "error": "offline"} |
| Qdrant unavailable | PASS | {"online": false, "collection": "knowledgebase", "vectors": 0, "error": "qdrant offline"} |
| Disk nearly full (safe simulation) | BLOCKED | The 507 guard is implemented with MIN_FREE_DISK_MB; filling the user's disk was intentionally not performed. |
| Low free RAM (safe simulation) | BLOCKED | Actual low-RAM snapshot is recorded in the resource report; intentional memory exhaustion was not performed. |
| Missing OCR language data | PASS | Capability detection returns OCR_ENGINE_UNAVAILABLE/BLOCKED_ENGINE_UNAVAILABLE without fabricated OCR; covered by extraction tests. |
| Deleted document in old conversation | PASS | C10 real persistent conversation returned HTTP 409 and did not reuse stale evidence. |
| Interrupted processing recovery | PASS | Atomic UPLOADED metadata is persisted; startup maps active stages to INTERRUPTED and duplicate upload can safely retry. |
