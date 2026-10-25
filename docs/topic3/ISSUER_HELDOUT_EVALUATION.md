# Milestone C — issuer/document held-out evaluation

## Freeze

Selection được chốt trước query/ranking trong `MILESTONE_C_ISSUER_HELDOUT_CORPUS.json` (SHA-256 `1944ca…b9f`). Query/qrels được source-inspect, không dùng LLM answer, rồi freeze tại SHA-256 `c8aedd…792a`.

- Development: Microsoft 2026 10-K + Coca-Cola 2025 10-K, 8 queries, generation `ddf187…a40d`.
- Held-out: NVIDIA 2026 10-K + Walmart 2026 10-K, 16 queries, generation `afe00a…691`, mở đúng một lần.
- Mỗi filing lấy 160 ordinal chunks theo deterministic sampling. Đây là source-grounded subset evaluation, không phải full-filing recall census.
- Fixed: top-5, candidate 40, RRF k=60, no tuning sau development.

## Kết quả

| Split/mode | Recall@5 | Recall@10 | MRR@5 | nDCG@5 | Precision@5 |
|---|---:|---:|---:|---:|---:|
| Dev BM25 | 0,625 | 0,875 | 0,463 | 0,502 | 0,125 |
| Dev Dense | 0,625 | 0,750 | 0,531 | 0,554 | 0,125 |
| Dev Hybrid | 0,875 | 0,875 | 0,594 | 0,665 | 0,175 |
| Held-out BM25 | 0,938 | 1,000 | 0,797 | 0,833 | 0,188 |
| Held-out Dense | 0,813 | 0,938 | 0,496 | 0,574 | 0,163 |
| Held-out Hybrid | 0,938 | 1,000 | 0,771 | 0,814 | 0,188 |

Held-out 95% bootstrap CI Recall@5: BM25/Hybrid `[0,8125, 1,0]`, Dense `[0,625, 1,0]`. n=16 vẫn nhỏ; BM25 và Hybrid equal recall, BM25 nhỉnh MRR/nDCG, vì vậy không có căn cứ đổi default.

## Per-query failures quan trọng

- Dense miss top-5: NVDA net income (rank 7), WMT net sales (rank 7), WMT U.S. margin (>10). Những top results là adjacent segment/narrative/table rows: xác nhận query/table-row mismatch, không phải missing index.
- BM25 miss: NVDA foreign tax rank 6; Hybrid đưa target lên rank 2 nhờ dense rank 5.
- Hybrid miss duy nhất: WMT U.S. margin. Target BM25 rank 1 nhưng Dense rank 24; nhiều overlapping irrelevant segment rows nhận hai RRF contributions và đẩy target xuống hybrid rank 9. Đây là equal-RRF fusion failure, không phải arithmetic/dedup bug.
- Tất cả 48 held-out requests có provenance validity 1,0; qrels nằm trong đúng filter scope; 0 chunk bị truncation vì selected texts dưới 6.000 ký tự.

## Diagnosis

Confirmed: model prefix defect cũ, financial table representation, query/document mismatch và equal-RRF overlap effect. Ruled out ở corpus này: metadata filter, generation/vector mismatch, missing relevant member, payload mismatch và truncation. “Model quá nhỏ/không finance-specific” chỉ là hypothesis vì chưa có controlled alternative-model comparison.
