# Milestone C — final acceptance report

## Quyết định

**READY_FOR_OWNER_ACCEPTANCE** cho pilot local/controlled review. PR #8 phải giữ **Draft**; quyết định này không phải production certification, không merge và không mở Milestone D.

## Đã đóng

- Mutation auth/default-deny, request/resource bounds và stable errors.
- Embedded Qdrant single-owner; server mode explicit.
- Conservative retention inventory/dry-run/apply, pin/evaluation/rollback protection, recovery audit; stale-plan activation race đã có repair + regression.
- Generation-bound provenance cache giữ per-request cryptographic rehash; measured p50 total giảm 1.558 → 238 ms trên controlled sample.
- Ollama session reuse, full identity, timeout; explicit IPv4 loại persistent ~2,05 giây first-connection fallback của `localhost`.
- Windows path preflight; failed atomic write không để `.tmp`.
- Issuer/document-held-out freeze và one-shot evaluation hoàn tất, không tuning trên held-out.
- Core GitHub Actions gate không phụ thuộc SEC/model/GPU.

## Critical fixes trong review

1. Accepted concurrent build từng có thể stranded ở BUILDING; đã serialize và test.
2. Nomic document/query prefix contract bị thiếu; đã đưa vào embedding identity và rebuild semantics.
3. Retention stale-plan race có thể xóa generation vừa activate/pin; đã dùng common mutation lock + in-lock revalidation.
4. Atomic write failure có thể để temp artifact; đã cleanup trong `finally`.

## Chất lượng và latency

Frozen 14-query evidence được bảo toàn: BM25/Dense/Hybrid Recall@5 `0,911/0,321/0,714`. Issuer held-out mới: `0,938/0,813/0,938`; BM25 vẫn nên là default vì MRR/nDCG nhỉnh Hybrid và Hybrid có failure WMT margin do overlap bias.

Ollama fresh connection `/api/tags`: localhost p50 `2.050 ms`, IPv4 p50 `4,1 ms`; reused localhost chỉ nhanh sau lần fallback đầu. Warm embedding p50 `50,6 ms` localhost session đã nối và `57,7 ms` IPv4. Provenance cache giữ hash-on-every-request và là cải thiện latency chính.

## Regression và giới hạn

Targeted hardening/ingestion/persistent suite: `39 passed`; hardening sau race repair: `13 passed`. Final full suite: `194 passed, 3 skipped, 1 warning in 21.44s`. Ba skip là integration tests cần owner model/SAPI/ffmpeg environment và không nằm trong deterministic CI. So với reported 182 PASS, chênh lệch +12 là các regression tests được thêm trong hai vòng review; không có test cũ bị xóa.

Giới hạn production còn lại: Qdrant server auth/TLS, distributed rate limiting/job queue, backup/restore và real power-loss/fsync tests, larger multi-issuer pooled qrels, alternative embedding model experiment, and fresh holdout for any future fusion tuning.
