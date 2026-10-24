# Đề xuất Milestone C — chưa được ủy quyền

Milestone B dừng ở normalized chunks + staging index. Không có hạng mục dưới đây được triển khai trong branch hiện tại.

## Điều kiện vào Milestone C

1. Cấu hình `SEC_USER_AGENT` với tên ứng dụng và contact email thật.
2. Chạy bounded live smoke (1 filing), xác minh accession, hashes, table và evidence.
3. Nếu smoke đạt, freeze một pilot manifest; nếu không, sửa B và tạo snapshot mới.
4. Chốt schema dataset membership và migration/rollback plan trước Qdrant.
5. Có explicit authorization của người dùng.

## Phạm vi đề xuất

- Persistent lexical index đồng bộ `index_generation` với financial vector namespace.
- Controlled Qdrant staging collection riêng; không dùng/xóa `knowledgebase`.
- BM25-only, dense-only, RRF và optional local reranker trên cùng snapshot.
- Metadata prefilter theo CIK/form/fiscal period trước candidate generation.
- Table-aware indexing, stable result IDs và full search provenance.
- Transaction/outbox hoặc generation switch để tránh lexical/vector lệch phiên bản.
- Indexing time/size, query P50/P95, throughput và resource measurements.
- Rollback và orphan-generation cleanup ở chế độ dry-run trước.

## Không thuộc Milestone C ban đầu

- Không tạo benchmark winner claim trước independent benchmark (Milestone D).
- Không bật reranker mặc định khi chưa đo lợi ích/chi phí.
- Không thêm multi-agent QA, model lớn, cloud trả phí hoặc UI phức tạp.
- Không di chuyển/xóa 1.947 vectors production.

## Rủi ro cần giải quyết

- Corpus version membership và amendment query policy.
- Exact synchronization giữa SQLite manifest, lexical generation và vector generation.
- Partial extraction visibility trong retrieval.
- Backfill metadata cho tài liệu cũ và zero cross-scope leakage.
- Windows 8 GB RAM/4 GB VRAM resource ceiling.

Milestone C chỉ bắt đầu sau khi Milestone B live gate được xử lý hoặc blocker được người dùng chấp nhận rõ ràng.


## Cập nhật độc lập 24/10/2026

Chưa sẵn sàng nghiệm thu B: cần giữ headers đa tầng, kỳ/scale/footnotes, versioned derived artifacts và bổ sung live legacy/amendment evidence. Chưa triển khai C. Đề xuất BM25 persistent lưu corpus statistics, incremental updates và generation/snapshot chung; metadata prefilter CIK/form/period/version; hybrid dense+BM25 và RRF; staging Qdrant riêng, table-aware representation; đo P50/P95, throughput, CPU/RAM trên SEC thật với manifest cố định; crash recovery và rollback theo generation. Không dùng 0,926 queries/s synthetic như kết quả SEC, không nêu cải thiện hiệu năng chưa đo. Chỉ bắt đầu sau nghiệm thu B và ủy quyền mới.
