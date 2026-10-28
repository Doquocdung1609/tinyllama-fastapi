# Search V2 owner acceptance — final verification2026-10-29

**SEARCH_V2_PARTIAL — NOT SEARCH_V2_LOCKED.** PR23 baseline commit retained as parent; new work is on codex/financial-search-accuracy-v2. No merge authorized or performed. Independent human source adjudication is absent, so Gate5 cannot be PASS even though38 heldout queries were executed after policy lock.

| Gate | Status | Evidence |
|---|---|---|
|1 Root cause | PASS | Original failure reproduced before changes; baseline ranks/hashes retained |
|2 Data integrity | PASS bounded / PARTIAL semantic extraction | Raw/checkpoint/chunk/index hashes guarded;87 vectors preserved; OCR labels/column semantics not fully certified |
|3 Retrieval relevance | PASS bounded provisional |70 queries,7 arms, ablations and measured latency; remaining SEC/cross-page misses retained |
|4 Evidence correctness | PASS bounded |17 real-source guard cases,3 Decimal checks; no wrong verified claim in final measured splits |
|5 Independent evaluation | PARTIAL |Single source annotator; no independent human review; shared documents, negative-family overlap and exposed-label retest after critical repair |
|6 Product stability | PASS |643backend,7frontend,build/pip/compile;fresh OCR and final Prebuilt browser;worker MIME200/304 verified |

Remaining limitations do not justify presenting this as fully locked quality. Candidate Search V2 is explicitly labelled and rollback is available through Baseline/API search_profile=baseline. Existing benchmark/history data, accepted model/digest, parent branch and user workspaces must remain unchanged. No additional model, SPLADE, autonomous framework or paid service.

## Reproduce

Stop the source application's launcher first. Prepare a **new** clone; never overwrite an owner workspace:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_search_v2_workspace.py --source studio_workspace/react-product-20261028 --destination studio_workspace/search-v2-replay
.\.venv\Scripts\python.exe scripts/benchmark_search_v2.py --root studio_workspace/search-v2-replay --split development --output tmp/search-v2-dev-replay.json --sec-root tmp/studio-runtime/sec/p7-isolated-review-product-20261028 --sec-vectors tmp/studio-runtime/sec/t3-p10-isolated-vectors-product-20261028
.\.venv\Scripts\python.exe scripts/benchmark_search_v2.py --root studio_workspace/search-v2-replay --split heldout --output tmp/search-v2-test-replay.json --sec-root tmp/studio-runtime/sec/p7-isolated-review-product-20261028 --sec-vectors tmp/studio-runtime/sec/t3-p10-isolated-vectors-product-20261028
.\.venv\Scripts\python.exe -m pytest -q
npm run test --prefix frontend
npm run build --prefix frontend
```

Heldout command verifies frozen policy/labels and refuses an existing output path. Source PDFs/snapshots/models must already exist; none downloaded by this task. The product's `/studio/evaluation/search-v2` exposes matching recorded metrics only, with a provisional-annotation warning. See EVALUATION_POLICY_LOCK.json for selection rationale.

## Kết luận cho chủ dự án

**SEARCH_V2_PARTIAL — chưa đủ điều kiện SEARCH_V2_LOCKED.** Đã sửa ca truy vấn Hòa Phát bằng chỉ mục dòng/kiểm tra ngữ cảnh, không gắn câu trả lời hay số trang HPG vào backend. Baseline nguyên bản vẫn có trong So sánh, phiên chỉ mục mới có thể rollback.

Kết quả chạy lại38câu đã xem sau sửa lỗi: C4 MRR@5=0.767,Recall@5=0.744,p95=403.3ms;B2 MRR@5=0.084,Recall@5=0.089. Đây không phải test độc lập chưa thấy.70nhãn tạm thời,0nhãn được con người độc lập rà soát; hồ sơ ban đầu và sửa lỗi sau test được giữ lại.

Lỗi gắn ô HPG cho câu hỏi về Apple đã tái hiện và sửa; kiểm tra tên tiếng Anh/tiếng Việt, phủ định scope/basis và statement type có regression.17ca bảo vệ nguồn thật và3ca Decimal PASS. Chưa chứng nhận mọi alias doanh nghiệp, quý/năm tài chính phức tạp, mọi dòng OCR hay câu hỏi AI tùy ý. SEC/cross-page vẫn có miss; không dùng những con số này để tuyên bố chính xác tài chính tổng quát.

Dữ liệu gốc của chủ máy8file byte-identical. Nomic768/digest/COSINE/prefix và các thế hệ SEC cũ giữ nguyên. Không merge PR23,không tạo framework/model/paid service. 643backend PASS (1deprecation warning),7frontend PASS,build/pip/compile PASS. Fresh Prebuilt OCR của2PDF đã chạy; lượt kiểm tra lại cuối dùng dữ liệu đã lưu, không giả là một lần OCR lạnh mới. Token/logs private không được commit.

Ứng dụng: http://127.0.0.1:8110/app/. Lệnh khởi động: `scripts/run_financial_studio.ps1 -Mode Prebuilt -Workspace .\studio_workspace\search-v2-prebuilt-20261028`. Chọn Baseline để rollback thuật toán ngay; API cũ mặc định baseline. Cần bộ nhãn/test mới được rà soát độc lập trước khi xem xét LOCK.

Original run bytes (including superseded diagnostics and first test) are retained in MEASURED_RUN_SNAPSHOTS.zip; per-entry hashes are in its manifest. Final result JSON files use one record per line without changing any measured values.
