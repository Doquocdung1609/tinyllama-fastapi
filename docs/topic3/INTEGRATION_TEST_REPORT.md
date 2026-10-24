# Báo cáo kiểm thử tích hợp Milestone B

Ngày chạy: 2026-10-24. Hệ điều hành Windows, Python dự án từ `.venv`.

## Kết quả

| Phạm vi | Lệnh | Kết quả | Phân loại |
|---|---|---:|---|
| B targeted | `.venv\\Scripts\\python.exe -m pytest tests/test_sec_connector.py tests/test_sec_parser.py tests/test_financial_ingestion.py tests/test_financial_corpus_api.py tests/test_financial_api.py tests/test_financial_search.py -q` | 38 passed, 1 warning | integration + unit, offline fixture |
| Full regression | `.venv\\Scripts\\python.exe -m pytest -q` | 115 passed, 3 skipped, 1 warning | automated regression |
| System Python | `python -m pytest -q` | collection blocked: thiếu reportlab | environment failure, không phải code pass/fail |
| CLI dry-run | `python scripts/financial_corpus.py discover --cik 320193 --forms 10-K --limit 1 --dry-run` | DRY_RUN, 0 network requests | real CLI |
| Live SEC | `python scripts/sec_live_smoke.py --cik 320193 --limit 1` | BLOCKED_EXTERNAL_SOURCE, 0 requests | live integration blocked |

Ba test bị skip là các skip hiện hữu; không được chuyển thành PASS. Warning là Starlette deprecation từ TestClient/httpx compatibility.

## Những gì được chứng minh

- CIK/accession/source URL canonical và form/date discovery.
- User-Agent hợp lệ là bắt buộc; dry-run không gửi mạng.
- Retry lỗi kết nối/429, Retry-After, conditional headers, 304 cache và host allowlist.
- Raw exact bytes/hash, immutable paths, parser HTML/iXBRL và normalized hash.
- 1 table giữ grid/cells/unit/period/footnote trên fixture.
- Stable chunk IDs; raw version mới tạo IDs mới.
- Rerun idempotent không download/duplicate.
- Amendment là filing riêng, liên kết filing gốc.
- Interrupt/restart/retry an toàn.
- Chunk -> raw source locator round trip VERIFIED; tamper trả INVALID_RAW_HASH.
- REST dry-run và các mã lỗi source/scope được phân biệt.

## Health và bảo toàn dữ liệu

Read-only health check thực tế:

- `http://127.0.0.1:8000/health`: `ok`.
- `http://127.0.0.1:8501/_stcore/health`: `ok`.
- `/qdrant/status`: collection `knowledgebase`, 1.947 vectors, dimension 768, Cosine.
- Qdrant port 6333 không listen riêng; ứng dụng dùng local/embedded service.

Không có delete/upsert nào được gửi đến production Qdrant. Endpoint corpus mới chưa có trên process backend cũ đang chạy; cần restart backend để nạp code mới.

## Điều chưa được chứng minh

- **BLOCKED:** live SEC discovery/download/parse/index/evidence do thiếu User-Agent với contact email thật.
- **NOT IMPLEMENTED:** BM25/dense/Qdrant financial indexing (Milestone C).
- **PARTIAL:** parser chưa được benchmark trên nhiều filing thật, malformed tables lớn, complete filing archives hoặc external XBRL instance documents.
