# Milestone C — retrieval diagnosis

> Addendum 2026-10-25: issuer/document-held-out evaluation mới (MSFT/KO development; NVDA/WMT held-out) đã freeze và chạy one-shot. Xem `ISSUER_HELDOUT_EVALUATION.md` cùng raw per-query evidence trong `reports/milestone_c_issuer_*.json`. Historical 14-query numbers bên dưới không bị thay đổi.

## Reproduction độc lập

Review tái tạo corpus từ đúng ba SEC URLs trong frozen qrels. Dấu vết nguồn:

- Apple 10-Q raw SHA-256 `d2fa4206…e8b8c`, normalized `94d101e7…0e7e`, 566 chunk, snapshot generation `84fb27e8…ad899` — khớp report.
- Tesla 10-K raw SHA-256 `78bd6ce4…9ed4`, 1.609 chunk.
- Tesla 10-K/A raw SHA-256 `04085826…0888`, 597 chunk; `amendment_of` trỏ đúng 10-K.
- Sampling giữ toàn bộ Apple và 128 ordinal positions từ mỗi Tesla filing: 822 chunk; 809 unique document texts.

Replay đúng raw-text embedding policy ở HEAD ban đầu tái hiện **chính xác aggregate metrics**:

| Mode | Recall@5 | MRR@5 | nDCG@5 | Precision@5 |
|---|---:|---:|---:|---:|
| BM25 | 0,911 | 0,786 | 0,822 | 0,271 |
| Dense | 0,321 | 0,113 | 0,160 | 0,071 |
| Hybrid RRF | 0,714 | 0,613 | 0,627 | 0,157 |

Một số irrelevant dense IDs đổi ở 6 case nhưng relevance metrics/failure pattern giữ nguyên. Nguyên nhân là nhiều cosine ties trên short/duplicate chunks và Qdrant cắt candidate trước secondary sort. BM25 top-5 khớp hoàn toàn.

## Chẩn đoán từng query frozen 14

`>40` nghĩa là target không có trong dense candidate top-40. Ranks dưới đây lấy trực tiếp từ rerun 822-chunk; Hybrid rank tính từ candidate lists bằng RRF k=60.

| Query | Relevant ranks BM25 / Dense / Hybrid | Failure top-5 |
|---|---|---|
| `aapl_sales` | `2,3,4,11 / >40×4 / 18,19,20,29` | BM25 lấy 3/4; Dense 0; Hybrid 0 vì double-channel irrelevant overlaps đẩy BM25-only targets xuống. |
| `aapl_assets` | `2 / >40 / 3` | Dense 0; Hybrid cứu target bằng BM25. |
| `aapl_cashflow` | `2 / >40 / 4` | Dense 0; Hybrid cứu target. |
| `aapl_eps` | `1 / 11 / 1` | Dense target nằm ngoài top-5; Hybrid tốt nhờ cả hai channel. |
| `aapl_period` | `2 / 36 / 12` | Dense/Hybrid đều miss top-5; short section headings chiếm dense top. |
| `aapl_numeric` | `1,2,3,4 / >40×4 / 8,10,12,14` | Exact number giúp BM25; Dense không tìm target; RRF demote cả bốn. |
| `aapl_percent` | `1 / 3 / 1` | Cả ba mode pass; query/table representation gần nhau. |
| `aapl_cash` | `11 / >40 / 32` | Cả ba miss; qrel row bị nhiều generic cash passages lấn át. |
| `tsla_profit` | `1,2 / 3,10 / 1,5` | Dense lấy 1/2; Hybrid lấy 2/2. |
| `tsla_receivables` | `1 / 3 / 1` | Cả ba pass. |
| `tsla_revenue` | `1 / 10 / 1` | Dense miss top-5; Hybrid cứu target. |
| `tsla_debt` | `1 / 3 / 1` | Cả ba pass. |
| `tsla_amend_ownership` | `1 / 4 / 1` | Cả ba pass. |
| `tsla_amend_fees` | `1 / 6 / 1` | Dense miss sát top-5; Hybrid cứu target. |

## RRF và dedup

Implementation đúng công thức và không double-count duplicate trong một channel. Failure không đến từ arithmetic defect mà từ candidate quality/equal weighting.

Ví dụ `aapl_sales`: Hybrid top-1 irrelevant “Note 2 – Revenue” nhận `1/(60+1)` từ BM25 và `1/(60+3)` từ Dense. Relevant rows chỉ có BM25 ranks 2–4 và không có dense rank, nên single-channel score của chúng thấp hơn mọi overlap hai channel, rơi xuống ranks 18–20. Với `k=60`, rank differences trong một channel bị nén; “xuất hiện ở cả hai channel” chi phối mạnh.

Không thay đổi k/weights/candidate limit trong review này. Việc tune trên 14-query set rồi báo unbiased improvement bị cấm.

## Root-cause matrix

| Khả năng | Kết luận | Bằng chứng |
|---|---|---|
| Incorrect metadata filtering | LOẠI TRỪ cho 14 cases | Mọi qrel tồn tại trong đúng filtered SQLite/Qdrant scope; CIK/ticker/form/year/period/filing ID parity tests pass. |
| Index/vector generation mismatch | LOẠI TRỪ | Full count=822, exact ID set match, generation payload match, dimension=768, returned payload hashes match; tamper tests fail closed. |
| Chunk truncation | LOẠI TRỪ | Min/mean/max lengths = 1/1.123,8/4.170 chars; 0 chunk vượt 6.000. |
| Missing model task prefixes | **CONFIRMED DEFECT** | Code embed raw documents/queries; Nomic model card yêu cầu `search_document:` và `search_query:`. |
| Query/document structural mismatch | **CONFIRMED** | Relevant Apple table chunks dài 1.345–2.617 chars với headers/duplicate cells; queries rất ngắn. Dense thường xếp short headings/boilerplate 10–35 chars lên đầu. |
| Financial table representation | **CONFIRMED CONTRIBUTOR** | `aapl_assets` dense top-5 là five 35-char headings; `aapl_cashflow` có four “Apple Inc.” 10-char chunks; exact target tables không vào top-40. |
| Embedding-model intrinsic limitation | HYPOTHESIS, chưa isolate | Nomic 137M không finance/table-specific. Prefix repair cải thiện nhưng không đủ; chưa so model khác trên held-out issuer set. |
| Annotation incompleteness | CONFIRMED LIMITATION | Qrels là exact source rows; semantically useful narrative passages có thể bị đánh non-target. Strict precision vì thế conservative. |

Nomic contract source: [official Nomic model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) nêu rõ task instruction prefix là bắt buộc cho RAG retrieval.

## Targeted prefix repair và evaluation tách biệt

Repair đổi model identity/input policy, buộc new generation và new vector cache; baseline/raw evidence cũ không bị sửa.

### Legacy 14-query development set (diagnostic only)

| Mode | Before Recall@5 | Prefix-aware Recall@5 | Before nDCG@5 | Prefix-aware nDCG@5 |
|---|---:|---:|---:|---:|
| BM25 | 0,911 | 0,911 | 0,822 | 0,822 |
| Dense | 0,321 | 0,554 | 0,160 | 0,372 |
| Hybrid | 0,714 | 0,786 | 0,627 | 0,714 |

Không gọi đây là unbiased improvement vì defect được phát hiện từ chính set này.

### Frozen next-eval set

`MILESTONE_C_NEXT_EVAL_QUERIES.json` được freeze trước prefix-aware evaluation, SHA-256 `39196ad6b304e5f79975c8bfb3573d593a3ef0052ccd55135bd1dbd2face6555`. 16 cases không trùng qrel với 14 cases cũ; 8 development + 8 held-out.

| Split | Queries | BM25 Recall@5 | Dense Recall@5 | Hybrid Recall@5 | BM25/ Dense/ Hybrid nDCG@5 |
|---|---:|---:|---:|---:|---|
| Development | 8 | 0,875 | 0,375 | 0,563 | 0,682 / 0,314 / 0,515 |
| Held-out (one evaluation) | 8 | 0,813 | 0,750 | 0,875 | 0,727 / 0,514 / 0,759 |

Held-out này là **query/qrel-held-out trên cùng ba filings**, không phải issuer/document-held-out. n=8 nhỏ; kết quả chỉ đủ làm acceptance signal cho contract repair, không chứng minh hybrid tổng quát tốt hơn.

## Kết luận chất lượng

- Poor Dense ban đầu chủ yếu là implementation/model-contract mismatch cộng với table/short-chunk representation; không phải filter, vector generation hay truncation bug.
- Prefix repair là cần thiết và cải thiện cả legacy diagnostic lẫn one-shot query-held-out, nhưng table-aware representation và boilerplate suppression vẫn cần experiment riêng.
- BM25 vẫn là default UI hợp lý cho pilot. Không đổi sang Hybrid default dựa trên 8 held-out cases.

