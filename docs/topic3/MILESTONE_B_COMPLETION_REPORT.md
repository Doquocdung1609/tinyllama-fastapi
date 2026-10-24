# Milestone B Completion Report

## Kết luận

**Trạng thái tổng thể: PARTIAL.** Code, offline integration, idempotency, recovery và lineage đã IMPLEMENTED/VERIFIED bằng fixture; acceptance gate bắt buộc live SEC chưa đạt vì môi trường không có `SEC_USER_AGENT` chứa contact email hợp lệ. Không có filing thật nào được tải và không có số liệu live bị bịa.

## Canonical Git state

- Branch: `codex/topic3-milestone-b-sec-corpus`.
- Base: `47dc39439eaa5e174c2d08113e9e6d759cf2fdd9`.
- Milestone A actual implementation: `87360aafb024632824c12a2f0e66be6600ad573f`.
- SHA được nêu trong work order `87360aa9b612...` không tồn tại local.
- PR #1 remote head vẫn `76336f4...`, draft/open, chưa merge.
- Milestone A commits sau PR head chỉ có local tại thời điểm audit.
- `reports/streamlit.stderr.log` là thay đổi có sẵn của người dùng, không thuộc commit.

## Trạng thái chức năng

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| SEC connector | IMPLEMENTED / offline VERIFIED | retry, conditional, allowlist tests |
| Live SEC connector | BLOCKED_EXTERNAL_SOURCE | thiếu valid SEC identity, 0 requests |
| Raw immutable storage | VERIFIED | exact hash + version preservation tests |
| HTML/iXBRL parser | PARTIAL | fixture pass; chưa có filing thật |
| Table preservation | PARTIAL | 1 synthetic table fully preserved |
| Stable version-aware chunks | VERIFIED | stable/rerun/revision tests |
| Idempotency | VERIFIED | one download, no duplicate rows/chunks |
| Resume/recovery | VERIFIED | interrupted + failed-item retry tests |
| Amendment history | VERIFIED offline | separate filing + `amendment_of` test |
| Source lineage | VERIFIED offline | reparsed disclosure/hash round trip |
| Immutable manifest | VERIFIED offline | same state -> same snapshot/hash |
| Production Qdrant migration | NOT IMPLEMENTED by design | Milestone C only |
| Existing RAG compatibility | VERIFIED automated | full 115 pass, 3 skip |

## SEC filings thật được sử dụng

Không có. Live smoke ngày 2026-10-24 dừng trước mạng vì cấu hình định danh không hợp lệ. `filing_sample.htm` và `submissions_sample.json` là synthetic fixtures.

## Parsing/table results

Fixture 1.205 bytes: 4 structured elements, 1 table, 13 cells, 4 rows, 8 chunks (4 text + 4 table), fiscal year 2023, period FY, units `USDm`/`millions`, no warning. Một lần đo: parse 3,203 ms; chunk 1,689 ms.

## API error semantics

- `DOCUMENT_NOT_FOUND` (404)
- `FILING_NOT_INDEXED` (409)
- `PARTIAL_INGESTION` (409)
- `METADATA_UNAVAILABLE` (409)
- `SOURCE_UNAVAILABLE` (410)
- invalid query/scope (422)
- missing SEC identity (503)

## Files thay đổi và lý do

- `app/financial_ingestion/*`: schema, connector, parser, chunker, registry, pipeline.
- `app/api/financial_corpus.py`: corpus operations và evidence API.
- `app/api/financial.py`, `financial_search_service.py`: stable availability errors.
- `app/config.py`, `.env.example`, `.gitignore`: isolated configurable storage.
- `main.py`: router + restart recovery.
- `scripts/financial_corpus.py`, `scripts/sec_live_smoke.py`: CLI và bounded live check.
- `tests/fixtures/sec/*`, `tests/test_sec_*`, `tests/test_financial_ingestion.py`, `tests/test_financial_corpus_api.py`: reproducible verification.
- `docs/topic3/*`: architecture, contracts, test evidence và limits.

## Test summary

- Targeted: 38 passed, 1 dependency deprecation warning.
- Full `.venv`: 115 passed, 3 skipped, 1 dependency deprecation warning.
- Live source: BLOCKED_EXTERNAL_SOURCE.
- FastAPI/Streamlit health: healthy.
- Qdrant knowledgebase: 1.947 vectors preserved.

## Git delivery

Implementation commit SHA sẽ được ghi ở report-sealing commit sau khi code và test evidence được commit. Không push, không tạo/merge/close PR nếu không có explicit remote authorization trong bước này.

## Vấn đề còn lại

1. Cần người dùng cung cấp `SEC_USER_AGENT` có email liên hệ thật, sau đó chạy live smoke tối đa một filing và ghi accession/hash/source evidence.
2. Parser cần corpus filing thật đa dạng để đánh giá nested/inline tables và footnotes.
3. Registry cần membership table nếu một filing phải thuộc nhiều snapshot active.
4. Backend hiện chạy cần restart để nạp router mới.
5. Không được gọi staging là searchable corpus trước Milestone C.

STOP: Không bắt đầu Milestone C trong thay đổi này.
