# Milestone C — next experiment plan

> Status 2026-10-25: E5 provenance cache và E6 issuer/document-held-out đã hoàn tất trong hardening. Held-out NVDA/WMT v1 nay đã consumed và tuyệt đối không dùng để tune. Các E1–E4 còn lại phải dùng development split và một fresh holdout mới nếu chọn configuration.

## Freeze và separation

Giữ nguyên `MILESTONE_C_QUERIES.json` cùng SHA-256 đã báo cáo; 14 query đó là **legacy development/diagnostic set**, không được dùng để claim unbiased improvement.

Bộ mới nằm ở `MILESTONE_C_NEXT_EVAL_QUERIES.json`:

- status `FROZEN_UNEVALUATED` tại thời điểm tạo;
- SHA-256 freeze `39196ad6b304e5f79975c8bfb3573d593a3ef0052ccd55135bd1dbd2face6555`;
- content membership SHA-256 `e36ea2a7…a525201` và raw hashes của cả ba filings được pin;
- 16 query: 8 development, 8 held-out;
- không qrel chunk ID nào trùng 14-query set;
- mọi qrel/filter được kiểm tra tồn tại/eligible trên reconstructed 822-chunk corpus;
- ground truth do đọc source row/paragraph và physical locator; không dùng LLM answer.

Prefix contract repair được đánh giá sau freeze. Held-out đã được mở đúng một lần; từ đây 8 query này phải được coi là consumed holdout, không dùng để tune tiếp.

## Coverage matrix

| Nhóm | Ví dụ development | Ví dụ held-out |
|---|---|---|
| Exact financial line items | Apple R&D expense | Tesla operating lease liabilities |
| Paraphrased finance | cash spent buying back shares | income-tax cash actually paid |
| Financial terminology | contract liability ↔ deferred revenue | effective vs statutory tax rate |
| Table context | iPhone three/nine-month + growth | Tesla segment cost 2025/2024/2023 |
| Cross-section | Tesla inventory balance + write-down policy | Apple R&D row + management explanation |
| Filing-period distinctions | quarterly vs nine-month tax provision | inventory at June vs September dates |
| Original vs amended | 10-K/A equity compensation plan row | 10-K/A director compensation heading |
| Negative/percentage | buybacks, tax benefit, iPhone 22% | FX translation negatives, tax percentages |

## Protocol từ thời điểm này

1. **Development only:** thử representation/prefix/boilerplate policy trên 8 development cases. Ghi mọi variant trước khi chạy.
2. Không thay qrels dựa trên output. Nếu phát hiện unjudged relevant passage, mở pooled-judgment revision mới, giữ v1 immutable và báo cả strict-v1 lẫn pooled metrics.
3. Chốt một configuration bằng tiêu chí trước: no regression BM25, provenance 100%, filter parity, Dense/Hybrid gain trên development, bounded latency/disk.
4. **One held-out run:** hiện đã dùng cho prefix repair. Không dùng kết quả 8 held-out để chọn k/weights. Bất kỳ tuning tiếp theo cần một fresh holdout khác.
5. Report Recall/MRR/nDCG/Precision@5 theo query và macro average; thêm Recall@10/20 để phân biệt candidate failure và top-5 fusion failure.
6. Report exact-ID stability riêng relevance stability. Dense ties phải có metric `top-k set churn` qua 5 identical runs.
7. Mọi benchmark pin model name/digest, input policy, raw hashes, content membership hash, generation, endpoint, OS, Qdrant mode và query-file hash.

## Experiments kế tiếp (không phải Milestone D implementation)

### E1. Representation ablation

Variants được pre-register:

- raw current chunk;
- compact table text: company/form/statement/period/unit + row label + deduplicated values;
- dual vector per table row: compact row vector + full provenance text retained only for display;
- boilerplate/short-heading suppression below a documented information threshold;
- no numerical value stripping.

Không đổi RRF k/weight trong E1. Đánh giá development; dùng fresh held-out sau khi chọn một representation.

### E2. Model-contract/model comparison

- Nomic with required asymmetric prefixes (current repair);
- một finance-capable/local alternative chỉ khi model đã cài sẵn hoặc owner duyệt download;
- same corpus/queries/candidate limit; no model-specific qrel changes;
- report model RAM/VRAM/build time and dimension/storage cost.

Prefix repair không được xem là model hyperparameter tuning; model selection thì có, nên phải dùng fresh held-out.

### E3. Fusion failure analysis

Trước khi chỉnh RRF, đo per-query ranks đến 40, overlap rate, relevant present-in-one/both channels và tie groups. Pre-register tối đa ba fusion variants (ví dụ equal RRF, BM25-priority fallback cho exact numeric tokens, learned-free weighted RRF). Chọn trên development, evaluate một lần trên fresh holdout.

### E4. Metadata/amendment policy

Thêm explicit request policy: `original_only`, `amendment_only`, `both`, hoặc exact `filing_ids`. Test cùng fiscal period có 10-K và 10-K/A, không silently prefer amendment. UI phải hiển thị accession/form và warning khi cả hai được search.

### E5. Provenance cache

Implement generation-bound parsed-chunk cache như latency report; giữ cryptographic rehash mỗi query. Acceptance: tamper tests pass, provenance p50 giảm chủ yếu ở parse/rechunk, không thay search IDs.

### E6. Fresh issuer/document holdout

Bộ 16 hiện tại chỉ query-held-out trên cùng ba filings. Generalization claim cần ít nhất hai issuer chưa dùng, original+amendment pair khác, một 10-Q và một 10-K, manual pooled qrels và raw hashes frozen trước mọi run. Không dùng SEC source drift mà không pin bytes.

## Acceptance gates cho owner review tiếp theo

- Full regression pass trong documented environment.
- Prefix identity prevents reuse of raw-policy vectors.
- No `BUILDING` generation stranded under two accepted concurrent builds.
- Filter/provenance/Qdrant sync tests unchanged.
- Fresh document-held-out Hybrid must not underperform BM25 beyond predeclared tolerance; otherwise BM25 remains default.
- IPv4 endpoint/config documented; benchmark reports identity and embed separately.
- Disk retention policy and unauthenticated mutating endpoint risk resolved before any production claim.

